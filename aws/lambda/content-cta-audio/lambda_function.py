"""
AWS Lambda: CTA Audio Generation
Generates audio for Call-to-Action segments using AWS Polly
"""
import json
import boto3
from datetime import datetime
from decimal import Decimal

# AWS clients
polly = boto3.client('polly', region_name='eu-central-1')
s3 = boto3.client('s3', region_name='eu-central-1')
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
cost_table = dynamodb.Table('CostTracking')

# S3 bucket for audio files
AUDIO_BUCKET = 'youtube-automation-audio-files'

# AWS Polly pricing (per 1M characters)
POLLY_PRICING = {
    'neural': 16.00 / 1_000_000,
    'standard': 4.00 / 1_000_000
}

# Voice profile mapping
VOICE_PROFILES = {
    'deep_male': {'voice_id': 'Matthew', 'engine': 'neural'},
    'calm_male': {'voice_id': 'Joey', 'engine': 'neural'},
    'professional_male': {'voice_id': 'Stephen', 'engine': 'neural'},
    'warm_female': {'voice_id': 'Joanna', 'engine': 'neural'},
    'soothing_female': {'voice_id': 'Salli', 'engine': 'neural'},
    'british_male': {'voice_id': 'Brian', 'engine': 'neural'},
    'british_female': {'voice_id': 'Amy', 'engine': 'neural'},
}


def log_polly_cost(channel_id, content_id, operation, character_count, engine):
    """Log AWS Polly cost to CostTracking table"""
    try:
        pricing_key = 'neural' if engine == 'neural' else 'standard'
        cost_per_char = POLLY_PRICING[pricing_key]
        total_cost = Decimal(str(character_count * cost_per_char))

        now = datetime.utcnow()
        cost_table.put_item(
            Item={
                'date': now.strftime('%Y-%m-%d'),
                'timestamp': now.isoformat() + 'Z',
                'service': 'AWS Polly',
                'operation': operation,
                'channel_id': channel_id,
                'content_id': content_id,
                'cost_usd': total_cost,
                'units': character_count,
                'details': {
                    'engine': engine,
                    'character_count': character_count,
                    'cost_per_char': float(cost_per_char)
                }
            }
        )

        print(f"[OK] Logged Polly cost: ${float(total_cost):.6f} ({character_count} chars, {engine})")
        return float(total_cost)
    except Exception as e:
        print(f"[ERROR] Failed to log cost: {e}")
        return 0.0


def get_audio_duration_ms(audio_stream):
    """
    Estimate audio duration from audio stream
    Uses average speaking rate: ~150 words/min = 2.5 words/sec
    """
    # For now, use a simple estimation based on audio size
    # TODO: Use mutagen or similar library for exact duration
    audio_bytes = len(audio_stream.read())
    audio_stream.seek(0)  # Reset stream position

    # Rough estimation: MP3 at 24kbps = ~3KB/sec
    estimated_duration_ms = (audio_bytes / 3000) * 1000
    return int(estimated_duration_ms)


