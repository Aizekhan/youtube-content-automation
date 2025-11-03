import json
import boto3
import hashlib
import os
from datetime import datetime
from io import BytesIO

polly = boto3.client('polly', region_name='eu-central-1')
s3 = boto3.client('s3', region_name='eu-central-1')
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')

S3_BUCKET = 'youtube-automation-audio-files'
CHANNEL_CONFIGS_TABLE = 'ChannelConfigs'

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
    Generate audio files for narrative using AWS Polly

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

    print(f"Event: {json.dumps(event, default=str)}")

    try:
        # Parse input
        channel_id = event.get('channel_id')
        narrative_id = event.get('narrative_id', hashlib.md5(str(datetime.utcnow()).encode()).hexdigest())
        scenes = event.get('scenes', [])
        story_title = event.get('story_title', 'Untitled')

        if not channel_id or not scenes:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'channel_id and scenes are required'})
            }

        # Get voice from ChannelConfig
        voice_id = get_voice_for_channel(channel_id)
        print(f"Using voice: {voice_id} for channel {channel_id}")

        # Generate audio for each scene
        audio_files = []
        audio_streams = []

        for scene in scenes:
            scene_id = scene.get('id', 0)
            ssml_text = scene.get('ssml_text', '')

            if not ssml_text:
                print(f"Warning: Scene {scene_id} has no SSML text, skipping")
                continue

            print(f"Generating audio for scene {scene_id}...")

            # Generate audio with AWS Polly
            audio_stream, duration_ms = synthesize_speech(ssml_text, voice_id)

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

        print(f"✅ Generated {len(audio_files)} audio files")
        print(f"Total duration: {total_duration_sec:.2f} seconds")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Audio generated successfully',
                'narrative_id': narrative_id,
                'channel_id': channel_id,
                'story_title': story_title,
                'voice_id': voice_id,
                'audio_files': audio_files,
                'total_duration_ms': total_duration_ms,
                'total_duration_sec': round(total_duration_sec, 2),
                'scene_count': len(audio_files)
            }, default=str)
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Failed to generate audio',
                'message': str(e)
            })
        }


def get_voice_for_channel(channel_id):
    """Get voice ID from ChannelConfig"""
    try:
        table = dynamodb.Table(CHANNEL_CONFIGS_TABLE)

        # Query using GSI
        response = table.query(
            IndexName='channel_id-index',
            KeyConditionExpression='channel_id = :cid',
            ExpressionAttributeValues={':cid': channel_id}
        )

        items = response.get('Items', [])
        if not items:
            print(f"Warning: No config found for channel {channel_id}, using default voice")
            return 'Brian'  # Default

        config = items[0]

        # Get voice profile (e.g., "authoritative_male")
        voice_profile = config.get('tts_voice_profile', 'authoritative_male')

        # Map to Polly voice
        voice_id = VOICE_MAPPING.get(voice_profile, 'Brian')

        # Check if tts_voice_options has specific voice names
        voice_options = config.get('tts_voice_options', '')
        if voice_options:
            # tts_voice_options might be "Brian, Emma"
            voices = [v.strip() for v in voice_options.split(',')]
            if voices:
                voice_id = voices[0]  # Use first option

        return voice_id

    except Exception as e:
        print(f"Error getting voice for channel: {str(e)}")
        return 'Brian'  # Fallback


def synthesize_speech(ssml_text, voice_id):
    """
    Generate audio from SSML text using AWS Polly Neural
    Returns: (audio_stream, duration_ms)
    """
    try:
        response = polly.synthesize_speech(
            Text=ssml_text,
            TextType='ssml',
            OutputFormat='mp3',
            VoiceId=voice_id,
            Engine='neural',  # Use Neural engine for better quality
            LanguageCode='en-US'
        )

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

        return audio_stream, duration_ms

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
