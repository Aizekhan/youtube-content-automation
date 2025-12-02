"""
Collect Image Prompts Lambda
Збирає всі image prompts з усіх каналів для централізованого батчингу
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
          "channel_id": "UCxxx",
          "content_id": "temp_xxx",
          "image_data": { "scenes": [...] },
          "image_provider": "ec2-sd35"
        }
      ]
    }

    OUTPUT:
    {
      "all_image_prompts": [
        {
          "channel_id": "UCxxx",
          "content_id": "temp_xxx",
          "scene_index": 0,
          "prompt": "...",
          "narrative_id": "..."
        }
      ],
      "total_images": 15,
      "channels_count": 2,
      "provider": "ec2-sd35",  # Unified provider if all channels use same, otherwise first channel's
      "providers_used": {"ec2-sd35": 2}  # Count per provider
    }
    """

    print(f"🎯 Collecting image prompts from all channels")

    channels_data = event.get('channels_data', [])
    all_prompts = []
    providers_count = {}

    for channel in channels_data:
        # Extract channel_id from channel_item (Phase1 structure)
        channel_item = channel.get('channel_item', {})
        channel_id = channel_item.get('channel_id')

        # Extract data from narrativeResult.Payload
        narrative_result = channel.get('narrativeResult', {})
        narrative_payload = narrative_result.get('Payload', {})

        content_id = narrative_payload.get('content_id', '')
        image_data = narrative_payload.get('image_data', {})
        thumbnail_data = narrative_payload.get('thumbnail_data', {})
        scenes = image_data.get('scenes', [])

        # Extract provider from narrative output
        image_provider = narrative_payload.get('image_provider', 'ec2-sd35')

        # Count providers
        providers_count[image_provider] = providers_count.get(image_provider, 0) + 1

        print(f"📦 Channel {channel_id}: {len(scenes)} scenes + thumbnail, provider: {image_provider}")

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
            print(f"   ✅ Added thumbnail for {channel_id}")

    # Determine unified provider
    if len(providers_count) == 1:
        # All channels use same provider
        unified_provider = list(providers_count.keys())[0]
        print(f"✅ All channels use unified provider: {unified_provider}")
    else:
        # Multiple providers - use first channel's provider
        first_provider = list(providers_count.keys())[0]
        unified_provider = first_provider
        print(f"⚠️  Multiple providers detected: {providers_count}")
        print(f"   Using first channel's provider: {unified_provider}")

    print(f"✅ Collected {len(all_prompts)} image prompts from {len(channels_data)} channels")

    return {
        'statusCode': 200,
        'all_image_prompts': all_prompts,
        'total_images': len(all_prompts),
        'channels_count': len(channels_data),
        'provider': unified_provider,
        'providers_used': providers_count
    }
