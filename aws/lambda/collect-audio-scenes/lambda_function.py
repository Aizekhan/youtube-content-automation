"""
Collect Audio Scenes Lambda
Збирає всі audio scenes з усіх каналів для паралельного батчингу
"""
import json
import boto3
from datetime import datetime

dynamodb = boto3.client('dynamodb')

def lambda_handler(event, context):
    """
    INPUT:
    {
      "channels_data": [
        {
          "channel_item": { "channel_id": "UCxxx" },
          "narrativeResult": {
            "Payload": {
              "content_id": "temp_xxx",
              "narrative_data": { "scenes": [...] },
              "voice_config": { "language": "en", "speaker": "default", ... }
            }
          }
        }
      ]
    }

    OUTPUT:
    {
      "all_audio_scenes": [
        {
          "channel_id": "UCxxx",
          "content_id": "temp_xxx",
          "narrative_id": "...",
          "scene_index": 0,
          "scene_id": "scene_1",
          "text": "...",
          "language": "en",
          "speaker": "default",
          "voice_description": "..."
        }
      ],
      "total_scenes": 18,
      "channels_count": 2,
      "ec2_endpoint": "http://..."
    }
    """

    print(f"Collecting audio scenes from all channels")

    channels_data = event.get('channels_data', [])
    all_scenes = []

    # FIX 2026-02-14: Get EC2 endpoint from event parameter (passed from State Machine)
    ec2_endpoint = event.get('ec2_endpoint', '')
    print(f"EC2 endpoint from event: {ec2_endpoint}")

    for channel in channels_data:
        # Extract channel_id from channel_item
        channel_item = channel.get('channel_item', {})
        channel_id = channel_item.get('channel_id')

        # Extract data from narrativeResult.Payload
        narrative_result = channel.get('narrativeResult', {})
        narrative_payload = narrative_result.get('Payload', {})

        content_id = narrative_payload.get('content_id', '')
        # FIX 2026-02-13: Narrative Lambda returns scenes directly in Payload, not nested in narrative_data
        scenes = narrative_payload.get('scenes', [])
        narrative_id = narrative_payload.get('narrative_id', content_id)

        # Extract voice config
        voice_config = narrative_payload.get('voice_config', {})
        language = voice_config.get('language', 'en')
        speaker = voice_config.get('speaker', 'default')
        voice_description = voice_config.get('voice_description', '')

        # FIX 2026-02-14: ec2_endpoint now comes from event, not from narrative_payload

        print(f"Channel {channel_id}: {len(scenes)} scenes, language={language}, speaker={speaker}")

        # Collect all scenes
        for idx, scene in enumerate(scenes):
            scene_id = scene.get('id') or scene.get('scene_number', idx + 1)

            # Get text - prefer plain text over SSML for Qwen3-TTS
            text = scene.get('scene_narration') or scene.get('text', '')

            # Strip SSML tags if present
            if not text and 'text_with_ssml' in scene:
                import re
                text = re.sub(r'<[^>]+>', '', scene['text_with_ssml'])

            if not text:
                print(f"  WARNING: Scene {scene_id} has no text, skipping")
                continue

            all_scenes.append({
                'channel_id': channel_id,
                'content_id': content_id,
                'narrative_id': narrative_id,
                'scene_index': idx,
                'scene_id': str(scene_id),
                'text': text,
                'language': language,
                'speaker': speaker,
                'voice_description': voice_description
            })

    print(f"Collected {len(all_scenes)} audio scenes from {len(channels_data)} channels")
    print(f"EC2 endpoint: {ec2_endpoint}")

    return {
        'statusCode': 200,
        'all_audio_scenes': all_scenes,
        'total_scenes': len(all_scenes),
        'channels_count': len(channels_data),
        'ec2_endpoint': ec2_endpoint
    }
