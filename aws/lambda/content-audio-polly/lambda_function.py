"""
AWS Polly TTS Lambda Function
Generates audio using AWS Polly Neural/Standard engines
"""

import json
import hashlib
import os
from datetime import datetime
from boto3.dynamodb.conditions import Key
import boto3

from tts_common import (
    map_voice_profile_to_actual_voice,
    log_tts_cost
)
from polly_provider import PollyProvider

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
CHANNEL_CONFIGS_TABLE = 'ChannelConfigs'


def lambda_handler(event, context):
    """
    Generate audio files using AWS Polly

    Input event:
    {
        "channel_id": "UCRmO5HB89GW_zjX3dJACfzw",
        "narrative_id": "unique_id",
        "tts_service": "aws_polly_neural",  # or "aws_polly_standard"
        "tts_voice_profile": "matthew_male",
        "scenes": [
            {
                "scene_number": 1,
                "text_with_ssml": "<speak>...</speak>"
            }
        ],
        "story_title": "The Forgotten Goddess"
    }

    Output:
    {
        "message": "Audio generated successfully",
        "provider": "AWS Polly",
        "audio_files": [...],
        "total_duration_ms": 45000,
        "cost_usd": 0.002304
    }
    """

    print(f"🎤 AWS Polly TTS Lambda - v2.0 (Provider Architecture)")
    print(f"Event: {json.dumps(event, default=str)}")

    try:
        # Parse input
        channel_id = event.get('channel_id')
        narrative_id = event.get('narrative_id', hashlib.md5(str(datetime.utcnow()).encode()).hexdigest())
        scenes = event.get('scenes', [])
        story_title = event.get('story_title', 'Untitled')

        # Get TTS configuration
        tts_service = event.get('tts_service', 'aws_polly_neural')
        tts_voice_profile = event.get('tts_voice_profile', 'matthew_male')

        if not channel_id:
            return {
                'error': 'channel_id is required',
                'audio_files': [],
                'total_duration_ms': 0,
                'scene_count': 0
            }

        if not scenes:
            print("⚠️  No scenes provided, returning empty result")
            return {
                'audio_files': [],
                'total_duration_ms': 0,
                'scene_count': 0,
                'message': 'No scenes to process'
            }

        # Initialize Polly provider
        provider = PollyProvider()

        # Map voice profile to actual Polly voice
        voice_id = map_voice_profile_to_actual_voice(tts_voice_profile, tts_service)
        print(f"✅ Voice: {voice_id} (from profile: {tts_voice_profile})")

        # Determine engine
        prefer_neural = 'neural' in tts_service.lower()
        print(f"✅ Engine preference: {'Neural' if prefer_neural else 'Standard'}")

        # Generate audio for each scene
        audio_files = []
        total_characters = 0
        engine_used = 'neural' if prefer_neural else 'standard'

        for scene in scenes:
            scene_id = scene.get('scene_number') or scene.get('id', 0)
            ssml_text = scene.get('scene_narration') or scene.get('text_with_ssml') or scene.get('ssml_text', '')

            if not ssml_text:
                print(f"⚠️  Scene {scene_id} has no SSML text, skipping")
                continue

            print(f"🎙️  Generating audio for scene {scene_id}...")

            # Synthesize speech
            audio_data, duration_ms, characters, engine = provider.synthesize_speech(
                text=ssml_text,
                voice_id=voice_id,
                text_type='ssml',
                prefer_neural=prefer_neural
            )

            total_characters += characters
            engine_used = engine  # Track actual engine used

            # Upload to S3
            s3_key = f"narratives/{channel_id}/{narrative_id}/scene_{scene_id}.mp3"
            s3_url = provider.upload_to_s3(audio_data, s3_key)

            audio_files.append({
                'scene_id': scene_id,
                's3_url': s3_url,
                's3_key': s3_key,
                'duration_ms': duration_ms,
                'ssml_used': ssml_text,
                'voice_id': voice_id,
                'engine': engine
            })

            print(f"   ✅ Scene {scene_id}: {duration_ms}ms, {characters} chars, {engine} engine")

        # Calculate totals
        total_duration_ms = sum(af['duration_ms'] for af in audio_files)
        total_duration_sec = total_duration_ms / 1000

        # Get pricing and log cost
        pricing = provider.get_pricing(engine_used)
        cost_usd = log_tts_cost(
            channel_id=channel_id,
            content_id=narrative_id,
            service_name='AWS Polly',
            units=total_characters,
            cost_per_unit=pricing['cost_per_unit'],
            unit_type='characters',
            engine=engine_used
        )

        print(f"\n✅ Generated {len(audio_files)} audio files")
        print(f"   Total duration: {total_duration_sec:.2f}s")
        print(f"   Total characters: {total_characters}")
        print(f"   Engine: {engine_used}")
        print(f"   Cost: ${cost_usd:.6f}")

        return {
            'message': 'Audio generated successfully',
            'provider': 'AWS Polly',
            'narrative_id': narrative_id,
            'channel_id': channel_id,
            'story_title': story_title,
            'voice_id': voice_id,
            'voice_profile': tts_voice_profile,
            'tts_service': tts_service,
            'engine_used': engine_used,
            'audio_files': audio_files,
            'total_duration_ms': total_duration_ms,
            'total_duration_sec': round(total_duration_sec, 2),
            'scene_count': len(audio_files),
            'cost_usd': cost_usd,
            'total_characters': total_characters,
            'api_version': 'provider_v2'
        }

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

        return {
            'error': 'Failed to generate audio',
            'message': str(e),
            'provider': 'AWS Polly',
            'audio_files': [],
            'total_duration_ms': 0,
            'total_duration_sec': 0,
            'scene_count': 0
        }
