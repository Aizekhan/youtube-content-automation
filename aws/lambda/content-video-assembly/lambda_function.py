"""
AWS Lambda: Video Assembly - Short Videos (<15 min)
Uses FFmpeg to assemble final video from audio, images, and SFX
"""
import json
import os
import subprocess
import boto3
from decimal import Decimal
from datetime import datetime
import tempfile
import random
import re

s3 = boto3.client('s3', region_name='eu-central-1')
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')

# Tables
content_table = dynamodb.Table('GeneratedContent')
template_table = dynamodb.Table('VideoEditingTemplates')

# FFmpeg path (will be in Lambda Layer)
FFMPEG_PATH = '/opt/bin/ffmpeg'

# S3 URL Validation
ALLOWED_S3_BUCKETS = [
    'youtube-automation-audio-files',
    'youtube-automation-images',
    'youtube-automation-data-grucia',
    'youtube-automation-final-videos'
]

def validate_s3_url(s3_url, context='unknown'):
    """
    Validate S3 URL format and bucket to prevent injection attacks

    Args:
        s3_url: S3 URL to validate (format: s3://bucket/key)
        context: Description of where this URL is used (for error messages)

    Returns:
        tuple: (bucket, key) if valid

    Raises:
        ValueError: If URL is invalid or suspicious
    """
    if not s3_url or not isinstance(s3_url, str):
        raise ValueError(f"Invalid S3 URL in {context}: empty or not a string")

    # S3 URL format: s3://bucket-name/key/path
    s3_pattern = r'^s3://([a-z0-9][a-z0-9-]*[a-z0-9])/(.+)$'
    match = re.match(s3_pattern, s3_url)

    if not match:
        raise ValueError(f"Invalid S3 URL format in {context}: {s3_url}")

    bucket = match.group(1)
    key = match.group(2)

    # Validate bucket is in allowed list
    if bucket not in ALLOWED_S3_BUCKETS:
        raise ValueError(f"S3 bucket '{bucket}' not in allowed list for {context}")

    # Check for path traversal attempts
    if '..' in key or key.startswith('/'):
        raise ValueError(f"Suspicious S3 key (path traversal) in {context}: {key}")

    # Check for null bytes or other suspicious characters
    if '\x00' in key or '\0' in key:
        raise ValueError(f"Suspicious characters in S3 key for {context}: {key}")

    return bucket, key



def lambda_handler(event, context):
    """
    Main handler for video assembly
    Input:
        - content_id: ID of content in GeneratedContent table
        - template_id (optional): Video editing template ID
    """
    print(f"VIDEO ASSEMBLY Lambda - Short Videos (<15 min)")
    print(f"Event: {json.dumps(event)}")

    content_id = event.get('content_id')
    channel_id = event.get('channel_id')
    user_id = event.get('user_id')  # Multi-tenant support
    template_id = event.get('template_id', 'video_template_universal_v2')
    estimate_only = event.get('estimate_only', False)

    if not content_id or not channel_id:
        raise ValueError("Missing content_id or channel_id")

    print(f"Video Assembly - user_id: {user_id}, channel: {channel_id}, content: {content_id}")


    # Get content from DynamoDB
    content = get_content(channel_id, content_id, user_id)

    # Get video template
    template = get_template(template_id)

    # Estimate duration
    estimated_duration_min = estimate_duration(content)

    # Check if Lambda can handle this (max 15 min)
    if estimated_duration_min > 15:
        print(f"Video too long ({estimated_duration_min} min) for Lambda!")
        return {
            'status': 'redirect_to_ecs',
            'reason': f'Video duration {estimated_duration_min} min exceeds Lambda limit',
            'recommended_mode': 'ecs_fargate'
        }

    print(f"Estimated duration: {estimated_duration_min} min - OK for Lambda")

    # If only estimation is requested, return early
    if estimate_only:
        print('ESTIMATE ONLY mode - returning duration estimate')
        return {
            'status': 'ok_for_lambda',
            'duration_minutes': estimated_duration_min,
            'rendering_mode': 'lambda'
        }

    # Create working directory
    work_dir = tempfile.mkdtemp(dir='/tmp')
    print(f"Work dir: {work_dir}")

    try:
        # Step 1: Download all assets
        print("\n=== STEP 1: Downloading Assets ===")
        assets = download_assets(content, work_dir)

        # Step 2: Assemble video
        print("\n=== STEP 2: Assembling Video ===")
        final_video_path = assemble_video(content, assets, template, work_dir)

        # Step 3: Upload to S3
        print("\n=== STEP 3: Uploading to S3 ===")
        video_url = upload_video(final_video_path, channel_id, content_id)

        # Step 4: Update DynamoDB
        print("\n=== STEP 4: Updating DynamoDB ===")
        created_at = content.get('created_at')  # Get from already-fetched content
        update_content_with_video(channel_id, created_at, content_id, video_url, template)

        print(f"\nSUCCESS! Video URL: {video_url}")

        return {
            'status': 'success',
            'video_url': video_url,
            'content_id': content_id,
            'channel_id': channel_id,
            'rendering_mode': 'lambda',
            'duration_minutes': estimated_duration_min
        }

    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

        # Update DynamoDB with error
        update_video_status(channel_id, content_id, 'failed', str(e))

        raise

    finally:
        # Cleanup
        cleanup_directory(work_dir)


