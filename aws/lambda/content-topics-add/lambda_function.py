"""
Content Topics Add Lambda
Sprint 1 - Task 1.2

Functionality:
- Add topic manually (user input)
- Validate fields
- Generate topic_id (UUID)
- Set status = "draft"
- Save to DynamoDB ContentTopicsQueue
"""

import json
import boto3
import uuid
from datetime import datetime
from decimal import Decimal
from botocore.config import Config

# AWS clients with timeout configuration
boto_config = Config(
    connect_timeout=5,
    read_timeout=60,
    retries={'max_attempts': 3, 'mode': 'standard'}
)

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1', config=boto_config)
topics_table = dynamodb.Table('ContentTopicsQueue')


def lambda_handler(event, context):
    """
    Add new topic to queue

    Input:
    {
      "user_id": "xxx",
      "channel_id": "UCxxx",
      "topic_text": "The Hidden Temples of Angkor Wat",
      "topic_description": {
        "context": "Historical context...",
        "tone_suggestion": "dark",
        "key_elements": ["temples", "mystery", "discovery"]
      },
      "priority": 100
    }

    Output:
    {
      "success": true,
      "topic_id": "uuid",
      "message": "Topic added successfully"
    }
    """

    print("=" * 80)
    print("Content Topics Add Lambda")
    print("=" * 80)
    print(f"Event: {json.dumps(event, default=str)[:500]}")

    # Extract parameters
    user_id = event.get('user_id')
    channel_id = event.get('channel_id')
    topic_text = event.get('topic_text')
    topic_description = event.get('topic_description', {})
    priority = event.get('priority', 100)

    # Validation
    if not user_id:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'success': False,
                'error': 'user_id is required'
            })
        }

    if not channel_id:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'success': False,
                'error': 'channel_id is required'
            })
        }

    if not topic_text or len(topic_text.strip()) == 0:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'success': False,
                'error': 'topic_text is required and cannot be empty'
            })
        }

    # Validate topic_description structure (MVP version)
    if not isinstance(topic_description, dict):
        topic_description = {}

    # Ensure MVP fields exist
    if 'context' not in topic_description:
        topic_description['context'] = ''
    if 'tone_suggestion' not in topic_description:
        topic_description['tone_suggestion'] = 'dark'
    if 'key_elements' not in topic_description:
        topic_description['key_elements'] = []

    # Validate tone_suggestion
    valid_tones = ['dark', 'emotional', 'epic', 'calm', 'light', 'mysterious', 'uplifting']
    if topic_description['tone_suggestion'] not in valid_tones:
        topic_description['tone_suggestion'] = 'dark'

    # Validate key_elements is array
    if not isinstance(topic_description['key_elements'], list):
        topic_description['key_elements'] = []

    # Generate topic_id
    topic_id = f"topic_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

    # Prepare item for DynamoDB
    timestamp = datetime.utcnow().isoformat() + 'Z'

    topic_item = {
        'channel_id': channel_id,
        'topic_id': topic_id,
        'topic_text': topic_text.strip(),
        'topic_description': topic_description,
        'priority': int(priority),
        'status': 'draft',  # draft → approved → queued → in_progress → published
        'source': 'manual',
        'created_at': timestamp,
        'updated_at': timestamp,
        'user_id': user_id
    }

    print(f"\n📝 Adding topic:")
    print(f"  topic_id: {topic_id}")
    print(f"  channel_id: {channel_id}")
    print(f"  topic_text: {topic_text}")
    print(f"  tone: {topic_description.get('tone_suggestion')}")
    print(f"  priority: {priority}")

    try:
        # Save to DynamoDB
        topics_table.put_item(Item=topic_item)

        print(f"✅ Topic saved successfully!")

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
            },
            'body': json.dumps({
                'success': True,
                'topic_id': topic_id,
                'message': 'Topic added successfully',
                'topic': {
                    'topic_id': topic_id,
                    'topic_text': topic_text,
                    'status': 'draft',
                    'priority': priority,
                    'created_at': timestamp
                }
            })
        }

    except Exception as e:
        print(f"❌ Error saving topic: {e}")
        import traceback
        traceback.print_exc()

        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
            },
            'body': json.dumps({
                'success': False,
                'error': f'Failed to save topic: {str(e)}'
            })
        }
