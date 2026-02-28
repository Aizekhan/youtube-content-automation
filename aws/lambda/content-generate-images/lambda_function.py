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

s3 = boto3.client('s3', region_name='eu-central-1')
secrets_client = boto3.client('secretsmanager', region_name='eu-central-1')
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
cost_table = dynamodb.Table('CostTracking')

def decimal_default(obj):
    """Convert Decimal to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

EC2_ENDPOINT = None
S3_BUCKET = 'youtube-automation-audio-files'
S3_IMAGES_PREFIX = 'images'

PRICING = {
    'ec2-zimage': {
        'hourly_rate': 1.006,
        'images_per_hour': 720
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

        if user_id:
            item['user_id'] = user_id
            print(f"✅ Logged cost for user {user_id}: ${float(total_cost):.6f}")
        else:
            print(f"⚠️  Logging cost WITHOUT user_id: ${float(total_cost):.6f}")

        cost_table.put_item(Item=item)
        return float(total_cost)
    except Exception as e:
        print(f"❌ Failed to log cost: {e}")
        return 0.0

def generate_with_ec2_zimage(prompt, image_config):
    """Generate image using EC2 Z-Image-Turbo"""
    global EC2_ENDPOINT
    try:
        if EC2_ENDPOINT:
            endpoint_data = EC2_ENDPOINT
            if isinstance(endpoint_data, dict) and 'body' in endpoint_data:
                body = endpoint_data['body']
                if isinstance(body, str):
                    body = json.loads(body)
                ec2_endpoint = body.get('endpoint', '')
            elif isinstance(endpoint_data, str):
                ec2_endpoint = endpoint_data
            else:
                ec2_endpoint = endpoint_data.get('endpoint', '')
        else:
            secret = secrets_client.get_secret_value(SecretId='ec2-zimage-endpoint')
            ec2_endpoint = secret['SecretString']

        if ec2_endpoint.startswith('http://'):
            parts = ec2_endpoint.replace('http://', '').split(':')
            api_host = parts[0]
            api_port = int(parts[1].split('/')[0]) if len(parts) > 1 else 5000
        else:
            api_host = ec2_endpoint
            api_port = 5000

        width = int(image_config.get('width', 1024))
        height = int(image_config.get('height', 576))

        request_body = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "steps": int(image_config.get('steps', 4))
        }

        print(f"🎨 Calling Z-Image at {api_host}:{api_port}")

        conn = http.client.HTTPConnection(api_host, api_port, timeout=60)
        headers = {'Content-Type': 'application/json'}

        conn.request('POST', '/generate', body=json.dumps(request_body), headers=headers)
        response = conn.getresponse()
        response_data = response.read()

        if response.status != 200:
            raise Exception(f"Z-Image API Error: {response.status}")

        content_type = response.getheader('Content-Type', '')
        if 'image/png' not in content_type:
            raise Exception(f"Unexpected content type: {content_type}")

        image_bytes = response_data
        cost = PRICING['ec2-zimage']['hourly_rate'] / PRICING['ec2-zimage']['images_per_hour']

        print(f"✅ Image generated ({width}x{height}, ${cost:.6f})")

        return {
            'image_bytes': image_bytes,
            'cost': cost,
            'provider': 'ec2-zimage',
            'width': width,
            'height': height
        }

    except Exception as e:
        print(f"❌ Z-Image generation failed: {e}")
        raise

def wait_for_image_service(endpoint, max_wait=120):
    """Wait for Z-Image service to be ready"""
    import time

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
        return True

    print(f'⏳ Waiting for Z-Image service at {host}:{port}...')
    waited = 0
    interval = 10

    while waited < max_wait:
        try:
            conn = http.client.HTTPConnection(host, port, timeout=5)
            conn.request('GET', '/health')
            resp = conn.getresponse()
            resp.read()
            conn.close()
            print(f'✅ Service ready after {waited}s')
            return True
        except Exception:
            print(f'⏳ Not ready ({waited}/{max_wait}s), retrying...')
        time.sleep(interval)
        waited += interval

    print(f'⚠️  WARNING: Service not ready after {max_wait}s')
    return False

def get_dimensions_from_aspect_ratio(aspect_ratio, resolution_hint=None):
    """Convert aspect ratio to dimensions"""
    if resolution_hint and 'x' in str(resolution_hint):
        parts = str(resolution_hint).split('x')
        return (int(parts[0]), int(parts[1]))

    aspect_ratio_map = {
        '16:9': (1024, 576),
        '9:16': (576, 1024),
        '4:3': (768, 576),
        '1:1': (768, 768),
        '21:9': (1152, 512),
    }

    return aspect_ratio_map.get(aspect_ratio, (1024, 576))

def upload_to_s3(image_bytes, channel_id, narrative_id, scene_id):
    """Upload image to S3"""
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

        print(f"📤 Uploaded: {key}")

        return {
            's3_url': s3_url,
            'https_url': https_url,
            'key': key
        }

    except Exception as e:
        print(f"❌ Upload failed: {e}")
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

                    # Thumbnail dimensions (Templates system removed - use defaults)
                    # IMPORTANT: Dimensions must be divisible by 16 for FLUX
                    aspect_ratio = '16:9'  # YouTube standard
                    resolution = '1920x1088'  # 1088 is divisible by 16 (1080 is NOT)
                    width, height = get_dimensions_from_aspect_ratio(aspect_ratio, resolution)
                    thumbnail_dimensions[channel_id] = (width, height)
                    print(f"    {channel_id[-6:]}: Thumbnail {aspect_ratio} = {width}x{height}")
            except Exception as e:
                print(f"     Failed to load channel config for {channel_id}: {e}")

        # Default image config for scene images
    # IMPORTANT: Dimensions must be divisible by 16 for FLUX
    default_image_config = {
        'quality': 'standard',
        'width': 1920,
        'height': 1088,  # 1088/16=68, 1080/16=67.5 (NOT divisible!)
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
        provider = event.get('provider', 'ec2-zimage')

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
        quality = image_settings.get('quality', 'standard')
        width = image_settings.get('width', 1920)  # Full HD 16:9
        height = image_settings.get('height', 1088)  # 1088/16=68 (divisible by 16 for FLUX)

        print(f" Image provider: {provider}")
        print(f"   Quality: {quality}, Size: {width}x{height}")

        # 3. Get API keys if needed (reserved for future providers)
        api_keys = {}

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
                # Generate image using EC2 Z-Image (FLUX)
                result = generate_with_ec2_zimage(image_prompt, image_config)

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


        # 7b. Auto-stop EC2 SD35 instance if we started it
        if ec2_instance_started:
            print("Auto-stopping EC2 SD35 instance to save costs...")
            stop_ec2_sd35()

        return output

    except Exception as e:
        print(f" ERROR: {str(e)}")
        import traceback
        traceback.print_exc()


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
