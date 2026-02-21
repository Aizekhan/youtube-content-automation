import json
import boto3
import hashlib
import os
from datetime import datetime
from decimal import Decimal
from io import BytesIO
from boto3.dynamodb.conditions import Key
import sys

# Add shared directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'shared'))
from config_merger import merge_configuration, map_voice_profile_to_actual_voice
from ssml_validator import validate_and_fix_ssml
from ssml_generator import generate_ssml_timeline

s3 = boto3.client('s3', region_name='eu-central-1')
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')

S3_BUCKET = 'youtube-automation-audio-files'
CHANNEL_CONFIGS_TABLE = 'ChannelConfigs'
COST_TRACKING_TABLE = 'CostTracking'

# AWS Polly Pricing (USD) - November 2025

# Voice mapping from profile to AWS Polly voice
VOICE_MAPPING = {
    'authoritative_male': 'Brian',  # British male, authoritative
    'deep_male': 'Matthew',  # US male, deep
    'neutral_male': 'Joey',  # US male, neutral
    'soft_female': 'Emma',  # British female, soft
    'gentle_female': 'Joanna',  # US female, gentle
    'warm_female': 'Amy',  # British female, warm
}

def lambda_handler(event, context):
    """
    Generate audio files for narrative using AWS Polly - Config Merger Version 2.0

    Input:
    {
        "channel_id": "UCRmO5HB89GW_zjX3dJACfzw",
        "narrative_id": "unique_id",
        "scenes": [
            {
                "id": 1,
                "ssml_text": "<speak>...</speak>",
                "paragraph_text": "..."
            }
        ],
        "story_title": "The Forgotten Goddess"
    }

    Output:
    {
        "statusCode": 200,
        "audio_files": [
            {
                "scene_id": 1,
                "s3_url": "s3://bucket/path/scene_1.mp3",
                "duration_ms": 12500
            }
        ],
        "full_audio_url": "s3://bucket/path/full.mp3"
    }
    """

    print(f"🎤 Audio TTS - Config Merger Version 2.0")
    print(f"Event: {json.dumps(event, default=str)}")

    # WEEK 2 FIX: Extract user_id for multi-tenant data isolation
    user_id = event.get('user_id')
    if not user_id:
        print("WARNING: No user_id provided")
        # For backward compatibility during migration
        raise ValueError('SECURITY ERROR: user_id is required for all requests')

    try:
        # Parse input
        channel_id = event.get('channel_id')
        narrative_id = event.get('narrative_id', hashlib.md5(str(datetime.utcnow()).encode()).hexdigest())
        scenes = event.get('scenes', [])
        story_title = event.get('story_title', 'Untitled')

        if not channel_id:
            return {
                'error': 'channel_id is required',
                'audio_files': [],
                'total_duration_ms': 0,
                'total_duration_sec': 0,
                'scene_count': 0
            }

        # Handle empty scenes gracefully (e.g., when narrative generation failed)
        if not scenes:
            print("Warning: No scenes provided, returning empty audio result")
            return {
                'audio_files': [],
                'total_duration_ms': 0,
                'total_duration_sec': 0,
                'scene_count': 0,
                'message': 'No scenes to process'
            }

        # 1. Get channel config
        channel_table = dynamodb.Table(CHANNEL_CONFIGS_TABLE)
        channel_response = channel_table.query(
            IndexName='channel_id-index',
            KeyConditionExpression=Key('channel_id').eq(channel_id)
        )

        if not channel_response.get('Items'):
            print(f"Warning: No config found for channel {channel_id}, using defaults")
            # Use defaults
            merged_config = {
                'tts_service': 'aws_polly_neural',
                'tts_voice_profile': 'neutral_male'
            }
        else:
            channel_config = channel_response['Items'][0]
            print(f"✅ Channel config loaded: {channel_config.get('channel_name', 'Unknown')}")

            # Get TTS template
            selected_tts_template = channel_config.get('selected_tts_template', 'tts_universal_v1')
            print(f"🎵 Loading TTS template: {selected_tts_template}")

            tts_table = dynamodb.Table('TTSTemplates')
            tts_response = tts_table.get_item(Key={'template_id': selected_tts_template})

            if 'Item' not in tts_response:
                print(f"⚠️  TTS template '{selected_tts_template}' not found, using defaults")
                tts_template = {}
            else:
                tts_template = tts_response['Item']
                print(f"✅ TTS template loaded: {tts_template.get('template_name', 'Unknown')}")

            # Get TTS config from template
            tts_config = tts_template.get('tts_config', {})
            tts_settings = tts_template.get('tts_settings', {})

            # Voice selection priority: TTS Template → ChannelConfig → Default
            # 1. tts_config.voice_id (manual mode)
            # 2. tts_settings.tts_voice_profile (template level)
            # 3. tts_config.voice_profile (fallback)
            # 4. channel_config.tts_voice_profile (channel level)
            # 5. Default
            template_voice_id = tts_config.get('voice_id')
            template_settings_voice = tts_settings.get('tts_voice_profile')
            template_voice_profile = tts_config.get('voice_profile')
            channel_voice_profile = channel_config.get('tts_voice_profile')

            # Determine final voice profile
            if template_voice_id:
                # Template has explicit voice_id (manual mode)
                final_voice_profile = template_voice_id
                print(f"🎤 Using voice from TTS Template (tts_config.voice_id): {final_voice_profile}")
            elif template_settings_voice:
                # Template has voice in tts_settings
                final_voice_profile = template_settings_voice
                print(f"🎤 Using voice from TTS Template (tts_settings.tts_voice_profile): {final_voice_profile}")
            elif template_voice_profile:
                # Template has voice_profile
                final_voice_profile = template_voice_profile
                print(f"🎤 Using voice from TTS Template (tts_config.voice_profile): {final_voice_profile}")
            elif channel_voice_profile:
                # Fallback to channel config
                final_voice_profile = channel_voice_profile
                print(f"🎤 Using voice from ChannelConfig: {final_voice_profile}")
            else:
                # No voice configured - STOP generation with clear error
                error_msg = (
                    "NO TTS VOICE CONFIGURED!
"
                    "Please configure a voice in one of these locations:
"
                    "  1. TTS Template (tts_config.voice_id or voice_profile)
"
                    "  2. Channel Config (tts_voice_profile)
"
                    "Content generation cannot proceed without a voice selection."
                )
                print(error_msg)
                raise ValueError(error_msg)

            # Merge configs
            merged_config = {
                'tts_service': tts_settings.get('tts_service') or tts_config.get('service') or channel_config.get('tts_service', 'aws_polly_neural'),
                'tts_voice_profile': final_voice_profile,
                'tts_mood_variants': channel_config.get('tts_mood_variants', ''),
                'channel_name': channel_config.get('channel_name', 'Unknown'),
                'scene_variations': tts_template.get('scene_variations', {})
            }

        print(f"✅ Using TTS config:")
        print(f"   Service: {merged_config['tts_service']}")
        print(f"   Voice Profile: {merged_config['tts_voice_profile']}")

        # ========================================
        # PROVIDER ROUTER: Route to appropriate TTS provider
        # ========================================
        tts_service = merged_config['tts_service']

        # Route to Qwen3-TTS if selected
        if tts_service == 'qwen3_tts':
            print(f"🔀 Routing to Qwen3-TTS provider")
            qwen3_result = invoke_qwen3_provider(event, merged_config, user_id)

            if qwen3_result:
                # Qwen3-TTS succeeded
                return qwen3_result
            else:
                # Qwen3-TTS failed, fallback to Polly
                print("⚠️ Qwen3-TTS failed, falling back to AWS Polly")
                print("ERROR: Qwen3-TTS failed and no fallback available")
                raise Exception("Qwen3-TTS provider failed")
                tts_service = 'aws_polly_neural'

        # Continue with AWS Polly (original code)
        # 2. Map voice profile to actual Polly voice using config_merger helper
        voice_id = map_voice_profile_to_actual_voice(
            merged_config['tts_voice_profile'],
            merged_config['tts_service']
        )
        print(f"✅ Mapped to Polly voice: {voice_id}")

        # 3. Check if scenes already have SSML (MEGA mode) or need SSML generation
        # MEGA mode sends scenes with text_with_ssml already populated
        # Old mode sends scenes with scene_narration (plain text) that needs SSML generation
        first_scene = scenes[0] if scenes else {}
        has_ssml = 'text_with_ssml' in first_scene or 'ssml_text' in first_scene

        if has_ssml:
            print(f"✅ Scenes already have SSML markup (MEGA mode), using as-is")
            scenes_with_ssml = scenes
        else:
            print(f"🎙️ Generating SSML markup from plain text...")
            scenes_with_ssml = generate_ssml_timeline(scenes, merged_config)
            print(f"✅ SSML generated for {len(scenes_with_ssml)} scenes")

        # Generate audio for each scene
        audio_files = []
        audio_streams = []
        total_characters = 0
        engine_used = 'neural'  # Track engine used

        for scene in scenes_with_ssml:
            # Support both old and new field names (MEGA mode uses different names)
            scene_id = scene.get('id') or scene.get('scene_number', 0)
            ssml_text = scene.get('ssml_text') or scene.get('text_with_ssml', '')

            if not ssml_text:
                print(f"Warning: Scene {scene_id} has no SSML text, skipping")
                continue

            print(f"Generating audio for scene {scene_id}...")

            # Generate audio with AWS Polly
            audio_stream, duration_ms, characters, engine, final_ssml = synthesize_speech(ssml_text, voice_id)
            total_characters += characters
            engine_used = engine  # Save last engine used

            # Upload to S3
            s3_key = f"narratives/{channel_id}/{narrative_id}/scene_{scene_id}.mp3"
            s3_url = upload_to_s3(audio_stream, s3_key)

            audio_files.append({
                'scene_id': scene_id,
                's3_url': s3_url,
                's3_key': s3_key,
                'duration_ms': duration_ms,
                'ssml_used': final_ssml  # ✅ Save actual SSML used for TTS
            })

            audio_streams.append(audio_stream)

            print(f"✅ Scene {scene_id} audio generated: {s3_url}")

        # Calculate total duration
        total_duration_ms = sum(af['duration_ms'] for af in audio_files)
        total_duration_sec = total_duration_ms / 1000

        # Log Polly cost
        cost_usd = log_polly_cost(
            channel_id=channel_id,
            content_id=narrative_id,
            total_characters=total_characters,
            engine=engine_used,
            user_id=user_id  # WEEK 2 FIX: Multi-tenant cost tracking
        )

        print(f"✅ Generated {len(audio_files)} audio files")
        print(f"Total duration: {total_duration_sec:.2f} seconds")
        print(f"Total characters: {total_characters}, Cost: ${cost_usd:.6f}")

        return {
            'message': 'Audio generated successfully',
            'narrative_id': narrative_id,
            'channel_id': channel_id,
            'story_title': story_title,
            'voice_id': voice_id,
            'voice_profile': merged_config['tts_voice_profile'],  # NEW: track voice profile used
            'tts_service': merged_config['tts_service'],  # NEW: track TTS service used
            'audio_files': audio_files,
            'total_duration_ms': total_duration_ms,
            'total_duration_sec': round(total_duration_sec, 2),
            'scene_count': len(audio_files),
            'cost_usd': cost_usd,
            'total_characters': total_characters,
            'api_version': 'config_merger_v2'  # NEW: mark as v2
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

        return {
            'error': 'Failed to generate audio',
            'message': str(e),
            'audio_files': [],
            'total_duration_ms': 0,
            'total_duration_sec': 0,
            'scene_count': 0
        }


# DEPRECATED: Old voice mapping function - replaced by config_merger.map_voice_profile_to_actual_voice()
# Kept for reference only
# def get_voice_for_channel(channel_id):
#     """Get voice ID from ChannelConfig"""
#     try:
#         table = dynamodb.Table(CHANNEL_CONFIGS_TABLE)
#         response = table.query(
#             IndexName='channel_id-index',
#             KeyConditionExpression='channel_id = :cid',
#             ExpressionAttributeValues={':cid': channel_id}
#         )
#         items = response.get('Items', [])
#         if not items:
#             print(f"Warning: No config found for channel {channel_id}, using default voice")
#             return 'Brian'
#         config = items[0]
#         voice_profile = config.get('tts_voice_profile', 'Brian')
#         valid_polly_voices = [
#             'Matthew', 'Joey', 'Justin', 'Kevin', 'Stephen', 'Russell', 'Brian',
#             'Joanna', 'Kendra', 'Kimberly', 'Salli', 'Ruth', 'Danielle', 'Ivy',
#             'Nicole', 'Emma', 'Amy'
#         ]
#         if voice_profile in valid_polly_voices:
#             print(f"Using direct voice: {voice_profile}")
#             return voice_profile
#         voice_id = VOICE_MAPPING.get(voice_profile, 'Brian')
#         print(f"Mapped profile '{voice_profile}' to voice: {voice_id}")
#         return voice_id
#     except Exception as e:
#         print(f"Error getting voice for channel: {str(e)}")
#         return 'Brian'


def synthesize_speech(ssml_text, voice_id):
    """
    Generate audio from SSML text using AWS Polly
    Returns: (audio_stream, duration_ms, characters, engine, fixed_ssml)
    """
    # Validate and fix SSML using comprehensive validator
    fixed_ssml, is_valid, warnings, errors = validate_and_fix_ssml(ssml_text)

    if warnings:
        print(f"⚠️  SSML warnings: {', '.join(warnings)}")

    if errors:
        print(f"❌ SSML errors: {', '.join(errors)}")
        # Use fixed version anyway - validator auto-fixes most issues

    if fixed_ssml != ssml_text:
        print(f"✅ SSML was auto-fixed")

    ssml_text = fixed_ssml

    try:
        # Try Neural engine first
        try:
                Text=ssml_text,
                TextType='ssml',
                OutputFormat='mp3',
                VoiceId=voice_id,
                Engine='neural',  # Try Neural engine for better quality
                LanguageCode='en-US'
            )
            audio_stream, duration_ms, characters = process_polly_response(response)
            return audio_stream, duration_ms, characters, 'neural', ssml_text
        except Exception as neural_error:
            print(f"Neural engine failed: {str(neural_error)}, trying standard...")
            # Fallback to standard engine
                Text=ssml_text,
                TextType='ssml',
                OutputFormat='mp3',
                VoiceId=voice_id,
                Engine='standard',  # Fallback to standard
                LanguageCode='en-US'
            )
            audio_stream, duration_ms, characters = process_polly_response(response)
            return audio_stream, duration_ms, characters, 'standard', ssml_text
    except Exception as e:
        print(f"Error synthesizing speech: {str(e)}")
        raise


