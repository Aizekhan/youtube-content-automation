"""
Prepare Image Batches Lambda - WITH EC2 endpoint extraction

Розділяє scenes на батчі для паралельної генерації зображень.
Парсить і передає EC2 endpoint в кожен батч для SD3.5 генерації.
"""

import json


def lambda_handler(event, context):
    """Підготовка батчів зображень для паралельної обробки"""

    print(f"📦 Prepare Image Batches")
    print(f"Event keys: {list(event.keys())}")

    # Extract data
    channel_id = event.get('channel_id', 'Unknown')
    narrative_id = event.get('content_id', event.get('narrative_id', 'Unknown'))
    story_title = event.get('selected_topic', event.get('story_title', 'Untitled'))

    # Get EC2 endpoint (from Step Functions ec2StartResult.Payload)
    ec2_result = event.get('ec2_endpoint', {})
    
    # Parse endpoint from Lambda response
    # ec2_result structure: {"statusCode": 200, "body": "{\"endpoint\": \"http://...\" }"}
    endpoint_url = None
    if isinstance(ec2_result, dict):
        body = ec2_result.get('body')
        if body:
            try:
                if isinstance(body, str):
                    body_parsed = json.loads(body)
                    endpoint_url = body_parsed.get('endpoint')
                else:
                    endpoint_url = body.get('endpoint')
            except json.JSONDecodeError as e:
                print(f"⚠️  Failed to parse ec2_endpoint body: {e}")
        
    print(f"📡 EC2 Endpoint extracted: {endpoint_url}")

    # Get scenes from image_data
    image_data = event.get('image_data', {})
    scenes = image_data.get('scenes', [])

    # Configuration
    batch_size = event.get('batch_size', 6)

    total_scenes = len(scenes)

    if total_scenes == 0:
        print("⚠️  No scenes provided, returning empty batches")
        return {
            'batches': [],
            'total_batches': 0,
            'total_scenes': 0,
            'batch_size': batch_size
        }

    # Calculate total batches needed
    total_batches = (total_scenes + batch_size - 1) // batch_size

    print(f"📊 Batching stats:")
    print(f"   Total scenes: {total_scenes}")
    print(f"   Batch size: {batch_size}")
    print(f"   Total batches: {total_batches}")

    # Create batches
    batches = []

    for batch_idx in range(total_batches):
        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, total_scenes)

        batch_scenes = scenes[start_idx:end_idx]
        scenes_in_batch = len(batch_scenes)

        batch = {
            'batch_index': batch_idx,
            'batch_size': batch_size,
            'channel_id': channel_id,
            'narrative_id': narrative_id,
            'story_title': story_title,
            'scenes': batch_scenes,
            'batch_mode': True,
            'batch_range': f"{start_idx + 1}-{end_idx}",
            'provider': 'ec2-sd35'
        }
        
        # Add endpoint only if we successfully extracted it
        if endpoint_url:
            batch['ec2_api_host'] = endpoint_url
            print(f"   ✅ Batch {batch_idx}: Added endpoint {endpoint_url}")
        else:
            print(f"   ⚠️  Batch {batch_idx}: No endpoint available")

        batches.append(batch)

        print(f"   Batch {batch_idx}: scenes {start_idx + 1}-{end_idx} ({scenes_in_batch} scenes)")

    output = {
        'batches': batches,
        'total_batches': total_batches,
        'total_scenes': total_scenes,
        'batch_size': batch_size,
        'channel_id': channel_id,
        'narrative_id': narrative_id
    }

    print(f"✅ Created {total_batches} batches for {total_scenes} scenes")

    return output
