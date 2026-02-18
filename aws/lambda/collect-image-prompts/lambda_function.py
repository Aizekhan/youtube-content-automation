"""
Collect Image Prompts Lambda
Collects all image prompts from all channels for centralized batching
"""
import json
import boto3
import os
from datetime import datetime

dynamodb = boto3.client('dynamodb')
INTERMEDIATE_TABLE = 'IntermediateContent'

def lambda_handler(event, context):
    """
    INPUT:
    {
      "channels_data": [
        {
          "channel_id": "UCxxx",       # top-level from Phase1 Map output
          "narrativeResult": {
            "data": {                   # ResultSelector wraps Payload as "data"
              "content_id": "...",
              "image_data": { "scenes": [...] },
              "image_provider": "ec2-sd35"
            }
          }
        }
      ]
    }

    OUTPUT:
    {
      "all_image_prompts": [...],
      "total_images": 15,
      "channels_count": 2,
      "provider": "ec2-sd35",
      "providers_used": {"ec2-sd35": 2}
    }
    """

    print("Collecting image prompts from all channels")

    channels_data = event.get('channels_data', [])
    all_prompts = []
    providers_count = {}

    for channel in channels_data:
        # channel_id is at top level of Phase1 Map output
        channel_id = channel.get('channel_id')

        # narrativeResult.data (ResultSelector: {"data.$": "$.Payload"})
        narrative_result = channel.get('narrativeResult', {})
        narrative_payload = narrative_result.get('data', {})

        content_id = narrative_payload.get('content_id', '')
        image_data = narrative_payload.get('image_data', {})
        thumbnail_data = narrative_payload.get('thumbnail_data', {})
        scenes = image_data.get('scenes', [])

        # Extract provider from narrative output
        image_provider = narrative_payload.get('image_provider', 'ec2-sd35')

        # Count providers
        providers_count[image_provider] = providers_count.get(image_provider, 0) + 1

        print(f"Channel {channel_id}: {len(scenes)} scenes, provider: {image_provider}")

        # Add scene images
        for idx, scene in enumerate(scenes):
            all_prompts.append({
                'channel_id': channel_id,
                'content_id': content_id,
                'scene_index': idx,
                'prompt': scene.get('image_prompt', ''),
                'negative_prompt': scene.get('negative_prompt', ''),
                'scene_number': scene.get('scene_number', idx + 1),
                'image_type': 'scene'
            })

        # Add thumbnail image
        thumbnail_prompt = thumbnail_data.get('thumbnail_prompt', '')
        if thumbnail_prompt:
            all_prompts.append({
                'channel_id': channel_id,
                'content_id': content_id,
                'scene_index': 999,  # Special index for thumbnail
                'prompt': thumbnail_prompt,
                'negative_prompt': thumbnail_data.get('negative_prompt', ''),
                'scene_number': 0,  # Thumbnail is scene 0
                'image_type': 'thumbnail'
            })
            print(f"  Added thumbnail for {channel_id}")

    # Determine unified provider
    if len(providers_count) == 0:
        unified_provider = 'none'
        print("No channels found, no images to generate")
    elif len(providers_count) == 1:
        unified_provider = list(providers_count.keys())[0]
        print(f"All channels use unified provider: {unified_provider}")
    else:
        first_provider = list(providers_count.keys())[0]
        unified_provider = first_provider
        print(f"Multiple providers detected: {providers_count}")
        print(f"Using first channel provider: {unified_provider}")

    print(f"Collected {len(all_prompts)} image prompts from {len(channels_data)} channels")

    return {
        'all_image_prompts': all_prompts,
        'total_images': len(all_prompts),
        'channels_count': len(channels_data),
        'provider': unified_provider,
        'providers_used': providers_count
    }
