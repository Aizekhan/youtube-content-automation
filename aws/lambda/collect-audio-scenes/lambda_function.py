"""
Collect Audio Scenes Lambda
Збирає всі audio scenes з усіх каналів для паралельного батчингу
Підтримує multi-voice TTS через narrative_parser для серіалів
"""
import json
import re
import boto3
from datetime import datetime
from narrative_parser import parse_narrative_for_tts, get_character_voices_from_series_state

dynamodb = boto3.client('dynamodb')
series_table = boto3.resource('dynamodb', region_name='eu-central-1').Table('SeriesState')

# DISABLED: Voice description causes unnatural intonation/modulation in Qwen3-TTS
# Use None to get clean, natural voice without style modulation
VOICE_DESCRIPTION = None


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
              "scenes": [...],
              "voice_config": { "language": "en", "speaker": "Ryan" }
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
          "narrative_id": "...",
          "scene_id": "scene_1",
          "text": "...",
          "language": "en",
          "speaker": "Ryan",
          "voice_description": "..."  <- per-scene з variation_used
        }
      ]
    }
    """

    print(f"Collecting audio scenes from all channels")

    channels_data = event.get('channels_data', [])
    all_scenes = []
    all_cta_segments = []

    # FIX 2026-02-14: Get EC2 endpoint from event parameter (passed from State Machine)
    ec2_endpoint = event.get('ec2_endpoint', '')
    print(f"EC2 endpoint from event: {ec2_endpoint}")

    for channel in channels_data:
        # Support both flat format (channel_id at top level) and nested (channel_item.channel_id)
        channel_id = channel.get('channel_id') or channel.get('channel_item', {}).get('channel_id')

        # Support both ResultSelector format (narrativeResult.data) and old (narrativeResult.Payload)
        narrative_result = channel.get('narrativeResult', {})
        narrative_payload = narrative_result.get('data', narrative_result.get('Payload', {}))

        content_id = narrative_payload.get('content_id', '')
        scenes = narrative_payload.get('scenes', [])
        narrative_id = narrative_payload.get('narrative_id', content_id)

        # Extract voice config (set by content-narrative from channel config)
        voice_config = narrative_payload.get('voice_config', {})
        language = voice_config.get('language', 'en')
        speaker = voice_config.get('speaker', 'Ryan') or 'Ryan'

        # Check if this is a series episode (for multi-voice support)
        series_id = channel.get('series_id')
        character_voices = {}

        if series_id:
            print(f"Channel {channel_id}: Series episode detected (series_id={series_id})")
            try:
                response = series_table.get_item(Key={'series_id': series_id})
                if 'Item' in response:
                    series_state = response['Item']
                    character_voices = get_character_voices_from_series_state(series_state)
                    print(f"  Loaded {len(character_voices)} character voices from SeriesState")
            except Exception as e:
                print(f"  WARNING: Failed to load SeriesState for {series_id}: {e}")
                # Fallback to single voice

        print(f"Channel {channel_id}: {len(scenes)} scenes, language={language}, default_speaker={speaker}")

        # Collect all scenes
        for idx, scene in enumerate(scenes):
            scene_id = scene.get('id') or scene.get('scene_number', idx + 1)

            # Get text - prefer plain text over SSML for Qwen3-TTS
            text = scene.get('scene_narration') or scene.get('text', '')

            # Strip SSML tags if present
            if not text and 'text_with_ssml' in scene:
                text = re.sub(r'<[^>]+>', '', scene['text_with_ssml'])

            if not text:
                print(f"  WARNING: Scene {scene_id} has no text, skipping")
                continue

            # Per-scene voice_description based on variation_used (from OpenAI / story blueprint)
            # Keep it simple - just use the base variation description
            # Single voice description for all scenes
            scene_voice_desc = VOICE_DESCRIPTION

            # Multi-voice parsing: if series_id exists and text has character tags
            if series_id and ('[NARRATOR]' in text or re.search(r'\[[A-Z_]+\]', text)):
                print(f"  Scene {scene_id}: Parsing for multi-voice")
                segments = parse_narrative_for_tts(text, scene_id, speaker, character_voices)

                for seg in segments:
                    all_scenes.append({
                        'channel_id': channel_id,
                        'content_id': content_id,
                        'narrative_id': narrative_id,
                        'scene_index': idx,
                        'scene_id': str(scene_id),
                        'segment_index': seg['segment_index'],
                        'character_id': seg['character_id'],
                        'text': seg['text'],
                        'language': language,
                        'speaker': seg['speaker'],
                        'voice_description': scene_voice_desc,
                        'audio_type': 'scene'
                    })
            else:
                # Single voice (no series or no character tags)
                print(f"  Scene {scene_id}: Single voice")
                all_scenes.append({
                    'channel_id': channel_id,
                    'content_id': content_id,
                    'narrative_id': narrative_id,
                    'scene_index': idx,
                    'scene_id': str(scene_id),
                    'text': text,
                    'language': language,
                    'speaker': speaker,
                    'voice_description': scene_voice_desc,
                    'audio_type': 'scene'
                })

        # Collect CTA segments - support both narrative_content.cta_segments and cta_data.cta_segments
        narrative_content = narrative_payload.get('narrative_content', {})
        cta_segments = narrative_content.get('cta_segments', narrative_payload.get('cta_data', {}).get('cta_segments', []))

        print(f"Channel {channel_id}: {len(cta_segments)} CTA segments")

        # CTA uses same voice description
        cta_voice_desc = VOICE_DESCRIPTION

        for idx, cta_segment in enumerate(cta_segments):
            cta_audio_segment = cta_segment.get('cta_audio_segment', {})
            cta_text = cta_audio_segment.get('ssml_text', '')

            if cta_text:
                cta_text_plain = re.sub(r'<[^>]+>', '', cta_text)

                all_cta_segments.append({
                    'channel_id': channel_id,
                    'content_id': content_id,
                    'narrative_id': narrative_id,
                    'scene_index': idx,
                    'scene_id': f"cta_{cta_segment.get('type', idx)}",
                    'text': cta_text_plain,
                    'language': language,
                    'speaker': speaker,
                    'voice_description': cta_voice_desc,
                    'audio_type': 'cta',
                    'cta_type': cta_segment.get('type', 'generic')
                })

    print(f"Collected {len(all_scenes)} audio scenes from {len(channels_data)} channels")
    print(f"Collected {len(all_cta_segments)} CTA segments from {len(channels_data)} channels")
    print(f"EC2 endpoint: {ec2_endpoint}")

    total_audio_files = len(all_scenes) + len(all_cta_segments)

    return {
        'statusCode': 200,
        'all_audio_scenes': all_scenes,
        'all_cta_segments': all_cta_segments,
        'total_scenes': len(all_scenes),
        'total_cta': len(all_cta_segments),
        'total_audio_files': total_audio_files,
        'channels_count': len(channels_data),
        'ec2_endpoint': ec2_endpoint
    }
