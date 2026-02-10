import json
import boto3
import hashlib
import requests
from datetime import datetime
from decimal import Decimal
from boto3.dynamodb.conditions import Key

lambda_client = boto3.client('lambda', region_name='eu-central-1')
s3 = boto3.client('s3', region_name='eu-central-1')
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')

S3_BUCKET = 'youtube-automation-audio-files'
COST_TRACKING_TABLE = 'CostTracking'

# Qwen3-TTS Pricing (g4dn.xlarge On-Demand)
QWEN3_PRICING = {
    'hourly_rate': 0.526,  # g4dn.xlarge USD/hour
}

def log_qwen3_cost(channel_id, content_id, generation_time_sec, scene_count, user_id=None):
    """
    Log Qwen3-TTS cost to CostTracking table

    Cost based on EC2 usage time
    """
    try:
        cost_table = dynamodb.Table(COST_TRACKING_TABLE)

        # Calculate cost based on generation time
        hourly_rate = QWEN3_PRICING['hourly_rate']
        total_cost = Decimal(str((generation_time_sec / 3600) * hourly_rate))

        # Log to CostTracking
        now = datetime.utcnow()
        date_str = now.strftime('%Y-%m-%d')
        timestamp = now.isoformat() + 'Z'

        item = {
            'date': date_str,
            'timestamp': timestamp,
            'service': 'Qwen3-TTS (EC2)',
            'operation': 'audio_generation',
            'channel_id': channel_id,
            'content_id': content_id,
            'cost_usd': total_cost,
            'units': scene_count,
            'details': {
                'generation_time_sec': generation_time_sec,
                'instance_type': 'g4dn.xlarge',
                'scenes': scene_count
            }
        }

        # Add user_id for multi-tenant cost tracking
        if user_id:
            item['user_id'] = user_id
        else:
            print("⚠️ WARNING: Cost logged without user_id")

        cost_table.put_item(Item=item)

        print(f"✅ Logged Qwen3-TTS cost: ${float(total_cost):.6f} ({generation_time_sec}s, {scene_count} scenes)")
        return float(total_cost)

    except Exception as e:
        print(f"❌ Failed to log cost: {str(e)}")
        return 0.0