def get_content(channel_id, content_id, user_id=None):
    """Fetch content from DynamoDB with multi-tenant support

    Args:
        content_table: DynamoDB Table resource
        channel_id: Channel ID
        content_id: Content ID (may be compressed timestamp from narrative Lambda)
        user_id: User ID for multi-tenant filtering

    Returns:
        dict: Content item from DynamoDB
    """
    # First try: get_item with channel_id and created_at
    # Note: content_id might be a compressed timestamp, not the actual created_at
    response = content_table.get_item(
        Key={
            'channel_id': channel_id,
            'created_at': content_id  # Try as-is first
        }
    )

    if 'Item' in response:
        item = response['Item']
        # Verify user_id if provided (security check)
        if user_id and item.get('user_id') != user_id:
            raise ValueError(f"Access denied: Content belongs to different user")
        print(f"Found content via get_item")
        return item

    print(f"Content not found with created_at={content_id}")

    # WEEK 3.6: Use content_id GSI instead of table scan (10-100x faster!)
    print(f"Querying content_id-created_at-index for content_id={content_id}")
    response = content_table.query(
        IndexName='content_id-created_at-index',
        KeyConditionExpression='content_id = :cid',
        ExpressionAttributeValues={':cid': content_id},
        ScanIndexForward=False  # Most recent first
    )

    items = response.get('Items', [])
    print(f"Found {len(items)} items with content_id={content_id}")

    if not items:
        raise ValueError(f"Content not found: {content_id}")

    # Filter by channel_id and user_id (if provided)
    for item in items:
        item_channel_id = item.get('channel_id')
        item_user_id = item.get('user_id')

        # Check channel_id match
        if item_channel_id != channel_id:
            continue

        # Check user_id match (security check)
        if user_id and item_user_id != user_id:
            print(f" SECURITY: Content {content_id} belongs to user {item_user_id}, not {user_id}")
            continue

        print(f" Match found! created_at={item.get('created_at')}")
        return item

    # No matching item found after filtering
    if user_id:
        raise ValueError(f"Content not found or access denied: {content_id} (user_id: {user_id}, channel: {channel_id})")
    else:
        raise ValueError(f"Content not found: {content_id} (channel: {channel_id})")

    print(f"Found content via scan")
    return items[0]
def get_template(template_id):
    """Fetch video editing template"""
    response = template_table.get_item(Key={'template_id': template_id})

    if 'Item' not in response:
        print(f"Template {template_id} not found, using defaults")
        return get_default_template()

    return response['Item']


def get_default_template():
    """Default template if none found"""
    return {
        'editing_params': {
            'transitions': [{'type': 'fade', 'duration': 0.5}],
            'audio_params': {
                'voice_volume': 1.0,
                'music_volume': 0.3,
                'sfx_volume': 0.5,
                'normalize': True
            },
            'export_settings': {
                'resolution': '1920x1080',
                'fps': 30,
                'codec': 'h264',
                'bitrate': '8M'
            },
            'visual_effects': {
                'enabled': True,
                'effects': {
                    'ken_burns': {'enabled': True, 'intensity': 'medium'}
                }
            }
        }
    }


