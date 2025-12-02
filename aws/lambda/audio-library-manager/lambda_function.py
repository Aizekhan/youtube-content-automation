"""
Audio Library Manager Lambda
Handles audio file uploads to S3 and updates SFX template library catalogs
"""

import json
import boto3
import os
from datetime import datetime
from decimal import Decimal

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

BUCKET = 'youtube-automation-audio-files'
TABLE_NAME = 'SFXTemplates'

# Response headers (CORS is handled by Function URL config)
RESPONSE_HEADERS = {
    'Content-Type': 'application/json'
}

def lambda_handler(event, context):
    """
    Main handler for audio library management

    Supports:
    1. Upload audio file to S3
    2. Scan S3 and update template library
    3. Get presigned upload URL
    """

    try:
        # Parse request
        if 'body' in event:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event

        action = body.get('action')

        if action == 'get_upload_url':
            return get_upload_url(body)
        elif action == 'scan_and_update':
            return scan_and_update_libraries(body)
        elif action == 'list_files':
            return list_library_files(body)
        elif action == 'get_playback_url':
            return get_playback_url(body)
        else:
            return {
                'statusCode': 400,
                'headers': RESPONSE_HEADERS,
                'body': json.dumps({'error': 'Invalid action'})
            }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': RESPONSE_HEADERS,
            'body': json.dumps({'error': str(e)})
        }

def get_upload_url(body):
    """Generate presigned URL for direct S3 upload"""

    file_type = body.get('file_type', 'sfx')  # sfx or music
    category = body.get('category', 'ambient')
    filename = body.get('filename')

    if not filename:
        return {
            'statusCode': 400,
            'headers': RESPONSE_HEADERS,
            'body': json.dumps({'error': 'Filename required'})
        }

    # Construct S3 key
    key = f"{file_type}/{category}/{filename}"

    # Generate presigned URL (valid for 10 minutes)
    presigned_url = s3.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': BUCKET,
            'Key': key,
            'ContentType': 'audio/mpeg'
        },
        ExpiresIn=600
    )

    return {
        'statusCode': 200,
        'headers': RESPONSE_HEADERS,
        'body': json.dumps({
            'success': True,
            'upload_url': presigned_url,
            'file_key': key
        })
    }

def get_playback_url(body):
    """Generate presigned URL for audio playback"""

    file_type = body.get('file_type', 'sfx')  # sfx or music
    category = body.get('category')
    filename = body.get('filename')

    if not category or not filename:
        return {
            'statusCode': 400,
            'headers': RESPONSE_HEADERS,
            'body': json.dumps({'error': 'Category and filename required'})
        }

    # Construct S3 key
    key = f"{file_type}/{category}/{filename}"

    # Generate presigned URL for playback (valid for 1 hour)
    presigned_url = s3.generate_presigned_url(
        'get_object',
        Params={
            'Bucket': BUCKET,
            'Key': key
        },
        ExpiresIn=3600
    )

    return {
        'statusCode': 200,
        'headers': RESPONSE_HEADERS,
        'body': json.dumps({
            'success': True,
            'playback_url': presigned_url,
            'file_key': key
        })
    }

def list_library_files(body):
    """List all audio files in S3 library with pagination support"""

    file_type = body.get('file_type')  # sfx, music, or None (all)

    prefix = f"{file_type}/" if file_type else ""

    files = {}
    continuation_token = None

    # Paginate through all S3 objects
    while True:
        params = {
            'Bucket': BUCKET,
            'Prefix': prefix
        }
        if continuation_token:
            params['ContinuationToken'] = continuation_token

        response = s3.list_objects_v2(**params)

        for obj in response.get('Contents', []):
            key = obj['Key']
            if key.endswith('/'):
                continue  # Skip folder markers

            # Parse key: sfx/ambient/rain.mp3 -> type=sfx, category=ambient, file=rain.mp3
            parts = key.split('/')
            if len(parts) >= 3:
                ftype = parts[0]
                category = parts[1]
                filename = parts[2]

                if ftype not in files:
                    files[ftype] = {}
                if category not in files[ftype]:
                    files[ftype][category] = []

                files[ftype][category].append({
                    'filename': filename,
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat()
                })

        # Check if there are more results
        if response.get('IsTruncated'):
            continuation_token = response.get('NextContinuationToken')
        else:
            break

    return {
        'statusCode': 200,
        'headers': RESPONSE_HEADERS,
        'body': json.dumps({
            'success': True,
            'files': files
        })
    }

def scan_and_update_libraries(body):
    """Scan S3 and update all SFX template libraries"""

    template_id = body.get('template_id', 'sfx_universal_v1')

    # Scan S3 for SFX files
    sfx_library = {}
    sfx_response = s3.list_objects_v2(Bucket=BUCKET, Prefix='sfx/')
    for obj in sfx_response.get('Contents', []):
        key = obj['Key']
        if key.endswith('/'):
            continue

        parts = key.split('/')
        if len(parts) >= 3:
            category = parts[1]
            filename = parts[2]

            if category not in sfx_library:
                sfx_library[category] = []
            sfx_library[category].append(filename)

    # Scan S3 for Music files
    music_library = {}
    music_response = s3.list_objects_v2(Bucket=BUCKET, Prefix='music/')
    for obj in music_response.get('Contents', []):
        key = obj['Key']
        if key.endswith('/'):
            continue

        parts = key.split('/')
        if len(parts) >= 3:
            category = parts[1]
            filename = parts[2]

            if category not in music_library:
                music_library[category] = []
            music_library[category].append(filename)

    # Calculate stats
    sfx_files = sum(len(files) for files in sfx_library.values())
    music_files = sum(len(files) for files in music_library.values())

    # Update DynamoDB template
    table = dynamodb.Table(TABLE_NAME)

    update_data = {
        'sfx_library': sfx_library,
        'music_library': music_library,
        'library_stats': {
            'sfx_files': sfx_files,
            'music_files': music_files,
            'total_files': sfx_files + music_files,
            'sfx_categories': len(sfx_library),
            'music_categories': len(music_library)
        },
        'last_library_scan': datetime.utcnow().isoformat() + 'Z',
        'updated_at': int(datetime.utcnow().timestamp() * 1000)
    }

    table.update_item(
        Key={'template_id': template_id},
        UpdateExpression='SET sfx_library = :sfx, music_library = :music, library_stats = :stats, last_library_scan = :scan, updated_at = :updated',
        ExpressionAttributeValues={
            ':sfx': sfx_library,
            ':music': music_library,
            ':stats': update_data['library_stats'],
            ':scan': update_data['last_library_scan'],
            ':updated': update_data['updated_at']
        }
    )

    return {
        'statusCode': 200,
        'headers': RESPONSE_HEADERS,
        'body': json.dumps({
            'success': True,
            'message': 'Libraries updated successfully',
            'stats': {
                'sfx_files': sfx_files,
                'sfx_categories': len(sfx_library),
                'music_files': music_files,
                'music_categories': len(music_library),
                'total_files': sfx_files + music_files
            },
            'sfx_library': sfx_library,
            'music_library': music_library
        })
    }
