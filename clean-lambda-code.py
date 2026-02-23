#!/usr/bin/env python3
"""
Clean Lambda functions - Remove FLUX/SD3.5/Bedrock code
Keep ONLY ec2-zimage support
"""

import os
import re
import shutil
from datetime import datetime

TIMESTAMP = datetime.now().strftime('%Y%m%d_%H%M%S')

def backup_file(filepath):
    """Create backup of file before modification"""
    backup_path = f"{filepath}.backup_{TIMESTAMP}"
    shutil.copy2(filepath, backup_path)
    print(f"   📦 Backup: {backup_path}")
    return backup_path

def clean_content_generate_images():
    """Clean content-generate-images Lambda - ONLY keep ec2-zimage"""
    filepath = "aws/lambda/content-generate-images/lambda_function.py"

    print(f"\n🔧 Cleaning {filepath}...")

    if not os.path.exists(filepath):
        print(f"   ⏭️  File not found, skipping")
        return

    backup_file(filepath)

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # New cleaned version
    new_content = '''import json
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

'''

    # Find where handle_multi_channel_batch starts (keep it as-is mostly)
    # Find lambda_handler (keep it but simplify)

    # For now, write the cleaned imports and core functions
    # The handle_multi_channel_batch and lambda_handler will need the rest of the original logic

    # Let's find these sections in original
    start_batch = None
    start_handler = None

    for i, line in enumerate(lines):
        if 'def handle_multi_channel_batch' in line:
            start_batch = i
        if 'def lambda_handler' in line:
            start_handler = i

    if start_batch and start_handler:
        # Extract these functions (they're mostly provider-agnostic)
        batch_function = ''.join(lines[start_batch:start_handler])
        handler_function = ''.join(lines[start_handler:])

        # Clean batch_function - remove provider conditionals
        batch_function = re.sub(
            r"if provider == 'ec2-flux'.*?result = generate_with_ec2_flux.*?\n",
            "",
            batch_function,
            flags=re.DOTALL
        )
        batch_function = re.sub(
            r"elif provider.*?'ec2-sd35'.*?result = generate_with_ec2_sd35.*?\n",
            "",
            batch_function
        )
        batch_function = re.sub(
            r"elif provider.*?'aws-bedrock-sdxl'.*?result = generate_with_bedrock_sdxl.*?\n",
            "",
            batch_function
        )
        batch_function = re.sub(
            r"else:.*?print.*?Unknown provider.*?result = generate_with_ec2_flux.*?\n",
            "# Generate using Z-Image\n                result = generate_with_ec2_zimage(prompt, image_config)\n",
            batch_function
        )

        # Clean handler_function
        handler_function = re.sub(
            r"provider = image_settings\.get\('provider', '[^']+'\)",
            "provider = 'ec2-zimage'  # ONLY Z-Image supported",
            handler_function
        )

        # Remove provider selection logic
        handler_function = re.sub(
            r"if provider == 'aws-bedrock-sdxl':.*?result = generate_with_bedrock_sdxl.*?\n",
            "",
            handler_function,
            flags=re.DOTALL
        )
        handler_function = re.sub(
            r"elif provider\.startswith\('ec2-flux'\):.*?result = generate_with_ec2_flux.*?\n",
            "",
            handler_function
        )
        handler_function = re.sub(
            r"elif provider\.startswith\('ec2-sd35'\):.*?result = generate_with_ec2_sd35.*?\n",
            "# Generate using Z-Image\n                result = generate_with_ec2_zimage(image_prompt, image_config)\n",
            handler_function
        )

        new_content += batch_function + handler_function

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)

    original_lines = len(lines)
    new_lines = len(new_content.split('\n'))

    print(f"   ✅ Cleaned: {original_lines} → {new_lines} lines (-{original_lines - new_lines} lines)")

def clean_content_narrative():
    """Update default provider in content-narrative Lambda"""
    filepath = "aws/lambda/content-narrative/lambda_function.py"

    print(f"\n🔧 Cleaning {filepath}...")

    if not os.path.exists(filepath):
        print(f"   ⏭️  File not found, skipping")
        return

    backup_file(filepath)

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Update default provider
    content = re.sub(
        r"image_provider = image_generation_config\.get\('provider', '[^']+'\)",
        "image_provider = image_generation_config.get('provider', 'ec2-zimage')",
        content
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"   ✅ Updated default provider to ec2-zimage")

def clean_collect_image_prompts():
    """Clean collect-image-prompts Lambda"""
    filepath = "aws/lambda/collect-image-prompts/lambda_function.py"

    print(f"\n🔧 Cleaning {filepath}...")

    if not os.path.exists(filepath):
        print(f"   ⏭️  File not found, skipping")
        return

    backup_file(filepath)

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Update any provider defaults
    content = re.sub(
        r"provider = ['\"](?:ec2-flux|ec2-sd35|vast-ai-flux|bedrock-sdxl)['\"]",
        "provider = 'ec2-zimage'",
        content
    )

    content = re.sub(
        r"\.get\(['\"]provider['\"]\s*,\s*['\"][^'\"]*['\"]\)",
        ".get('provider', 'ec2-zimage')",
        content
    )

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"   ✅ Updated provider references")

def main():
    print("=" * 80)
    print("🧹 LAMBDA CODE CLEANUP - Remove FLUX/SD3.5/Bedrock")
    print("=" * 80)

    clean_content_generate_images()
    clean_content_narrative()
    clean_collect_image_prompts()

    print("\n" + "=" * 80)
    print("✅ Lambda code cleanup completed!")
    print("=" * 80)
    print("\nℹ️  Backups created with timestamp:", TIMESTAMP)
    print("\n📋 Next steps:")
    print("   1. Review cleaned files")
    print("   2. Test locally if possible")
    print("   3. Deploy to AWS Lambda")
    print("   4. Test image generation")

if __name__ == "__main__":
    main()