def lambda_handler(event, context):
    """
    Generate audio files using Qwen3-TTS on EC2

    Input: Same format as content-audio-tts
    {
        "channel_id": "UCxxxx",
        "narrative_id": "unique_id",
        "scenes": [
            {
                "id": 1,
                "scene_narration": "Text to synthesize",
                "text_with_ssml": "<speak>SSML text</speak>"  (optional)
            }
        ],
        "story_title": "Title",
        "user_id": "user_123",
        "language": "English",  (optional, default: English)
        "speaker": "Ryan"  (optional, default: Ryan)
    }

    Output: Same format as content-audio-tts
    {
        "message": "Audio generated successfully",
        "audio_files": [...],
        "voice_id": "Ryan",
        "voice_profile": "deep_male",
        "tts_service": "qwen3_tts",
        "total_duration_ms": 45000,
        "cost_usd": 0.02
    }
    """

    print(f"🎤 Qwen3-TTS Audio Generation")
    print(f"Event: {json.dumps(event, default=str)}")

    # Extract user_id for multi-tenant cost isolation
    user_id = event.get('user_id')
    if not user_id:
        print("⚠️ WARNING: No user_id provided")

    try:
        # Parse input
        channel_id = event.get('channel_id')
        narrative_id = event.get('narrative_id', hashlib.md5(str(datetime.utcnow()).encode()).hexdigest())
        scenes = event.get('scenes', [])
        story_title = event.get('story_title', 'Untitled')
        language = event.get('language', 'English')
        speaker = event.get('speaker', 'Ryan')  # Default Qwen3 speaker
        voice_description = event.get('voice_description')  # NEW: Tone + Narration Style

        if not channel_id:
            return {
                'error': 'channel_id is required',
                'audio_files': [],
                'total_duration_ms': 0,
                'scene_count': 0
            }

        if not scenes:
            print("⚠️ No scenes provided, returning empty result")
            return {
                'audio_files': [],
                'total_duration_ms': 0,
                'scene_count': 0,
                'message': 'No scenes to process'
            }

        # 1. Ensure EC2 is running
        print("🔄 Starting EC2 Qwen3-TTS instance...")
        ec2_endpoint = start_ec2_instance()

        if not ec2_endpoint:
            raise Exception("Failed to start EC2 instance")

        print(f"✅ EC2 endpoint: {ec2_endpoint}")

        # 2. Generate audio for each scene
        audio_files = []
        generation_start = datetime.utcnow()

        for scene in scenes:
            scene_id = scene.get('id') or scene.get('scene_number', 0)

            # Get text - prefer plain text over SSML for Qwen3-TTS
            text = scene.get('scene_narration') or scene.get('text', '')

            # Strip SSML tags if present (Qwen3 uses plain text)
            if not text and 'text_with_ssml' in scene:
                import re
                text = re.sub(r'<[^>]+>', '', scene['text_with_ssml'])

            if not text:
                print(f"⚠️ Scene {scene_id} has no text, skipping")
                continue

            print(f"Generating audio for scene {scene_id}...")

            try:
                # Call Qwen3-TTS API on EC2
                audio_data, duration_ms = generate_with_qwen3(
                    ec2_endpoint=ec2_endpoint,
                    text=text,
                    language=language,
                    speaker=speaker,
                    voice_description=voice_description
                )

                # Upload to S3
                s3_key = f"narratives/{channel_id}/{narrative_id}/scene_{scene_id}.wav"
                s3_url = upload_to_s3(audio_data, s3_key, content_type='audio/wav')

                audio_files.append({
                    'scene_id': scene_id,
                    's3_url': s3_url,
                    's3_key': s3_key,
                    'duration_ms': duration_ms
                })

                print(f"✅ Scene {scene_id} audio generated: {duration_ms}ms")

            except Exception as scene_error:
                print(f"❌ Error generating scene {scene_id}: {scene_error}")
                continue

        # Calculate total generation time
        generation_end = datetime.utcnow()
        generation_time_sec = (generation_end - generation_start).total_seconds()

        # Calculate total duration
        total_duration_ms = sum(af['duration_ms'] for af in audio_files)
        total_duration_sec = total_duration_ms / 1000

        # Log Qwen3-TTS cost
        cost_usd = log_qwen3_cost(
            channel_id=channel_id,
            content_id=narrative_id,
            generation_time_sec=generation_time_sec,
            scene_count=len(audio_files),
            user_id=user_id
        )

        print(f"✅ Generated {len(audio_files)} audio files in {generation_time_sec:.2f}s")
        print(f"Total audio duration: {total_duration_sec:.2f}s, Cost: ${cost_usd:.6f}")

        return {
            'message': 'Audio generated successfully',
            'narrative_id': narrative_id,
            'channel_id': channel_id,
            'story_title': story_title,
            'voice_id': speaker,
            'voice_profile': speaker.lower() + '_voice',  # Map to profile
            'tts_service': 'qwen3_tts',
            'language': language,
            'audio_files': audio_files,
            'total_duration_ms': total_duration_ms,
            'total_duration_sec': round(total_duration_sec, 2),
            'scene_count': len(audio_files),
            'cost_usd': cost_usd,
            'generation_time_sec': round(generation_time_sec, 2),
            'provider': 'Qwen3-TTS-0.6B',
            'api_version': 'qwen3_v1'
        }

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

        return {
            'error': 'Failed to generate audio with Qwen3-TTS',
            'message': str(e),
            'audio_files': [],
            'total_duration_ms': 0,
            'scene_count': 0
        }