def lambda_handler(event, context):
    """
    Generate audio for CTA segments

    Input:
        - channel_id: Channel ID
        - content_id: Content ID for tracking
        - cta_segments: Array of CTA segments with text
        - voice_config: Voice configuration (voice_id, voice_profile, tts_service)

    Output:
        - cta_segments with added audio data (s3_url, duration_ms)
    """
    print("=" * 80)
    print("CTA AUDIO GENERATION Lambda")
    print("=" * 80)
    print(f"Event: {json.dumps(event, default=str)}")

    channel_id = event.get('channel_id', 'Unknown')
    content_id = event.get('content_id', f"cta_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")
    cta_segments = event.get('cta_segments', [])
    voice_config = event.get('voice_config', {})

    if not cta_segments:
        print("[WARNING]  No CTA segments provided, returning empty result")
        return {
            'cta_segments': [],
            'total_segments': 0,
            'total_cost': 0
        }

    # Get voice settings
    tts_service = voice_config.get('tts_service', 'aws_polly_neural')
    voice_profile = voice_config.get('tts_voice_profile', 'deep_male')
    voice_id = voice_config.get('voice_id')

    # Map voice profile to actual voice
    if not voice_id and voice_profile in VOICE_PROFILES:
        voice_mapping = VOICE_PROFILES[voice_profile]
        voice_id = voice_mapping['voice_id']
        engine = voice_mapping['engine']
    else:
        voice_id = voice_id or 'Matthew'
        engine = 'neural' if 'neural' in tts_service else 'standard'

    print(f"\n[VOICE] Voice Settings:")
    print(f"   Service: {tts_service}")
    print(f"   Voice Profile: {voice_profile}")
    print(f"   Voice ID: {voice_id}")
    print(f"   Engine: {engine}")

    # Generate audio for each CTA segment
    total_cost = 0.0
    processed_segments = []

    for i, cta in enumerate(cta_segments, 1):
        print(f"\n{'='*60}")
        print(f"Processing CTA Segment {i}/{len(cta_segments)}")
        print(f"{'='*60}")

        cta_type = cta.get('type', 'generic')
        cta_text = cta.get('cta_text', '')

        if not cta_text:
            print(f"[WARNING]  Skipping CTA {i}: No text provided")
            continue

        # Clean SSML text for Polly
        ssml_text = cta_text.strip()

        # Ensure SSML is wrapped in <speak> tags
        if not ssml_text.startswith('<speak>'):
            ssml_text = f'<speak>{ssml_text}</speak>'

        print(f"Type: {cta_type}")
        print(f"Text length: {len(cta_text)} chars")
        print(f"SSML preview: {ssml_text[:100]}...")

        try:
            # Generate audio with Polly
            print(f"\n[POLLY]  Calling AWS Polly...")
            response = polly.synthesize_speech(
                Text=ssml_text,
                OutputFormat='mp3',
                VoiceId=voice_id,
                Engine=engine,
                TextType='ssml'
            )

            # Get audio stream
            audio_stream = response['AudioStream']

            # Estimate duration
            duration_ms = get_audio_duration_ms(audio_stream)

            # Upload to S3
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            s3_key = f"cta/{channel_id}/{content_id}/cta_{cta_type}_{timestamp}.mp3"

            print(f"\n[S3]  Uploading to S3...")
            print(f"   Bucket: {AUDIO_BUCKET}")
            print(f"   Key: {s3_key}")

            s3.put_object(
                Bucket=AUDIO_BUCKET,
                Key=s3_key,
                Body=audio_stream.read(),
                ContentType='audio/mpeg'
            )

            s3_url = f"s3://{AUDIO_BUCKET}/{s3_key}"

            print(f"[OK] Audio generated successfully!")
            print(f"   S3 URL: {s3_url}")
            print(f"   Duration: {duration_ms}ms ({duration_ms/1000:.1f}s)")

            # Log cost
            char_count = len(cta_text)
            cost = log_polly_cost(
                channel_id=channel_id,
                content_id=content_id,
                operation=f'cta_audio_{cta_type}',
                character_count=char_count,
                engine=engine
            )
            total_cost += cost

            # Add audio data to CTA segment
            cta['cta_audio_segment'] = {
                's3_url': s3_url,
                'duration_ms': duration_ms,
                'target_duration_seconds': int(duration_ms / 1000),
                'voice_id': voice_id,
                'voice_profile': voice_profile,
                'engine': engine,
                'character_count': char_count,
                'generation_cost_usd': cost
            }

            processed_segments.append(cta)

        except Exception as e:
            print(f"\n[ERROR] Error generating audio for CTA {i}: {str(e)}")
            import traceback
            traceback.print_exc()

            # Add error info to segment
            cta['audio_error'] = str(e)
            processed_segments.append(cta)

    # Summary
    print(f"\n" + "=" * 80)
    print(f"CTA AUDIO GENERATION COMPLETE")
    print(f"=" * 80)
    print(f"Total CTA segments: {len(cta_segments)}")
    print(f"Successfully processed: {len([c for c in processed_segments if 'cta_audio_segment' in c])}")
    print(f"Failed: {len([c for c in processed_segments if 'audio_error' in c])}")
    print(f"Total cost: ${total_cost:.6f}")
    print("=" * 80)

    return {
        'cta_segments': processed_segments,
        'total_segments': len(processed_segments),
        'successful_segments': len([c for c in processed_segments if 'cta_audio_segment' in c]),
        'failed_segments': len([c for c in processed_segments if 'audio_error' in c]),
        'total_cost': total_cost,
        'voice_id': voice_id,
        'voice_profile': voice_profile,
        'engine': engine
    }