def estimate_duration(content):
    """Estimate video duration in minutes"""
    # Get audio duration
    audio_files = content.get('audio_files', [])
    total_duration_ms = 0.0  # Initialize as float

    for a in audio_files:
        duration = a.get('duration_ms', 0)
        # Convert Decimal to float (DynamoDB returns Decimal)
        total_duration_ms += float(duration) if duration else 0.0

    # Add CTA segments
    cta_data = content.get('cta_data', {})
    cta_segments = cta_data.get('cta_segments', [])
    for cta in cta_segments:
        cta_audio = cta.get('cta_audio_segment', {})
        target_duration = cta_audio.get('target_duration_seconds', 10)
        # Convert Decimal to float
        total_duration_ms += float(target_duration) * 1000 if target_duration else 0.0

    # Convert to minutes
    duration_min = total_duration_ms / 1000 / 60

    return round(duration_min, 2)


def download_assets(content, work_dir):
    """Download all assets from S3"""
    assets = {
        'audio': [],
        'images': [],
        'music': [],
        'sfx': []
    }

    # Download audio files
    audio_files = content.get('audio_files', [])
    print(f"Downloading {len(audio_files)} audio files...")
    for i, audio in enumerate(audio_files):
        s3_url = audio.get('s3_url', '')
        if not s3_url:
            continue

        # Parse S3 URL
        parts = s3_url.replace('s3://', '').split('/', 1)
        bucket = parts[0]
        key = parts[1]

        # Download
        local_path = os.path.join(work_dir, f'audio_scene_{i+1}.mp3')
        s3.download_file(bucket, key, local_path)

        assets['audio'].append({
            'path': local_path,
            'scene_id': audio.get('scene_id'),
            'duration_ms': audio.get('duration_ms')
        })

    # Download images
    scene_images = content.get('scene_images', [])
    print(f"Downloading {len(scene_images)} images...")
    for i, img in enumerate(scene_images):
        # Accept both 'success' and 'completed' status
        if img.get('status') not in ['success', 'completed']:
            continue

        # Support both 's3_url' and 'image_url' field names
        s3_url = img.get('s3_url', img.get('image_url', ''))
        if not s3_url:
            continue

        # Validate S3 URL for security
        try:
            bucket, key = validate_s3_url(s3_url, context=f'scene image {i}')
        except ValueError as e:
            print(f"SECURITY ERROR: {e}")
            raise

        local_path = os.path.join(work_dir, f'image_scene_{i+1}.png')
        s3.download_file(bucket, key, local_path)

        assets['images'].append({
            'path': local_path,
            'scene_number': img.get('scene_number')
        })

    print(f"Downloaded: {len(assets['audio'])} audio, {len(assets['images'])} images")

    return assets


