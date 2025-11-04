import json
import boto3
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
table = dynamodb.Table('GeneratedContent')

def convert_floats_to_decimal(obj):
    """Recursively convert float values to Decimal for DynamoDB compatibility"""
    if isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_floats_to_decimal(value) for key, value in obj.items()}
    elif isinstance(obj, float):
        return Decimal(str(obj))
    return obj

def lambda_handler(event, context):
    print(f"Save Result - Python Version with Audio Support")
    print(f"Event: {json.dumps(event, ensure_ascii=False, default=str)}")

    channel_id = event.get('channel_id')
    topic = event.get('topic', 'Unknown')
    narrative = event.get('narrative', 'No content')
    status = event.get('status', 'completed')

    # Audio data (optional)
    audio_files = event.get('audio_files', [])
    audio_duration_sec = event.get('audio_duration_sec', 0)

    created_at = datetime.utcnow().isoformat() + 'Z'

    # Build item with all data
    item = {
        'channel_id': channel_id,
        'created_at': created_at,
        'type': 'narrative_generation',
        'topic': topic,
        'status': status
    }

    # Add narrative data if it's a dict with full structure
    if isinstance(narrative, dict):
        item['story_title'] = narrative.get('story_title', topic)
        item['full_response'] = narrative
        item['character_count'] = narrative.get('character_count', 0)
        item['narrative_text'] = narrative.get('narrative_text', '')
    else:
        item['narrative_content'] = narrative

    # Add audio data if available
    if audio_files:
        item['audio_files'] = audio_files
        item['audio_duration_sec'] = audio_duration_sec
        item['has_audio'] = True
    else:
        item['has_audio'] = False

    try:
        # Convert all floats to Decimal for DynamoDB
        item = convert_floats_to_decimal(item)

        table.put_item(Item=item)

        result = {
            'channel_id': channel_id,
            'status': 'saved',
            'timestamp': created_at,
            'has_audio': len(audio_files) > 0,
            'audio_scene_count': len(audio_files)
        }

        print(f"Saved to DynamoDB: {json.dumps(result, ensure_ascii=False)}")
        return result

    except Exception as e:
        print(f"Error saving: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'channel_id': channel_id,
            'status': 'error',
            'error': str(e)
        }
