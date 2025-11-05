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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'shared'))
from config_merger import merge_configuration, map_voice_profile_to_actual_voice
from ssml_validator import validate_and_fix_ssml

polly = boto3.client('polly', region_name='eu-central-1')
s3 = boto3.client('s3', region_name='eu-central-1')
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')

S3_BUCKET = 'youtube-automation-audio-files'
CHANNEL_CONFIGS_TABLE = 'ChannelConfigs'
COST_TRACKING_TABLE = 'CostTracking'

# AWS Polly Pricing (USD) - November 2025
POLLY_PRICING = {
    'standard': 4.00 / 1_000_000,  # $4 per 1M characters
    'neural': 16.00 / 1_000_000,   # $16 per 1M characters
}

# Voice mapping from profile to AWS Polly voice
VOICE_MAPPING = {
    'authoritative_male': 'Brian',  # British male, authoritative
    'deep_male': 'Matthew',  # US male, deep
    'neutral_male': 'Joey',  # US male, neutral
    'soft_female': 'Emma',  # British female, soft
    'gentle_female': 'Joanna',  # US female, gentle
    'warm_female': 'Amy',  # British female, warm
}

def log_polly_cost(channel_id, content_id, total_characters, engine='neural'):
    """Log AWS Polly cost to CostTracking table"""
    try:
        cost_table = dynamodb.Table(COST_TRACKING_TABLE)

        # Calculate cost
        cost_per_char = POLLY_PRICING.get(engine, POLLY_PRICING['neural'])
        total_cost = Decimal(str(total_characters * cost_per_char))

        # Log to CostTracking
        now = datetime.utcnow()
        date_str = now.strftime('%Y-%m-%d')
        timestamp = now.isoformat() + 'Z'

        cost_table.put_item(
            Item={
                'date': date_str,
                'timestamp': timestamp,
                'service': 'AWS Polly',
                'operation': 'audio_generation',
                'channel_id': channel_id,
                'content_id': content_id,
                'cost_usd': total_cost,
                'units': total_characters,
                'details': {
                    'characters': total_characters,
                    'engine': engine
                }
            }
        )

        print(f"✅ Logged Polly cost: ${float(total_cost):.6f} ({total_characters} characters, {engine})")
        return float(total_cost)
    except Exception as e:
        print(f"❌ Failed to log cost: {str(e)}")
        return 0.0

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

            # For audio-tts, we primarily need channel config (TTS settings)
            # Template would be used if we need SSML rules, but SSML is already in scenes
            # So we'll do a simplified merge - just extract TTS settings from channel
            merged_config = {
                'tts_service': channel_config.get('tts_service', 'aws_polly_neural'),
                'tts_voice_profile': channel_config.get('tts_voice_profile', 'neutral_male'),
                'tts_mood_variants': channel_config.get('tts_mood_variants', ''),
                'channel_name': channel_config.get('channel_name', 'Unknown')
            }

        print(f"✅ Using TTS config:")
        print(f"   Service: {merged_config['tts_service']}")
        print(f"   Voice Profile: {merged_config['tts_voice_profile']}")

        # 2. Map voice profile to actual Polly voice using config_merger helper
        voice_id = map_voice_profile_to_actual_voice(
            merged_config['tts_voice_profile'],
            merged_config['tts_service']
        )
        print(f"✅ Mapped to Polly voice: {voice_id}")

        # Generate audio for each scene
        audio_files = []
        audio_streams = []
        total_characters = 0
        engine_used = 'neural'  # Track engine used

        for scene in scenes:
            scene_id = scene.get('id', 0)
            ssml_text = scene.get('ssml_text', '')

            if not ssml_text:
                print(f"Warning: Scene {scene_id} has no SSML text, skipping")
                continue

            print(f"Generating audio for scene {scene_id}...")

            # Generate audio with AWS Polly
            audio_stream, duration_ms, characters, engine = synthesize_speech(ssml_text, voice_id)
            total_characters += characters
            engine_used = engine  # Save last engine used

            # Upload to S3
            s3_key = f"narratives/{channel_id}/{narrative_id}/scene_{scene_id}.mp3"
            s3_url = upload_to_s3(audio_stream, s3_key)

            audio_files.append({
                'scene_id': scene_id,
                's3_url': s3_url,
                's3_key': s3_key,
                'duration_ms': duration_ms
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
            engine=engine_used
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
    Returns: (audio_stream, duration_ms, characters, engine)
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
            response = polly.synthesize_speech(
                Text=ssml_text,
                TextType='ssml',
                OutputFormat='mp3',
                VoiceId=voice_id,
                Engine='neural',  # Try Neural engine for better quality
                LanguageCode='en-US'
            )
            audio_stream, duration_ms, characters = process_polly_response(response)
            return audio_stream, duration_ms, characters, 'neural'
        except Exception as neural_error:
            print(f"Neural engine failed: {str(neural_error)}, trying standard...")
            # Fallback to standard engine
            response = polly.synthesize_speech(
                Text=ssml_text,
                TextType='ssml',
                OutputFormat='mp3',
                VoiceId=voice_id,
                Engine='standard',  # Fallback to standard
                LanguageCode='en-US'
            )
            audio_stream, duration_ms, characters = process_polly_response(response)
            return audio_stream, duration_ms, characters, 'standard'
    except Exception as e:
        print(f"Error synthesizing speech: {str(e)}")
        raise


def process_polly_response(response):
    """Process Polly API response and extract audio data
    Returns: (audio_stream, duration_ms, characters)
    """
    # Read audio stream
    audio_stream = response['AudioStream'].read()

    # Get metadata if available
    audio_marks = response.get('Markers', [])
    request_characters = response.get('RequestCharacters', 0)

    # Estimate duration (rough approximation)
    # Average speaking rate: ~150 words per minute = ~2.5 words/sec
    # Average word length: ~5 characters
    # So: characters / 12.5 = seconds
    estimated_duration_sec = request_characters / 12.5 if request_characters > 0 else 10
    duration_ms = int(estimated_duration_sec * 1000)

    return audio_stream, duration_ms, request_characters


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
