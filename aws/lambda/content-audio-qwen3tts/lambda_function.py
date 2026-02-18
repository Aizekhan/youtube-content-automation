import json
import boto3
import hashlib
import urllib.request
import urllib.parse
from datetime import datetime
from decimal import Decimal
from boto3.dynamodb.conditions import Key
from concurrent.futures import ThreadPoolExecutor, as_completed

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
            print("WARNING: Cost logged without user_id")

        cost_table.put_item(Item=item)

        print(f"Logged Qwen3-TTS cost: ${float(total_cost):.6f} ({generation_time_sec}s, {scene_count} scenes)")
        return float(total_cost)

    except Exception as e:
        print(f"Failed to log cost: {str(e)}")
        return 0.0




def process_single_scene(scene, ec2_endpoint):
    """
    Worker function for BATCHED processing
    All params extracted from scene object
    Handles both scene narration and CTA audio

    Returns: audio_file_dict or None
    """
    # Extract from scene object
    channel_id = scene.get('channel_id')
    narrative_id = scene.get('narrative_id')
    scene_id = scene.get('scene_id') or scene.get('id') or scene.get('scene_number', 0)
    language = scene.get('language', 'en')
    speaker = scene.get('speaker', 'default')
    voice_description = scene.get('voice_description')
    text = scene.get('text') or scene.get('scene_narration') or scene.get('narration', '')
    audio_type = scene.get('audio_type', 'scene')  # NEW: 'scene' or 'cta'
    cta_type = scene.get('cta_type', '')  # NEW: for CTA segments

    if not text:
        print(f"{audio_type.upper()} {scene_id}: no text")
        return None

    if not channel_id or not narrative_id:
        print(f"{audio_type.upper()} {scene_id}: missing channel_id or narrative_id")
        return None

    print(f"{audio_type.upper()} {scene_id}...")

    try:
        # Call Qwen3-TTS API on EC2
        audio_data, duration_ms = generate_with_qwen3(
            ec2_endpoint=ec2_endpoint,
            text=text,
            language=language,
            speaker=speaker,
            voice_description=voice_description
        )

        # Upload to S3 with different paths for scene vs CTA
        if audio_type == 'cta':
            s3_key = f"narratives/{channel_id}/{narrative_id}/cta_{scene_id}.wav"
        else:
            s3_key = f"narratives/{channel_id}/{narrative_id}/scene_{scene_id}.wav"

        s3_url = upload_to_s3(audio_data, s3_key, content_type='audio/wav')

        audio_file = {
            'channel_id': channel_id,
            'scene_id': scene_id,
            's3_url': s3_url,
            's3_key': s3_key,
            'duration_ms': duration_ms,
            'audio_type': audio_type  # NEW: Mark type in result
        }

        # Add CTA type if present
        if cta_type:
            audio_file['cta_type'] = cta_type

        print(f"{audio_type.upper()} {scene_id}: {duration_ms}ms")
        return audio_file

    except Exception as scene_error:
        print(f"{audio_type.upper()} {scene_id} error: {scene_error}")
        return None




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

    print(f"Qwen3-TTS Audio Generation")
    print(f"Event: {json.dumps(event, default=str)}")

    try:
        # Parse BATCHED input from collect-audio-scenes Lambda
        all_audio_scenes = event.get('all_audio_scenes', [])
        all_cta_segments = event.get('all_cta_segments', [])  # NEW: CTA segments
        ec2_endpoint = event.get('ec2_endpoint')

        print(f"Batch processing: {len(all_audio_scenes)} scenes + {len(all_cta_segments)} CTA segments")
        print(f"EC2 endpoint: {ec2_endpoint}")

        # NEW: Combine scenes and CTA for batch processing
        all_audio_tasks = all_audio_scenes + all_cta_segments

        if not all_audio_tasks:
            print("No audio to process")
            return {
                'audio_files': [],
                'cta_audio_files': [],  # NEW
                'total_files': 0,
                'total_duration_ms': 0,
                'scene_count': 0,
                'cta_count': 0  # NEW
            }

        if not ec2_endpoint:
            raise Exception("ec2_endpoint is required")

        # Generate audio for all tasks (scenes + CTA) in parallel
        all_results = []
        generation_start = datetime.utcnow()

        # Use ThreadPoolExecutor for parallel generation
        max_workers = min(8, len(all_audio_tasks))
        print(f"Generating {len(all_audio_tasks)} audio files with {max_workers} workers...")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks for processing
            futures = [
                executor.submit(process_single_scene, task, ec2_endpoint)
                for task in all_audio_tasks
            ]

            # Collect results as they complete
            for future in as_completed(futures):
                try:
                    audio_file = future.result()
                    if audio_file:
                        all_results.append(audio_file)
                except Exception as exc:
                    print(f"Audio task exception: {exc}")

        # NEW: Separate scene audio from CTA audio
        scene_audio_files = [f for f in all_results if f.get('audio_type') == 'scene']
        cta_audio_files = [f for f in all_results if f.get('audio_type') == 'cta']

        print(f"Complete: {len(scene_audio_files)} scenes + {len(cta_audio_files)} CTA / {len(all_audio_tasks)} total")

        # Calculate total generation time
        generation_end = datetime.utcnow()
        generation_time_sec = (generation_end - generation_start).total_seconds()

        # Calculate total duration (scenes + CTA)
        total_duration_ms = sum(af['duration_ms'] for af in all_results)
        total_duration_sec = total_duration_ms / 1000

        # Cost logging handled per-channel in distribute-audio
        cost_usd = 0.0

        print(f"Generated {len(all_results)} audio files ({len(scene_audio_files)} scenes + {len(cta_audio_files)} CTA) in {generation_time_sec:.2f}s")
        print(f"Total audio duration: {total_duration_sec:.2f}s, Cost: ${cost_usd:.6f}")

        return {
            'message': 'Audio generated successfully',
            'tts_service': 'qwen3_tts',
            'audio_files': scene_audio_files,  # NEW: Only scene audio
            'cta_audio_files': cta_audio_files,  # NEW: CTA audio separately
            'total_files': len(all_results),
            'total_duration_ms': total_duration_ms,
            'total_duration_sec': round(total_duration_sec, 2),
            'scene_count': len(scene_audio_files),  # NEW: Scene count
            'cta_count': len(cta_audio_files),  # NEW: CTA count
            'cost_usd': cost_usd,
            'generation_time_sec': round(generation_time_sec, 2),
            'provider': 'Qwen3-TTS-0.6B',
            'api_version': 'qwen3_v1'
        }

    except Exception as e:
        print(f"Error: {str(e)}")
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
        print("Invoking ec2-qwen3-control Lambda...")

        response = lambda_client.invoke(
            FunctionName='ec2-qwen3-control',
            InvocationType='RequestResponse',
            Payload=json.dumps({'action': 'start'})
        )

        result = json.loads(response['Payload'].read())

        print(f"EC2 control response: {json.dumps(result)}")

        if result.get('statusCode') == 200 and result.get('status') == 'running':
            endpoint = result.get('endpoint')
            print(f"EC2 running: {endpoint}")
            return endpoint

        elif result.get('statusCode') == 202:
            # Instance starting, wait and retry
            endpoint = result.get('endpoint')
            print(f"EC2 starting, waiting for service...")

            import time
            max_wait = 180  # 3 minutes max wait
            wait_interval = 10
            waited = 0

            while waited < max_wait:
                time.sleep(wait_interval)
                waited += wait_interval

                # Check if service is ready
                if check_service_health(endpoint):
                    print(f"Service ready after {waited}s")
                    return endpoint

                print(f"Still waiting... ({waited}s/{max_wait}s)")

            print(f"WARNING: Service not ready after {max_wait}s, proceeding anyway")
            return endpoint

        else:
            print(f"Unexpected EC2 control response: {result}")
            return None

    except Exception as e:
        print(f"Error starting EC2: {e}")
        import traceback
        traceback.print_exc()
        return None


def check_service_health(endpoint):
    """Check if Qwen3-TTS service is healthy"""
    try:
        health_url = f"{endpoint}/health"
        req = urllib.request.Request(health_url, method='GET')

        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
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

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')

        with urllib.request.urlopen(req, timeout=120) as response:
            if response.status != 200:
                error_text = response.read().decode('utf-8')
                raise Exception(f"Qwen3-TTS API error: {response.status} - {error_text}")

            result = json.loads(response.read().decode('utf-8'))

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
        print(f"Error calling Qwen3-TTS API: {e}")
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
        print(f"Error uploading to S3: {str(e)}")
        raise
