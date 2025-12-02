"""
Update SFX Library Lambda

Scans S3 bucket (autoyou-media) for SFX and music files,
builds library structure, and updates SFXTemplate in DynamoDB.

Triggered by:
- EventBridge daily schedule
- Manual trigger

Structure:
s3://youtube-automation-audio-files/sfx/
    ambient/
        rain.mp3
        forest.mp3
    action/
        explosion.mp3
    horror/
        creaking_door.mp3

s3://youtube-automation-audio-files/music/
    epic/
        dramatic/
            battle_theme.mp3
    calm/
        meditation.mp3
"""

import json
import boto3
from datetime import datetime
from decimal import Decimal

s3 = boto3.client('s3', region_name='eu-central-1')
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')

BUCKET_NAME = 'youtube-automation-audio-files'
SFX_PREFIX = 'sfx/'
MUSIC_PREFIX = 'music/'


def scan_s3_directory(prefix):
    """
    Scan S3 directory and build nested structure

    Args:
        prefix (str): S3 prefix (e.g., 'sfx/' or 'music/')

    Returns:
        dict: Nested structure of files by category
    """

    print(f"[INFO] Scanning s3://{BUCKET_NAME}/{prefix}")

    try:
        paginator = s3.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix)

        structure = {}

        for page in pages:
            if 'Contents' not in page:
                continue

            for obj in page['Contents']:
                key = obj['Key']

                # Skip the prefix itself
                if key == prefix:
                    continue

                # Skip non-audio files
                if not key.endswith(('.mp3', '.wav', '.ogg', '.m4a')):
                    continue

                # Parse path: sfx/category/subcategory/file.mp3
                # or: music/genre/mood/file.mp3
                parts = key[len(prefix):].split('/')

                if len(parts) == 1:
                    # File directly in root (sfx/file.mp3)
                    category = '_root'
                    filename = parts[0]
                    structure.setdefault(category, []).append(filename)

                elif len(parts) == 2:
                    # File in category (sfx/ambient/rain.mp3)
                    category = parts[0]
                    filename = parts[1]
                    structure.setdefault(category, []).append(filename)

                elif len(parts) >= 3:
                    # File in subcategory (music/epic/dramatic/battle.mp3)
                    category = parts[0]
                    subcategory = parts[1]
                    filename = parts[-1]  # Last part is always filename

                    if category not in structure:
                        structure[category] = {}

                    if isinstance(structure[category], dict):
                        structure[category].setdefault(subcategory, []).append(filename)
                    else:
                        # Convert list to dict if needed
                        old_list = structure[category]
                        structure[category] = {'_default': old_list}
                        structure[category].setdefault(subcategory, []).append(filename)

        print(f"[OK] Found {sum_files(structure)} files in {len(structure)} categories")
        return structure

    except Exception as e:
        print(f"[ERROR] Failed to scan {prefix}: {str(e)}")
        return {}


def sum_files(structure):
    """Count total files in nested structure"""
    total = 0
    for value in structure.values():
        if isinstance(value, list):
            total += len(value)
        elif isinstance(value, dict):
            total += sum_files(value)
    return total


def update_sfx_template(template_id, sfx_library, music_library):
    """
    Update SFXTemplate with new library structure

    Args:
        template_id (str): Template ID to update
        sfx_library (dict): SFX library structure
        music_library (dict): Music library structure
    """

    table = dynamodb.Table('SFXTemplates')

    try:
        # Get current template
        response = table.get_item(Key={'template_id': template_id})

        if 'Item' not in response:
            print(f"[ERROR] Template {template_id} not found")
            return False

        template = response['Item']

        # Update libraries
        template['sfx_library'] = sfx_library
        template['music_library'] = music_library
        template['updated_at'] = Decimal(str(int(datetime.utcnow().timestamp() * 1000)))
        template['last_library_scan'] = datetime.utcnow().isoformat() + 'Z'

        # Calculate stats
        sfx_count = sum_files(sfx_library)
        music_count = sum_files(music_library)

        template['library_stats'] = {
            'sfx_files': sfx_count,
            'music_files': music_count,
            'sfx_categories': len(sfx_library),
            'music_categories': len(music_library),
            'total_files': sfx_count + music_count
        }

        # Save template
        table.put_item(Item=template)

        print(f"[OK] Updated template {template_id}")
        print(f"   SFX: {sfx_count} files in {len(sfx_library)} categories")
        print(f"   Music: {music_count} files in {len(music_library)} categories")

        return True

    except Exception as e:
        print(f"[ERROR] Failed to update template: {str(e)}")
        return False


def scan_and_update_all_templates():
    """
    Scan S3 and update ALL SFXTemplates with new library data
    """

    print(f"[INFO] Starting SFX library update")
    print(f"[INFO] Scanning S3 bucket: {BUCKET_NAME}")

    # Scan S3
    sfx_library = scan_s3_directory(SFX_PREFIX)
    music_library = scan_s3_directory(MUSIC_PREFIX)

    if not sfx_library and not music_library:
        print(f"[WARN] No files found in S3")
        return {
            'status': 'no_files',
            'sfx_count': 0,
            'music_count': 0
        }

    # Get all SFXTemplates
    table = dynamodb.Table('SFXTemplates')

    try:
        response = table.scan()
        templates = response.get('Items', [])

        print(f"[INFO] Found {len(templates)} SFXTemplates to update")

        updated_count = 0

        for template in templates:
            template_id = template['template_id']
            template_name = template.get('template_name', 'Unknown')

            print(f"\n[TEMPLATE] {template_name} ({template_id})")

            if update_sfx_template(template_id, sfx_library, music_library):
                updated_count += 1

        print(f"\n[OK] Updated {updated_count}/{len(templates)} templates")

        return {
            'status': 'success',
            'templates_updated': updated_count,
            'sfx_count': sum_files(sfx_library),
            'music_count': sum_files(music_library),
            'sfx_library': sfx_library,
            'music_library': music_library
        }

    except Exception as e:
        print(f"[ERROR] Failed to scan templates: {str(e)}")
        return {
            'status': 'error',
            'error': str(e)
        }


def lambda_handler(event, context):
    """
    Main Lambda handler

    Event:
    - EventBridge daily schedule
    - Manual trigger with specific template_id
    """

    print(f"[INFO] Update SFX Library Lambda")
    print(f"Event: {json.dumps(event, default=str)}")

    try:
        # Check if updating specific template
        template_id = event.get('template_id')

        if template_id:
            # Update specific template
            print(f"[INFO] Updating specific template: {template_id}")

            sfx_library = scan_s3_directory(SFX_PREFIX)
            music_library = scan_s3_directory(MUSIC_PREFIX)

            success = update_sfx_template(template_id, sfx_library, music_library)

            return {
                'statusCode': 200 if success else 500,
                'body': json.dumps({
                    'status': 'success' if success else 'failed',
                    'template_id': template_id,
                    'sfx_count': sum_files(sfx_library),
                    'music_count': sum_files(music_library)
                })
            }

        else:
            # Update all templates (daily schedule)
            result = scan_and_update_all_templates()

            return {
                'statusCode': 200,
                'body': json.dumps(result, default=str)
            }

    except Exception as e:
        print(f"[ERROR] Lambda error: {str(e)}")
        import traceback
        traceback.print_exc()

        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'error',
                'error': str(e)
            })
        }