def create_thumbnail_intro(content, work_dir, duration_seconds):
    """
    Create thumbnail intro clip
    Returns path to intro video or None if thumbnail not found
    """
    try:
        # Get thumbnail image from content
        scene_images = content.get('scene_images', [])

        # Find thumbnail image (scene_number=0 or image_type='thumbnail')
        thumbnail_image = None
        for img in scene_images:
            if img.get('scene_number') == 0 or img.get('image_type') == 'thumbnail':
                thumbnail_image = img
                break

        if not thumbnail_image:
            print("  No thumbnail image found, skipping intro")
            return None

        # Download thumbnail
        s3_url = thumbnail_image.get('s3_url', thumbnail_image.get('image_url', ''))
        if not s3_url:
            print("WARNING: Thumbnail has no S3 URL")
            return None

        # Validate S3 URL for security
        try:
            bucket, key = validate_s3_url(s3_url, context='thumbnail image')
        except ValueError as e:
            print(f"SECURITY ERROR: {e}")
            return None

        thumbnail_path = os.path.join(work_dir, 'thumbnail_intro.png')
        s3.download_file(bucket, key, thumbnail_path)

        print(f" Downloaded thumbnail: {s3_url}")

        # Create intro video with fade-in effect
        intro_video_path = os.path.join(work_dir, 'thumbnail_intro.mp4')

        cmd = [
            FFMPEG_PATH,
            '-loop', '1',
            '-t', str(duration_seconds),
            '-i', thumbnail_path,
            '-vf', f'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fade=in:0:30',
            '-c:v', 'libx264',
            '-preset', 'fast',
            '-pix_fmt', 'yuv420p',
            '-r', '30',
            '-y',
            intro_video_path
        ]

        print(f"Creating {duration_seconds}s intro: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"FFmpeg intro error: {result.stderr}")
            return None

        print(f" Thumbnail intro created: {intro_video_path}")
        return intro_video_path

    except Exception as e:
        print(f"  Failed to create thumbnail intro: {e}")
        import traceback
        traceback.print_exc()
        return None


def assemble_video(content, assets, template, work_dir):
    """
    Assemble final video using FFmpeg
    """
    editing_params = template.get('editing_params', {})
    export_settings = editing_params.get('export_settings', {})
    audio_params = editing_params.get('audio_params', {})
    visual_effects = editing_params.get('visual_effects', {})

    # Check if thumbnail intro is enabled
    thumbnail_intro_enabled = editing_params.get('enable_thumbnail_intro', False)
    thumbnail_intro_duration = editing_params.get('thumbnail_intro_duration_seconds', 3)

    # Build scene videos
    scene_videos = []

    # Add thumbnail intro if enabled
    if thumbnail_intro_enabled:
        print(f"\n=== Creating thumbnail intro ({thumbnail_intro_duration}s) ===")
        thumbnail_video = create_thumbnail_intro(content, work_dir, thumbnail_intro_duration)
        if thumbnail_video:
            scene_videos.append(thumbnail_video)
            print(f" Thumbnail intro created: {thumbnail_video}")

    for i, (audio, image) in enumerate(zip(assets['audio'], assets['images'])):
        print(f"\nProcessing scene {i+1}...")

        scene_video = os.path.join(work_dir, f'scene_{i+1}.mp4')

        # Get duration from audio
        duration_sec = float(audio['duration_ms']) / 1000

        # Apply Ken Burns effect if enabled
        ken_burns = visual_effects.get('effects', {}).get('ken_burns', {})

        if ken_burns.get('enabled'):
            # Ken Burns: slow zoom and pan
            zoom_max = ken_burns.get('zoom_range', {}).get('max', 1.2)
            zoom_min = ken_burns.get('zoom_range', {}).get('min', 1.0)

            # Calculate zoom rate to complete over the ENTIRE duration
            total_frames = int(duration_sec * 30)
            zoom_range = zoom_max - zoom_min
            zoom_rate = zoom_range / total_frames if total_frames > 0 else 0.0015

            print(f"Ken Burns: {duration_sec}s, zoom {zoom_min}→{zoom_max}, rate={zoom_rate:.6f}")

            # FFmpeg zoompan filter with proper duration
            cmd = [
                FFMPEG_PATH,
                '-loop', '1',
                '-i', image['path'],
                '-i', audio['path'],
                '-vf', f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,zoompan=z='min(zoom+{zoom_rate},{zoom_max})':d={total_frames}:s=1920x1080:fps=30",
                '-c:v', 'libx264',
                '-preset', 'veryfast',  # Changed from 'fast' to 'veryfast' for 2x speed
                '-crf', '23',  # Quality setting (lower = better quality, 23 is good default)
                '-c:a', 'aac',
                '-shortest',
                '-y',
                scene_video
            ]
        else:
            # Simple static image + audio
            cmd = [
                FFMPEG_PATH,
                '-loop', '1',
                '-i', image['path'],
                '-i', audio['path'],
                '-vf', 'scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080',
                '-c:v', 'libx264',
                '-preset', 'veryfast',  # Changed from 'fast' to 'veryfast' for 2x speed
                '-crf', '23',  # Quality setting
                '-c:a', 'aac',
                '-shortest',
                '-y',
                scene_video
            ]

        print(f"Running FFmpeg: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f" FFmpeg FAILED for scene {i+1}")
            print(f"Return code: {result.returncode}")
            print(f"STDERR:\n{result.stderr}")
            print(f"STDOUT:\n{result.stdout}")
            print(f"Image path: {image['path']}, exists: {os.path.exists(image['path'])}")
            print(f"Audio path: {audio['path']}, exists: {os.path.exists(audio['path'])}")
            raise Exception(f"FFmpeg failed for scene {i+1}: {result.stderr[:500]}")

        scene_videos.append(scene_video)

    # Concatenate all scene videos
    print(f"\nConcatenating {len(scene_videos)} scenes...")

    concat_list = os.path.join(work_dir, 'concat_list.txt')
    with open(concat_list, 'w') as f:
        for video in scene_videos:
            f.write(f"file '{video}'\n")

    final_video = os.path.join(work_dir, 'final_video.mp4')

    cmd = [
        FFMPEG_PATH,
        '-f', 'concat',
        '-safe', '0',
        '-i', concat_list,
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '23',
        '-c:a', 'aac',
        '-b:a', '192k',
        '-y',
        final_video
    ]

    print(f"Running FFmpeg concat: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f" FFmpeg concat FAILED!")
        print(f"Return code: {result.returncode}")
        print(f"STDERR:\n{result.stderr}")
        print(f"STDOUT:\n{result.stdout}")
        # Also print concat list contents for debugging
        with open(concat_list, 'r') as f:
            concat_contents = f.read()
        print(f"Concat list contents:\n{concat_contents}")
        raise Exception(f"FFmpeg concatenation failed: {result.stderr[:500]}")

    print(f"Final video created: {final_video}")

    return final_video


def upload_video(video_path, channel_id, content_id):
    """Upload final video to S3"""
    bucket = 'youtube-automation-final-videos'
    key = f'videos/{channel_id}/{content_id}/final_video.mp4'

    print(f"Uploading to s3://{bucket}/{key}")

    s3.upload_file(
        video_path,
        bucket,
        key,
        ExtraArgs={
            'ContentType': 'video/mp4',
            'Metadata': {
                'content_id': content_id,
                'channel_id': channel_id,
                'created_at': datetime.utcnow().isoformat()
            }
        }
    )

    video_url = f's3://{bucket}/{key}'

    return video_url


def update_content_with_video(channel_id, created_at, content_id, video_url, template):
    """Update GeneratedContent with video URL"""

    # Use created_at directly (passed from already-fetched content)
    print(f"Updating content: channel={channel_id}, created_at={created_at}, content_id={content_id}")

    # Build final_video object for frontend compatibility
    final_video = {
        'video_url': video_url,
        'status': 'completed',
        'rendered_at': datetime.utcnow().isoformat() + 'Z',
        'rendering_mode': 'lambda',
        'template_id': template.get('template_id', 'unknown')
    }

    # Update with video info (nested in final_video for frontend)
    content_table.update_item(
        Key={
            'channel_id': channel_id,
            'created_at': created_at
        },
        UpdateExpression='''
            SET final_video = :final_video,
                video_url = :url,
                video_status = :status,
                video_rendered_at = :timestamp,
                rendering_mode = :mode,
                video_template_id = :template_id
        ''',
        ExpressionAttributeValues={
            ':final_video': final_video,
            ':url': video_url,
            ':status': 'completed',
            ':timestamp': datetime.utcnow().isoformat() + 'Z',
            ':mode': 'lambda',
            ':template_id': template.get('template_id', 'unknown')
        }
    )

    print(f"Updated content with video URL: {video_url}")


def update_video_status(channel_id, content_id, status, error=None):
    """
    Update video rendering status

    WEEK 3.6: Now uses content_id GSI instead of table scan
    """
    try:
        # Use content_id GSI query instead of scan (10-100x faster!)
        response = content_table.query(
            IndexName='content_id-created_at-index',
            KeyConditionExpression='content_id = :cid',
            ExpressionAttributeValues={':cid': content_id},
            Limit=1,
            ScanIndexForward=False  # Most recent first
        )

        if response.get('Items'):
            item = response['Items'][0]
            created_at = item['created_at']

            update_expr = 'SET video_status = :status'
            expr_values = {':status': status}

            if error:
                update_expr += ', video_error = :error'
                expr_values[':error'] = error

            content_table.update_item(
                Key={
                    'channel_id': channel_id,
                    'created_at': created_at
                },
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values
            )
    except Exception as e:
        print(f"Failed to update status: {e}")


def cleanup_directory(directory):
    """Clean up temporary files"""
    try:
        import shutil
        shutil.rmtree(directory)
        print(f"Cleaned up: {directory}")
    except Exception as e:
        print(f"Cleanup error: {e}")
