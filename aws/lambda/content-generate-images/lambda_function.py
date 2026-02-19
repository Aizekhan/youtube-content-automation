import json
import boto3
import base64
import http.client
from datetime import datetime
from decimal import Decimal
from boto3.dynamodb.conditions import Key
import sys
import os

# Add shared directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'shared'))
from config_merger import merge_configuration

bedrock_runtime = boto3.client('bedrock-runtime', region_name='eu-central-1')
s3 = boto3.client('s3', region_name='eu-central-1')
secrets_client = boto3.client('secretsmanager', region_name='eu-central-1')
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
cost_table = dynamodb.Table('CostTracking')
lambda_client = boto3.client('lambda', region_name='eu-central-1')

# Helper function to convert DynamoDB Decimal to JSON-serializable types
def decimal_default(obj):
    """Convert Decimal to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

# Global variable for EC2 endpoint (passed from Step Functions state)
EC2_ENDPOINT = None

S3_BUCKET = 'youtube-automation-audio-files'  # Використовуємо існуючий bucket
S3_IMAGES_PREFIX = 'images'  # Підпапка для зображень

# Pricing for different providers (USD)
PRICING = {
    'aws-bedrock-sdxl': {
        'standard': 0.018,
        'premium': 0.036
    },
    'aws-bedrock-nova-canvas': {
        'standard-1024': 0.04,
        'premium-1024': 0.06,
        'standard-2048': 0.06,
        'premium-2048': 0.08
    },
    'ec2-zimage': {
        'hourly_rate': 1.006,  # g5.xlarge
        'images_per_hour': 720  # ~5 seconds per image (10x faster than SD3.5)
    },
    # Deprecated: SD3.5 replaced by Z-Image-Turbo
    'ec2-sd35': {
        'hourly_rate': 1.006,  # g5.xlarge
        'images_per_hour': 85.7  # ~42 seconds per image (28 steps)
    }
}

def log_image_cost(channel_id, content_id, provider, num_images, cost_per_image, user_id=None):
    """Log image generation cost to CostTracking table"""
    try:
        total_cost = Decimal(str(num_images * cost_per_image))

        now = datetime.utcnow()
        date_str = now.strftime('%Y-%m-%d')
        timestamp = now.isoformat() + 'Z'

        item = {
            'date': date_str,
            'timestamp': timestamp,
            'service': provider,
            'operation': 'image_generation',
            'channel_id': channel_id,
            'content_id': content_id,
            'cost_usd': total_cost,
            'units': num_images,
            'details': {
                'provider': provider,
                'images_generated': num_images,
                'cost_per_image': float(cost_per_image)
            }
        }

        # Add user_id for multi-tenant support
        if user_id:
            item['user_id'] = user_id
            print(f" Logged {provider} cost for user {user_id}: ${float(total_cost):.6f} ({num_images} images)")
        else:
            print(f"  Logging {provider} cost WITHOUT user_id: ${float(total_cost):.6f} ({num_images} images)")

        cost_table.put_item(Item=item)
        return float(total_cost)
    except Exception as e:
        print(f" Failed to log cost: {str(e)}")
        return 0.0

def generate_with_bedrock_sdxl(prompt, image_config):
    """Generate image using AWS Bedrock Stable Diffusion XL"""
    try:
        quality = image_config.get('quality', 'standard')
        width = image_config.get('width', 1024)
        height = image_config.get('height', 1024)

        # Prepare request for SDXL
        request_body = {
            "text_prompts": [{"text": prompt}],
            "cfg_scale": image_config.get('cfg_scale', 7),
            "steps": image_config.get('steps', 50),
            "seed": image_config.get('seed', 0),
            "width": width,
            "height": height
        }

        # Call Bedrock
        response = bedrock_runtime.invoke_model(
            modelId='stability.stable-diffusion-xl-v1',
            body=json.dumps(request_body, default=decimal_default)
        )

        response_body = json.loads(response['body'].read())

        # Extract base64 image
        image_base64 = response_body.get('artifacts', [{}])[0].get('base64')

        if not image_base64:
            raise Exception("No image returned from Bedrock SDXL")

        # Decode image
        image_bytes = base64.b64decode(image_base64)

        cost = PRICING['aws-bedrock-sdxl'][quality]

        return {
            'image_bytes': image_bytes,
            'cost': cost,
            'provider': 'aws-bedrock-sdxl',
            'width': width,
            'height': height
        }

    except Exception as e:
        print(f" Bedrock SDXL generation failed: {str(e)}")
        raise

# DEPRECATED: generate_with_replicate_flux() removed




def generate_with_ec2_sd35(prompt, image_config):
    """Generate image using EC2 SD 3.5 Medium (g5.xlarge)"""
    return generate_with_ec2_flux(prompt, image_config, provider='ec2-sd35')


def generate_with_ec2_zimage(prompt, image_config):
    """Generate image using EC2 Z-Image-Turbo (g5.xlarge - 10x faster than SD3.5)"""
    return generate_with_ec2_flux(prompt, image_config, provider='ec2-zimage')


# DEPRECATED: Vast.ai functions removed



# EC2 SD35 Control Functions
def start_ec2_sd35():
    """Start EC2 SD3.5 instance via ec2-sd35-control Lambda"""
    try:
        print(" Starting EC2 SD35 instance...")
        response = lambda_client.invoke(
            FunctionName='ec2-sd35-control',
            InvocationType='RequestResponse',
            Payload=json.dumps({'action': 'start'})
        )
        
        result = json.loads(response['Payload'].read())
        body = json.loads(result.get('body', '{}' ))
        
        endpoint = body.get('endpoint')
        print(f" EC2 started: {endpoint}")
        return endpoint
    except Exception as e:
        print(f" Failed to start EC2: {e}")
        raise


def check_ec2_sd35_status():
    """Check if EC2 SD3.5 instance is running"""
    try:
        response = lambda_client.invoke(
            FunctionName='ec2-sd35-control',
            InvocationType='RequestResponse',
            Payload=json.dumps({'action': 'status'})
        )
        
        result = json.loads(response['Payload'].read())
        body = json.loads(result.get('body', '{}'))
        
        return body.get('state') == 'running'
    except Exception as e:
        print(f"Failed to check EC2 status: {e}")
        return False

def stop_ec2_sd35():
    """Stop EC2 SD3.5 instance via ec2-sd35-control Lambda (async)"""
    try:
        print("Stopping EC2 SD35 instance (async)...")
        lambda_client.invoke(
            FunctionName='ec2-sd35-control',
            InvocationType='Event',
            Payload=json.dumps({'action': 'stop'})
        )
        print(" EC2 stop initiated")
    except Exception as e:
        print(f"  Failed to stop EC2 (non-critical): {e}")


def wait_for_image_service(endpoint, max_wait=120):
    """
    Wait until Z-Image/EC2 image service is ready to accept requests.
    EC2 instance can be 'running' but the ML service takes 30-120s to start.

    Args:
        endpoint: EC2 endpoint URL (e.g. 'http://IP:5000') or dict
        max_wait: Max seconds to wait (default 120)
    Returns:
        True if service ready, False if timed out
    """
    import time

    # Parse host:port from endpoint
    if isinstance(endpoint, dict):
        ep_str = endpoint.get('endpoint', '') or ''
    else:
        ep_str = str(endpoint)

    if ep_str.startswith('http://'):
        parts = ep_str.replace('http://', '').split(':')
        host = parts[0]
        port = int(parts[1].split('/')[0]) if len(parts) > 1 else 5000
    else:
        host = ep_str
        port = 5000

    if not host:
        print('wait_for_image_service: no endpoint, skipping wait')
        return True

    print(f'Waiting for image service at {host}:{port} (max {max_wait}s)...')
    waited = 0
    interval = 10

    while waited < max_wait:
        try:
            conn = http.client.HTTPConnection(host, port, timeout=5)
            conn.request('GET', '/health')
            resp = conn.getresponse()
            resp.read()
            conn.close()
            print(f'Image service ready after {waited}s (HTTP {resp.status})')
            return True
        except Exception as e:
            err_str = str(e)
            if 'refused' in err_str.lower() or 'timed out' in err_str.lower():
                print(f'Service not ready ({waited}/{max_wait}s), retrying in {interval}s...')
            else:
                print(f'Image service responded after {waited}s: {err_str[:60]}')
                return True
        time.sleep(interval)
        waited += interval

    print(f'WARNING: Image service not ready after {max_wait}s, attempting anyway')
    return False


def generate_with_ec2_flux(prompt, image_config, provider='ec2-flux-schnell'):
    """
    Generate image using EC2 instance (SD3.5, Z-Image, or FLUX)

    Args:
        prompt: Image generation prompt
        image_config: Image configuration (width, height, steps, etc.)
        provider: Provider identifier for cost calculation (e.g., 'ec2-sd35', 'ec2-zimage')
    """
    global EC2_ENDPOINT
    try:
        # Get EC2 endpoint from global variable (Step Functions) or Secrets Manager
        if EC2_ENDPOINT:
            print(f" Using EC2 endpoint from Step Functions state")
            # Parse endpoint from Step Functions Payload
            endpoint_data = EC2_ENDPOINT
            if isinstance(endpoint_data, dict) and 'body' in endpoint_data:
                import json as json_module
                body = endpoint_data['body']
                if isinstance(body, str):
                    body = json_module.loads(body)
                ec2_endpoint = body.get('endpoint', '')
            elif isinstance(endpoint_data, str):
                ec2_endpoint = endpoint_data
            else:
                ec2_endpoint = endpoint_data.get('endpoint', '')
            print(f"   Endpoint from state: {ec2_endpoint}")
        else:
            print(f" Using EC2 endpoint from Secrets Manager (fallback)")
            secret = secrets_client.get_secret_value(SecretId='ec2-flux-endpoint')
            ec2_endpoint = secret['SecretString']

        # Parse endpoint (format: "http://IP:PORT/generate")
        if ec2_endpoint.startswith('http://'):
            parts = ec2_endpoint.replace('http://', '').split(':')
            flux_api_host = parts[0]
            flux_api_port = int(parts[1].split('/')[0]) if len(parts) > 1 else 8000
        else:
            flux_api_host = ec2_endpoint
            flux_api_port = 8000

        # Extract dimensions from image_config
        width = int(image_config.get('width', 1024))
        height = int(image_config.get('height', 1024))

        # Call FLUX endpoint on EC2 instance
        request_body = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "steps": int(image_config.get('steps', 15))  # FLUX schnell optimal: 4-15 steps
        }

        print(f" Calling EC2 FLUX API at {flux_api_host}:{flux_api_port}")
        print(f"   Prompt: {prompt[:80]}...")

        conn = http.client.HTTPConnection(flux_api_host, flux_api_port, timeout=180)  # Increased from 90 to 180 for SD35
        headers = {'Content-Type': 'application/json'}

        conn.request('POST', '/generate', body=json.dumps(request_body), headers=headers)
        response = conn.getresponse()
        response_data = response.read()

        if response.status != 200:
            raise Exception(f"EC2 FLUX API Error: {response.status} - {response_data.decode()}")

        # Response is raw PNG from FastAPI
        content_type = response.getheader('Content-Type', '')
        if 'image/png' in content_type:
            image_bytes = response_data
        else:
            raise Exception(f"Unexpected content type: {content_type}")

        # Calculate cost dynamically based on provider pricing
        if provider in PRICING and 'hourly_rate' in PRICING[provider]:
            provider_config = PRICING[provider]
            cost = provider_config['hourly_rate'] / provider_config['images_per_hour']
        else:
            # Fallback to ec2-sd35 pricing if provider not found
            cost = PRICING['ec2-sd35']['hourly_rate'] / PRICING['ec2-sd35']['images_per_hour']

        print(f" Image generated successfully ({width}x{height}, cost: ${cost:.6f})")

        return {
            'image_bytes': image_bytes,
            'cost': cost,
            'provider': provider,  # Use the passed provider parameter
            'width': width,
            'height': height
        }

    except Exception as e:
        print(f" EC2 FLUX generation failed: {str(e)}")
        raise

# DEPRECATED: generate_with_vast_ai() removed

def get_dimensions_from_aspect_ratio(aspect_ratio, resolution_hint=None):
    """
    Convert aspect ratio string to width/height tuple

    Args:
        aspect_ratio: String like '16:9', '4:3', '1:1', '9:16'
        resolution_hint: Optional string like '1280x720', '1920x1080', '720x720'

    Returns:
        (width, height) tuple
    """
    # If resolution_hint is provided, parse it directly
    if resolution_hint and 'x' in str(resolution_hint):
        parts = str(resolution_hint).split('x')
        return (int(parts[0]), int(parts[1]))

    # Otherwise calculate from aspect ratio
    aspect_ratio_map = {
        '16:9': (1920, 1080),   # Standard YouTube HD
        '9:16': (1080, 1920),   # Vertical/Portrait
        '4:3': (1024, 768),     # Classic 4:3
        '1:1': (1024, 1024),    # Square
        '21:9': (2560, 1080),   # Ultra-wide
    }

    # Default to 16:9 if not found
    return aspect_ratio_map.get(aspect_ratio, (1920, 1080))

def upload_to_s3(image_bytes, channel_id, narrative_id, scene_id):
    """Upload image to S3 and return URL"""
    try:
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        key = f"{S3_IMAGES_PREFIX}/{channel_id}/{narrative_id}/scene_{scene_id}_{timestamp}.png"

        s3.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=image_bytes,
            ContentType='image/png'
        )

        s3_url = f"s3://{S3_BUCKET}/{key}"
        https_url = f"https://{S3_BUCKET}.s3.eu-central-1.amazonaws.com/{key}"

        print(f" Uploaded image to S3: {key}")

        return {
            's3_url': s3_url,
            'https_url': https_url,
            'key': key
        }

    except Exception as e:
        print(f" Failed to upload to S3: {str(e)}")
        raise

def handle_multi_channel_batch(all_prompts, provider, user_id=None):
    """
    Handle multi-channel batch mode where all_prompts contains prompts from multiple channels

    Input:
    all_prompts = [
        {
            "channel_id": "UCxxx",
            "content_id": "temp_xxx",
            "scene_index": 0,
            "prompt": "...",
            "negative_prompt": "...",
            "scene_number": 1,
            "image_type": "scene" or "thumbnail"
        },
        ...
    ]

    Output:
    {
        "scene_images": [
            {
                "channel_id": "UCxxx",
                "content_id": "temp_xxx",
                "scene_index": 0,
                "scene_number": 1,
                "image_url": "s3://...",
                "https_url": "https://...",
                "cost_usd": 0.027
            }
        ],
        "total_cost_usd": 0.27,
        "images_generated": 10
    }
    """
    print(f" Multi-Channel Batch Image Generation")
    print(f"   Provider: {provider}")
    print(f"   Total prompts: {len(all_prompts)}")

    scene_images = []
    total_cost = 0.0

    # Load channel configs and thumbnail templates to get dimensions
    channel_configs = {}
    thumbnail_dimensions = {}

    #  ОПТИМІЗОВАНО: Batch loading замість N+1 запитів до DynamoDB
    # Старий спосіб: N запитів для configs + N запитів для templates = 2N запитів
    # Новий спосіб: 1 batch запит для configs + 1 batch для templates = 2 запити!
    print(f"    Using optimized batch loading...")
    try:
        from resource_pool_manager import optimize_channel_configs_loading
        channel_configs, thumbnail_dimensions = optimize_channel_configs_loading(all_prompts, dynamodb)
    except (ImportError, Exception) as e:
        # Fallback to old method if module not available
        print(f"     Batch loading failed ({e}), using legacy method...")
        channel_configs = {}
        thumbnail_dimensions = {}
        unique_channels = set(p.get('channel_id') for p in all_prompts if p.get('channel_id'))
        print(f"   Loading configs for {len(unique_channels)} unique channels...")

        for channel_id in unique_channels:
            try:
                channel_table = dynamodb.Table('ChannelConfigs')
                channel_response = channel_table.query(
                    IndexName='channel_id-index',
                    KeyConditionExpression=Key('channel_id').eq(channel_id)
                )
                if channel_response.get('Items'):
                    channel_config = channel_response['Items'][0]
                    channel_configs[channel_id] = channel_config

                    # Load thumbnail template for this channel
                    selected_thumbnail_template = channel_config.get('selected_thumbnail_template')
                    if selected_thumbnail_template:
                        try:
                            thumbnail_table = dynamodb.Table('ThumbnailTemplates')
                            thumbnail_response = thumbnail_table.get_item(
                                Key={'template_id': selected_thumbnail_template}
                            )
                            if 'Item' in thumbnail_response:
                                thumbnail_template = thumbnail_response['Item']
                                thumbnail_config = thumbnail_template.get('thumbnail_config', {})
                                aspect_ratio = thumbnail_config.get('aspect_ratio', '16:9')
                                resolution = thumbnail_config.get('resolution', '1920x1080')

                                # Convert to actual dimensions
                                width, height = get_dimensions_from_aspect_ratio(aspect_ratio, resolution)
                                thumbnail_dimensions[channel_id] = (width, height)
                                print(f"    {channel_id[-6:]}: Thumbnail {aspect_ratio} = {width}x{height}")
                        except Exception as e:
                            print(f"     Failed to load thumbnail template for {channel_id}: {e}")
            except Exception as e:
                print(f"     Failed to load channel config for {channel_id}: {e}")

        # Default image config for scene images
    default_image_config = {
        'quality': 'standard',
        'width': 1024,
        'height': 576,
        'steps': 15  # EC2 FLUX schnell optimal
    }

    for i, prompt_data in enumerate(all_prompts):
        channel_id = prompt_data.get('channel_id', 'unknown')
        content_id = prompt_data.get('content_id')
        scene_index = prompt_data.get('scene_index', 0)
        scene_number = prompt_data.get('scene_number', scene_index + 1)
        prompt = prompt_data.get('prompt', '')
        negative_prompt = prompt_data.get('negative_prompt', '')
        image_type = prompt_data.get('image_type', 'scene')  # 'scene' or 'thumbnail'

        if not prompt:
            print(f"  Prompt {i+1}/{len(all_prompts)} is empty, skipping")
            continue

        if not channel_id or channel_id == 'unknown':
            print(f"  Prompt {i+1}/{len(all_prompts)} missing channel_id, skipping")
            continue

        # Determine image dimensions based on type
        if image_type == 'thumbnail' and channel_id in thumbnail_dimensions:
            width, height = thumbnail_dimensions[channel_id]
            image_config = {
                'quality': default_image_config['quality'],
                'width': width,
                'height': height,
                'steps': default_image_config['steps']
            }
            print(f"\n  Generating THUMBNAIL {i+1}/{len(all_prompts)}")
            print(f"   Channel: {channel_id[-6:]}")
            print(f"   Dimensions: {width}x{height} (from template)")
            print(f"   Prompt: {prompt[:80]}...")
        else:
            # Use channel-specific dimensions or default
            channel_config = channel_configs.get(channel_id, {})
            image_settings = channel_config.get('image_generation', {})

            image_config = {
                'quality': image_settings.get('quality', default_image_config['quality']),
                'width': image_settings.get('width', default_image_config['width']),
                'height': image_settings.get('height', default_image_config['height']),
                'steps': image_settings.get('steps', default_image_config['steps'])
            }
            print(f"\n Generating SCENE image {i+1}/{len(all_prompts)}")
            print(f"   Channel: {channel_id[-6:]}")
            print(f"   Scene: {scene_number}")
            print(f"   Dimensions: {image_config['width']}x{image_config['height']}")
            print(f"   Prompt: {prompt[:80]}...")

        try:
            # Generate image based on provider
            if provider == 'ec2-flux' or provider.startswith('ec2-flux'):
                result = generate_with_ec2_flux(prompt, image_config, provider=provider)
            elif provider == 'ec2-sd35' or provider.startswith('ec2-sd35'):
                result = generate_with_ec2_sd35(prompt, image_config)
            elif provider == 'ec2-zimage' or provider.startswith('ec2-zimage'):
                result = generate_with_ec2_zimage(prompt, image_config)
            elif provider == 'aws-bedrock-sdxl':
                result = generate_with_bedrock_sdxl(prompt, image_config)
            else:
                print(f"  Unknown provider '{provider}', falling back to EC2 FLUX")
                result = generate_with_ec2_flux(prompt, image_config, provider=provider)

            # Upload to S3
            upload_result = upload_to_s3(
                result['image_bytes'],
                channel_id,
                content_id,
                scene_number
            )

            # Add to results with channel routing info
            scene_image = {
                'channel_id': channel_id,
                'content_id': content_id,
                'scene_index': scene_index,
                'scene_number': scene_number,
                'image_url': upload_result['s3_url'],
                'https_url': upload_result['https_url'],
                'prompt': prompt,
                'negative_prompt': negative_prompt,
                'provider': result['provider'],
                'generated_at': datetime.utcnow().isoformat() + 'Z',
                'width': result['width'],
                'height': result['height'],
                'status': 'completed',
                'cost_usd': float(result['cost'])
            }

            scene_images.append(scene_image)
            total_cost += result['cost']

            print(f" Image {i+1} generated successfully (${result['cost']:.4f})")

        except Exception as e:
            print(f" Failed to generate image {i+1}: {str(e)}")

            # Add failed entry
            scene_images.append({
                'channel_id': channel_id,
                'content_id': content_id,
                'scene_index': scene_index,
                'scene_number': scene_number,
                'prompt': prompt,
                'status': 'failed',
                'error': str(e),
                'generated_at': datetime.utcnow().isoformat() + 'Z'
            })

    print(f"\n Multi-channel batch completed!")
    print(f"   Generated: {len([img for img in scene_images if img.get('status') == 'completed'])} images")
    print(f"   Failed: {len([img for img in scene_images if img.get('status') == 'failed'])} images")
    print(f"   Total cost: ${total_cost:.4f}")

    # Log costs per channel to CostTracking table
    if total_cost > 0:
        # Group images by channel to log costs separately
        from collections import defaultdict
        channel_costs = defaultdict(lambda: {'images': 0, 'cost': 0.0, 'content_id': None})

        for img in scene_images:
            if img.get('status') == 'completed':
                channel_id = img.get('channel_id')
                content_id = img.get('content_id')
                cost = img.get('cost_usd', 0.0)

                channel_costs[channel_id]['images'] += 1
                channel_costs[channel_id]['cost'] += cost
                if not channel_costs[channel_id]['content_id']:
                    channel_costs[channel_id]['content_id'] = content_id

        # Log cost for each channel
        print(f" Logging costs to CostTracking table...")
        for channel_id, data in channel_costs.items():
            if data['images'] > 0:
                try:
                    log_image_cost(
                        channel_id=channel_id,
                        content_id=data['content_id'],
                        provider=provider,
                        num_images=data['images'],
                        cost_per_image=data['cost'] / data['images'],
                        user_id=user_id
                    )
                    print(f"    Logged {data['images']} images for {channel_id[-6:]}: ${data['cost']:.4f}")
                except Exception as e:
                    print(f"    Failed to log costs for {channel_id}: {e}")

    return {
        'scene_images': scene_images,
        'total_cost_usd': float(round(total_cost, 6)),
        'images_generated': len([img for img in scene_images if img.get('status') == 'completed']),
        'images_failed': len([img for img in scene_images if img.get('status') == 'failed']),
        'provider': provider
    }

def lambda_handler(event, context):
    """
    Generate images for narrative scenes using selected provider

    BATCHING MODE:
    - Supports batch_mode=true to process scenes in batches
    - Reduces timeout issues for large scene counts
    - Each batch processes up to batch_size scenes (default: 6)

    Input:
    {
        "channel_id": "UCxxxx",
        "narrative_id": "20251106123000",
        "story_title": "Horror Story",
        "scenes": [
            {
                "id": 1,
                "paragraph_text": "...",
                "image_prompt": "Dark haunted house..."
            }
        ],
        "batch_mode": true,  # Optional: enable batching
        "batch_size": 6,     # Optional: scenes per batch (default: 6)
        "batch_index": 0     # Optional: which batch to process (0-based)
    }

    Output:
    {
        "scene_images": [
            {
                "scene_id": 1,
                "image_url": "s3://bucket/images/...",
                "https_url": "https://...",
                "prompt": "...",
                "provider": "aws-bedrock-sdxl",
                "generated_at": "2025-11-06T12:00:00Z",
                "width": 1024,
                "height": 1024,
                "status": "completed",
                "cost_usd": 0.018
            }
        ],
        "total_cost_usd": 0.234,
        "images_generated": 13,
        "batch_info": {  # Only if batch_mode=true
            "batch_index": 0,
            "batch_size": 6,
            "total_batches": 3,
            "scenes_in_batch": 6
        }
    }
    """
    print(f" Image Generator - Multi-Provider Version with BATCHING")
    print(f"Event: {json.dumps(event, ensure_ascii=False, default=decimal_default)}")

    # Extract user_id for multi-tenant cost tracking
    user_id = event.get('user_id')
    if user_id:
        print(f" User ID: {user_id}")
    else:
        print(f"  WARNING: No user_id provided - costs will be logged without user association")

    # MULTI-CHANNEL BATCH MODE: Check if all_prompts is present (optimized multi-channel mode)
    all_prompts = event.get('all_prompts')
    multi_channel_mode = all_prompts is not None

    if multi_channel_mode:
        print(f" MULTI-CHANNEL BATCH MODE DETECTED")
        print(f"   Total prompts from all channels: {len(all_prompts)}")

        # Extract provider and EC2 endpoint from event (passed by Step Functions)
        provider = event.get('provider', 'ec2-flux')

        # Set global EC2 endpoint if provided
        global EC2_ENDPOINT
        EC2_ENDPOINT = event.get('ec2_endpoint')
        if EC2_ENDPOINT:
            print(f" EC2 endpoint received from Step Functions")

        # Wait for Z-Image service to be ready (EC2 may be running but service still starting)
        if EC2_ENDPOINT:
            wait_for_image_service(EC2_ENDPOINT, max_wait=120)

        # Process all prompts and return scene_images for distribution
        return handle_multi_channel_batch(all_prompts, provider, user_id)

    # SINGLE CHANNEL MODE (original logic)
    channel_id = event.get('channel_id', 'Unknown')
    narrative_id = event.get('narrative_id', 'Unknown')
    story_title = event.get('story_title', 'Untitled')
    scenes = event.get('scenes', [])

    # BATCHING support
    batch_mode = event.get('batch_mode', False)
    batch_size = event.get('batch_size', 6)  # Default: 6 scenes per batch
    batch_index = event.get('batch_index', 0)  # Which batch to process

    total_scenes = len(scenes)
    total_batches = (total_scenes + batch_size - 1) // batch_size  # Ceiling division

    if batch_mode:
        # Calculate batch boundaries
        start_idx = batch_index * batch_size
        end_idx = min(start_idx + batch_size, total_scenes)
        scenes_to_process = scenes[start_idx:end_idx]

        print(f" BATCH MODE ENABLED")
        print(f"   Total scenes: {total_scenes}")
        print(f"   Batch size: {batch_size}")
        print(f"   Total batches: {total_batches}")
        print(f"   Current batch: {batch_index + 1}/{total_batches}")
        print(f"   Processing scenes: {start_idx + 1} to {end_idx}")
    else:
        scenes_to_process = scenes
        print(f" Processing ALL {total_scenes} scenes (no batching)")

    try:
        # 1. Get channel config
        channel_table = dynamodb.Table('ChannelConfigs')
        channel_response = channel_table.query(
            IndexName='channel_id-index',
            KeyConditionExpression=Key('channel_id').eq(channel_id)
        )

        if not channel_response.get('Items'):
            raise Exception(f'Channel config not found for {channel_id}')

        channel_config = channel_response['Items'][0]
        print(f" Channel config loaded: {channel_config.get('channel_name', 'Unknown')}")

        # 2. Get image generation settings from channel config
        image_settings = channel_config.get('image_generation', {})
        provider = image_settings.get('provider', 'vast-ai-flux')  # Default to Vast.ai FLUX (Bedrock SDXL not available in eu-central-1)
        quality = image_settings.get('quality', 'standard')
        width = image_settings.get('width', 1024)
        height = image_settings.get('height', 576)  # FLUX default 16:9 aspect ratio

        print(f" Image provider: {provider}")
        print(f"   Quality: {quality}, Size: {width}x{height}")

        # 3. Get API keys if needed
        api_keys = {}
        if provider.startswith('replicate'):
            try:
                secret = secrets_client.get_secret_value(SecretId='replicate/api-key')
                api_keys['replicate'] = json.loads(secret['SecretString']).get('api_key')
            except:
                print("  Replicate API key not found")

        if provider.startswith('vast-ai'):
            try:
                secret = secrets_client.get_secret_value(SecretId='vast-ai/config')
                vast_config = json.loads(secret['SecretString'])
                api_keys['vast_ai'] = vast_config
            except:
                print("  Vast.ai config not found")

        # 4. Auto-start Vast.ai instance if using vast-ai provider
        vast_instance_started = False
        control_api_url = 'https://xmstnomewqj2zlhrgkqxnnhkz40znusc.lambda-url.eu-central-1.on.aws'

        if provider.startswith('vast-ai') and 'vast_ai' in api_keys:
            print("\n Checking Vast.ai instance status...")
            is_running = check_vast_instance_status(control_api_url)

            if not is_running:
                print("Instance is stopped, starting it now...")
                start_vast_instance_and_wait(control_api_url, max_wait=120)
                vast_instance_started = True
                print("Instance ready for image generation!")
            else:
                print("Instance already running")

        # 4b. Auto-start EC2 SD35 instance if using ec2-sd35 provider
        ec2_instance_started = False
        
        if provider.startswith('ec2-sd35'):
            print("Auto-starting EC2 SD35 instance...")
            try:
                start_ec2_sd35()
                ec2_instance_started = True
                print("EC2 SD35 instance ready for generation")
            except Exception as e:
                print(f" Failed to start EC2: {e}")
                raise

        # 5. Generate images for each scene
        scene_images = []
        total_cost = 0.0

        image_config = {
            'quality': quality,
            'width': width,
            'height': height,
            'cfg_scale': image_settings.get('cfg_scale', 7),
            'steps': image_settings.get('steps', 50),
            'flux_variant': image_settings.get('flux_variant', 'schnell')
        }

        for scene in scenes_to_process:
            # Support both old and new field names (MEGA mode uses different names)
            scene_id = scene.get('id') or scene.get('scene_number', 0)
            image_prompt = scene.get('image_prompt', '')

            if not image_prompt:
                print(f"  Scene {scene_id} has no image_prompt, skipping")
                continue

            print(f"\n Generating image for scene {scene_id}")
            print(f"   Prompt: {image_prompt[:100]}...")

            try:
                # Select generation method based on provider
                if provider == 'aws-bedrock-sdxl':
                    result = generate_with_bedrock_sdxl(image_prompt, image_config)

                elif provider.startswith('ec2-flux'):
                    result = generate_with_ec2_flux(image_prompt, image_config)

                elif provider.startswith('ec2-sd35'):
                    result = generate_with_ec2_sd35(image_prompt, image_config)


                else:
                    print(f"  Unknown provider '{provider}', falling back to EC2 FLUX")
                    result = generate_with_ec2_flux(image_prompt, image_config)

                # Upload to S3
                upload_result = upload_to_s3(
                    result['image_bytes'],
                    channel_id,
                    narrative_id,
                    scene_id
                )

                # Add to results
                scene_image = {
                    'scene_id': scene_id,
                    'image_url': upload_result['s3_url'],
                    'https_url': upload_result['https_url'],
                    'prompt': image_prompt,
                    'provider': result['provider'],
                    'generated_at': datetime.utcnow().isoformat() + 'Z',
                    'width': result['width'],
                    'height': result['height'],
                    'status': 'completed',
                    'cost_usd': float(result['cost'])
                }

                scene_images.append(scene_image)
                total_cost += result['cost']

                print(f" Scene {scene_id} generated successfully (${result['cost']:.4f})")

            except Exception as e:
                print(f" Failed to generate image for scene {scene_id}: {str(e)}")

                # Add failed entry
                scene_images.append({
                    'scene_id': scene_id,
                    'prompt': image_prompt,
                    'status': 'failed',
                    'error': str(e),
                    'generated_at': datetime.utcnow().isoformat() + 'Z'
                })

        # 5. Log total cost
        if total_cost > 0:
            log_image_cost(
                channel_id=channel_id,
                content_id=narrative_id,
                provider=provider,
                num_images=len([img for img in scene_images if img.get('status') == 'completed']),
                cost_per_image=total_cost / len([img for img in scene_images if img.get('status') == 'completed']),
                user_id=user_id
            )

        # 6. Return results
        output = {
            'channel_id': channel_id,
            'narrative_id': narrative_id,
            'story_title': story_title,
            'scene_images': scene_images,
            'total_cost_usd': float(round(total_cost, 6)),
            'images_generated': len([img for img in scene_images if img.get('status') == 'completed']),
            'images_failed': len([img for img in scene_images if img.get('status') == 'failed']),
            'provider': provider
        }

        # Add batch info if in batch mode
        if batch_mode:
            output['batch_info'] = {
                'batch_index': batch_index,
                'batch_size': batch_size,
                'total_batches': total_batches,
                'scenes_in_batch': len(scenes_to_process),
                'batch_range': f"{start_idx + 1}-{end_idx}"
            }

        print(f"\n Image generation completed!")
        print(f"   Generated: {output['images_generated']} images")
        print(f"   Failed: {output['images_failed']} images")
        print(f"   Total cost: ${total_cost:.4f}")

        # 7. Auto-stop Vast.ai instance if we started it
        if vast_instance_started:
            print("\n Auto-stopping Vast.ai instance to save costs...")
            stop_vast_instance(control_api_url)

        # 7b. Auto-stop EC2 SD35 instance if we started it
        if ec2_instance_started:
            print("Auto-stopping EC2 SD35 instance to save costs...")
            stop_ec2_sd35()

        return output

    except Exception as e:
        print(f" ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

        # Stop Vast.ai instance if we started it (even on error to save costs)
        if 'vast_instance_started' in locals() and vast_instance_started:
            print("\n Stopping Vast.ai instance after error to save costs...")
            stop_vast_instance(control_api_url)

        # Stop EC2 SD35 instance if we started it (even on error)
        if 'ec2_instance_started' in locals() and ec2_instance_started:
            print("Stopping EC2 SD35 instance after error to save costs...")
            stop_ec2_sd35()

        error_output = {
            'channel_id': channel_id,
            'narrative_id': narrative_id,
            'scene_images': [],
            'total_cost_usd': float(0.0),
            'images_generated': 0,
            'images_failed': len(scenes_to_process) if 'scenes_to_process' in locals() else len(scenes),
            'error': str(e)
        }

        # Add batch info if in batch mode
        if batch_mode:
            error_output['batch_info'] = {
                'batch_index': batch_index,
                'batch_size': batch_size,
                'total_batches': total_batches,
                'scenes_in_batch': len(scenes_to_process) if 'scenes_to_process' in locals() else 0
            }

        return error_output