def start_ec2_instance():
    """
    Start EC2 Qwen3-TTS instance via ec2-qwen3-control Lambda

    Returns: EC2 endpoint URL or None
    """
    try:
        print("🔄 Invoking ec2-qwen3-control Lambda...")

        response = lambda_client.invoke(
            FunctionName='ec2-qwen3-control',
            InvocationType='RequestResponse',
            Payload=json.dumps({'action': 'start'})
        )

        result = json.loads(response['Payload'].read())

        print(f"EC2 control response: {json.dumps(result)}")

        if result.get('statusCode') == 200 and result.get('status') == 'running':
            endpoint = result.get('endpoint')
            print(f"✅ EC2 running: {endpoint}")
            return endpoint

        elif result.get('statusCode') == 202:
            # Instance starting, wait and retry
            endpoint = result.get('endpoint')
            print(f"⏳ EC2 starting, waiting for service...")

            import time
            max_wait = 180  # 3 minutes max wait
            wait_interval = 10
            waited = 0

            while waited < max_wait:
                time.sleep(wait_interval)
                waited += wait_interval

                # Check if service is ready
                if check_service_health(endpoint):
                    print(f"✅ Service ready after {waited}s")
                    return endpoint

                print(f"⏳ Still waiting... ({waited}s/{max_wait}s)")

            print(f"⚠️ Service not ready after {max_wait}s, proceeding anyway")
            return endpoint

        else:
            print(f"❌ Unexpected EC2 control response: {result}")
            return None

    except Exception as e:
        print(f"❌ Error starting EC2: {e}")
        import traceback
        traceback.print_exc()
        return None


def check_service_health(endpoint):
    """Check if Qwen3-TTS service is healthy"""
    try:
        health_url = f"{endpoint}/health"
        response = requests.get(health_url, timeout=5)

        if response.status_code == 200:
            data = response.json()
            models_loaded = data.get('models_loaded', 0)
            return models_loaded >= 3

        return False

    except Exception as e:
        return False


def generate_with_qwen3(ec2_endpoint, text, language='English', speaker='Ryan', voice_description=None):
    """
    Generate audio using Qwen3-TTS API on EC2

    Returns: (audio_data, duration_ms)
    """
    try:
        url = f"{ec2_endpoint}/tts/generate"

        payload = {
            'scenes': [{'scene_number': 1, 'scene_narration': text}],
            'channel_id': 'temp',
            'narrative_id': 'temp',
            'language': language,
            'speaker': speaker
        }
        
        if voice_description:
            payload['voice_description'] = voice_description

        print(f"Calling Qwen3-TTS API: {url}")

        response = requests.post(url, json=payload, timeout=120)

        if response.status_code != 200:
            raise Exception(f"Qwen3-TTS API error: {response.status_code} - {response.text}")

        result = response.json()

        audio_files = result.get('audio_files', [])
        if not audio_files:
            raise Exception("No audio files returned from Qwen3-TTS")

        # Download audio from S3
        first_audio = audio_files[0]
        s3_key = first_audio['s3_key']
        duration_ms = first_audio['duration_ms']

        # Get audio data from S3
        s3_response = s3.get_object(Bucket=S3_BUCKET, Key=s3_key)
        audio_data = s3_response['Body'].read()

        # Delete temporary S3 file
        s3.delete_object(Bucket=S3_BUCKET, Key=s3_key)

        return audio_data, duration_ms

    except Exception as e:
        print(f"❌ Error calling Qwen3-TTS API: {e}")
        raise


def upload_to_s3(audio_data, s3_key, content_type='audio/wav'):
    """Upload audio file to S3"""
    try:
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=s3_key,
            Body=audio_data,
            ContentType=content_type
        )

        s3_url = f"s3://{S3_BUCKET}/{s3_key}"
        return s3_url

    except Exception as e:
        print(f"❌ Error uploading to S3: {str(e)}")
        raise
