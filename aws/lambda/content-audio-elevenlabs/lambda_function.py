"""
ElevenLabs TTS Lambda Function
Generates audio using ElevenLabs API
"""

import json
import hashlib
from datetime import datetime

from tts_common import log_tts_cost
from elevenlabs_provider import ElevenLabsProvider


def lambda_handler(event, context):
    """
    Generate audio files using ElevenLabs

    Input event:
    {
        "channel_id": "UCRmO5HB89GW_zjX3dJACfzw",
        "narrative_id": "unique_id",
        "tts_service": "elevenlabs",
        "tts_voice_profile": "adam_male",
        "elevenlabs_model": "turbo",  # optional: turbo, multilingual, english
        "scenes": [
            {
                "scene_number": 1,
                "text_with_ssml": "<speak>Hello world</speak>"
            }
        ],
        "story_title": "My Story"
    }

    Output:
    {
        "message": "Audio generated successfully",
        "provider": "ElevenLabs",
        "model_used": "eleven_turbo_v2_5",
        "audio_files": [...],
        "total_duration_sec": 12.5,
        "cost_usd": 0.00024
    }
    """

    print(f"🎤 ElevenLabs TTS Lambda - v2.0 (Provider Architecture)")
    print(f"Event: {json.dumps(event, default=str)}")

    try:
        # Parse input
        channel_id = event.get('channel_id')
        narrative_id = event.get('narrative_id', hashlib.md5(str(datetime.utcnow()).encode()).hexdigest())
        scenes = event.get('scenes', [])
        story_title = event.get('story_title', 'Untitled')

        # Get TTS configuration
        tts_voice_profile = event.get('tts_voice_profile', 'adam_male')
        elevenlabs_model = event.get('elevenlabs_model', 'turbo')

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

        # Initialize ElevenLabs provider
        provider = ElevenLabsProvider()

        print(f"✅ Voice profile: {tts_voice_profile}")
        print(f"✅ Model: {elevenlabs_model}")

        # Generate audio for each scene
        audio_files = []
        total_characters = 0
        model_used = None

        for scene in scenes:
            scene_id = scene.get('scene_number') or scene.get('id', 0)
            ssml_text = scene.get('text_with_ssml') or scene.get('ssml_text', '')

            if not ssml_text:
                print(f"⚠️  Scene {scene_id} has no text, skipping")
                continue

            print(f"🎙️  Generating audio for scene {scene_id}...")

            # Synthesize speech (SSML will be stripped automatically)
            audio_data, duration_ms, characters, model_id = provider.synthesize_speech(
                text=ssml_text,
                voice_profile=tts_voice_profile,
                model=elevenlabs_model
            )

            total_characters += characters
            model_used = model_id

            # Upload to S3
            s3_key = f"narratives/{channel_id}/{narrative_id}/scene_{scene_id}.mp3"
            s3_url = provider.upload_to_s3(audio_data, s3_key)

            audio_files.append({
                'scene_id': scene_id,
                's3_url': s3_url,
                's3_key': s3_key,
                'duration_ms': duration_ms,
                'text_used': ssml_text[:100] + '...',  # First 100 chars
                'voice_profile': tts_voice_profile,
                'model': model_id
            })

            print(f"   ✅ Scene {scene_id}: {duration_ms}ms, {characters} chars")

        # Calculate totals
        total_duration_ms = sum(af['duration_ms'] for af in audio_files)
        total_duration_sec = total_duration_ms / 1000

        # Get pricing and log cost
        pricing = provider.get_pricing(model_used)
        cost_usd = log_tts_cost(
            channel_id=channel_id,
            content_id=narrative_id,
            service_name='ElevenLabs',
            units=total_characters,
            cost_per_unit=pricing['cost_per_unit'],
            unit_type='characters',
            engine=model_used,
            additional_details={
                'voice_profile': tts_voice_profile,
                'model': model_used
            }
        )

        print(f"\n✅ Generated {len(audio_files)} audio files")
        print(f"   Total duration: {total_duration_sec:.2f}s")
        print(f"   Total characters: {total_characters}")
        print(f"   Model: {model_used}")
        print(f"   Cost: ${cost_usd:.6f}")

        return {
            'message': 'Audio generated successfully',
            'provider': 'ElevenLabs',
            'narrative_id': narrative_id,
            'channel_id': channel_id,
            'story_title': story_title,
            'voice_profile': tts_voice_profile,
            'tts_service': 'elevenlabs',
            'model_used': model_used,
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
            'provider': 'ElevenLabs',
            'audio_files': [],
            'total_duration_ms': 0,
            'total_duration_sec': 0,
            'scene_count': 0
        }