def upload_to_s3(audio_data, s3_key):
    """Upload audio file to S3"""
    try:
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=audio_data,
            ContentType='audio/mpeg'
        )

        s3_url = f"s3://{S3_BUCKET}/{s3_key}"
        return s3_url

    except Exception as e:
        print(f"Error uploading to S3: {str(e)}")
        raise


def invoke_qwen3_provider(event, merged_config, user_id):
    """
    Delegate to Qwen3-TTS Lambda provider

    Args:
        event: Original Lambda event
        merged_config: Merged TTS configuration
        user_id: User ID for multi-tenant tracking

    Returns:
        Audio generation result (same format as Polly) or None on failure
    """
    print("🎤 Invoking Qwen3-TTS provider...")

    try:
        lambda_client = boto3.client('lambda', region_name='eu-central-1')

        # Extract language from config (default: English)
        # Qwen3-TTS supports: Chinese, English, Japanese, Korean, German, French, Russian, Portuguese, Spanish, Italian
        language = merged_config.get('language', 'English')

        # Map voice profile to Qwen3 speaker
        voice_profile = merged_config.get('tts_voice_profile', 'deep_male')
        speaker = map_voice_profile_to_qwen3_speaker(voice_profile)

        # Build voice_description from Tone + Narration Style
        tone = merged_config.get('tone', '')
        narration_style = merged_config.get('narration_style', '')
        voice_description = None
        if tone or narration_style:
            parts = []
            if tone:
                parts.append(tone)
            if narration_style:
                parts.append(narration_style)
            voice_description = '. '.join(parts)
            print(f"   Voice Description: {voice_description}")

        # Prepare payload for Qwen3-TTS Lambda
        payload = {
            'channel_id': event.get('channel_id'),
            'narrative_id': event.get('narrative_id'),
            'scenes': event.get('scenes', []),
            'story_title': event.get('story_title', 'Untitled'),
            'user_id': user_id,
            'language': language,
            'speaker': speaker,
            'voice_description': voice_description
        }

        print(f"   Language: {language}")
        print(f"   Speaker: {speaker} (from profile: {voice_profile})")
        print(f"   Scenes: {len(payload['scenes'])}")

        # Invoke Qwen3-TTS Lambda
        response = lambda_client.invoke(
            FunctionName='content-audio-qwen3tts',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )

        result = json.loads(response['Payload'].read())

        # Check for errors
        if 'error' in result:
            print(f"❌ Qwen3-TTS error: {result.get('error')}")
            print(f"   Message: {result.get('message', 'Unknown error')}")
            return None  # Signal fallback to Polly

        # Success - return result
        print(f"✅ Qwen3-TTS completed successfully")
        print(f"   Generated: {result.get('scene_count', 0)} scenes")
        print(f"   Duration: {result.get('total_duration_sec', 0)}s")
        print(f"   Cost: ${result.get('cost_usd', 0):.6f}")

        return result

    except Exception as e:
        print(f"❌ Error invoking Qwen3-TTS Lambda: {str(e)}")
        import traceback
        traceback.print_exc()
        return None  # Signal fallback to Polly


def map_voice_profile_to_qwen3_speaker(voice_profile):
    """
    Map abstract voice profile to Qwen3-TTS speaker name

    Qwen3-TTS CustomVoice speakers: Ryan, Lily, Emily, Mark, Jane, etc.

    Args:
        voice_profile: Abstract profile (e.g., 'deep_male', 'soft_female')

    Returns:
        Qwen3-TTS speaker name
    """
    profile_to_speaker = {
        # Male voices
        'deep_male': 'Ryan',
        'authoritative_male': 'Ryan',
        'neutral_male': 'Mark',
        'young_male': 'Mark',
        'matthew_male': 'Ryan',
        'joey_male': 'Mark',

        # Female voices
        'soft_female': 'Lily',
        'gentle_female': 'Lily',
        'warm_female': 'Emily',
        'neutral_female': 'Emily',
        'joanna_female': 'Lily',
        'emma_female': 'Emily',

        # Direct Qwen3 speaker names (if user specifies directly)
        'ryan': 'Ryan',
        'lily': 'Lily',
        'emily': 'Emily',
        'mark': 'Mark',
        'jane': 'Jane',
    }

    # Get speaker or default to Ryan
    speaker = profile_to_speaker.get(voice_profile.lower(), 'Ryan')

    return speaker
