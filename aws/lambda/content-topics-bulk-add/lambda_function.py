"""
Content Topics Bulk Add Lambda
Sprint 1 - Extension for Manual Bulk Input

Functionality:
- Add multiple topics at once (bulk import)
- Support for series/episodes (series_id, episode_number)
- Auto-detect episode numbers from text
- Manual control for producers/creators
- 100+ topics in one request

Use Cases:
- Manual series planning (100 episode names)
- True crime series (episode list)
- Documentary series planning
- Educational content series
"""

import json
import boto3
import uuid
import re
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


def detect_episode_number(text):
    """
    Auto-detect episode number from text

    Patterns:
    - Episode 1 – The Title
    - Ep 1: Title
    - S01E01 - Title
    - #1 Title
    - 1. Title
    """
    patterns = [
        r'Episode\s+(\d+)',
        r'Ep\.?\s*(\d+)',
        r'S\d+E(\d+)',
        r'#(\d+)',
        r'^(\d+)\.',
        r'^(\d+)\s*[-–—:]',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))

    return None


def lambda_handler(event, context):
    """
    Bulk add topics to queue

    Input:
    {
      "user_id": "xxx",
      "channel_id": "UCxxx",
      "topics": [
        "Episode 1 – The Whispering Shore",
        "Episode 2 – Beneath the Black Tide",
        "Episode 3 – The Forgotten Depths"
      ],
      "default_priority": 100,
      "default_status": "draft",
      "series_id": "deep_sea_saga_v1",  // optional - for series
      "season": 1,                       // optional
      "auto_detect_episode": true,       // auto-detect episode numbers
      "tone_suggestion": "dark",         // default tone for all
      "key_elements": ["mystery", "ocean"]  // default elements
    }

    Output:
    {
      "success": true,
      "topics_added": 100,
      "topic_ids": ["topic_xxx", "topic_yyy", ...],
      "series_id": "deep_sea_saga_v1",
      "episodes_detected": 100
    }
    """

    print("=" * 80)
    print("Content Topics Bulk Add Lambda")
    print("=" * 80)
    print(f"Event: {json.dumps(event, default=str)[:500]}")

    # Extract parameters from different sources (Function URL, Step Functions, Direct)
    user_id = None
    channel_id = None
    topics_input = []
    default_priority = 100
    default_status = 'draft'
    series_id = None
    season = 1
    auto_detect_episode = True
    tone_suggestion = 'dark'
    key_elements = []

    # Try body (POST request via Function URL)
    if 'body' in event and event['body']:
        try:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            user_id = body.get('user_id')
            channel_id = body.get('channel_id')
            topics_input = body.get('topics', [])
            default_priority = body.get('default_priority', 100)
            default_status = body.get('default_status', 'draft')
            series_id = body.get('series_id')
            season = body.get('season', 1)
            auto_detect_episode = body.get('auto_detect_episode', True)
            tone_suggestion = body.get('tone_suggestion', 'dark')
            key_elements = body.get('key_elements', [])
        except json.JSONDecodeError:
            pass

    # Try direct parameters (Step Functions / Lambda invoke)
    if not channel_id:
        user_id = event.get('user_id')
        channel_id = event.get('channel_id')
        topics_input = event.get('topics', [])
        default_priority = event.get('default_priority', 100)
        default_status = event.get('default_status', 'draft')
        series_id = event.get('series_id')
        season = event.get('season', 1)
        auto_detect_episode = event.get('auto_detect_episode', True)
        tone_suggestion = event.get('tone_suggestion', 'dark')
        key_elements = event.get('key_elements', [])

    # Validation
    if not user_id:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
            },
            'body': json.dumps({
                'success': False,
                'error': 'user_id is required'
            })
        }

    if not channel_id:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
            },
            'body': json.dumps({
                'success': False,
                'error': 'channel_id is required'
            })
        }

    if not topics_input or len(topics_input) == 0:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
            },
            'body': json.dumps({
                'success': False,
                'error': 'topics array is required and cannot be empty'
            })
        }

    # Limit bulk size (prevent abuse)
    if len(topics_input) > 500:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
            },
            'body': json.dumps({
                'success': False,
                'error': f'Maximum 500 topics per bulk request (got {len(topics_input)})'
            })
        }

    print(f"\nBulk adding {len(topics_input)} topics:")
    print(f"  user_id: {user_id}")
    print(f"  channel_id: {channel_id}")
    print(f"  default_priority: {default_priority}")
    print(f"  default_status: {default_status}")
    print(f"  series_id: {series_id or 'None (standalone topics)'}")
    print(f"  season: {season}")
    print(f"  auto_detect_episode: {auto_detect_episode}")

    timestamp_base = datetime.utcnow().isoformat() + 'Z'
    created_topic_ids = []
    episodes_detected = 0

    try:
        # Process each topic
        for idx, topic_text in enumerate(topics_input):
            topic_text = topic_text.strip()

            if not topic_text:
                print(f"  Skipping empty line {idx+1}")
                continue

            # Generate topic_id
            topic_id = f"topic_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"

            # Detect episode number if enabled
            episode_number = None
            if auto_detect_episode:
                detected = detect_episode_number(topic_text)
                if detected:
                    episode_number = detected
                    episodes_detected += 1
                    print(f"  [{idx+1}] Detected episode {episode_number}: {topic_text[:50]}...")
                else:
                    # Fallback: use sequential number
                    episode_number = idx + 1
                    print(f"  [{idx+1}] Auto-assigned episode {episode_number}: {topic_text[:50]}...")

            # Build topic_description
            topic_description = {
                'context': f'Bulk imported topic {idx+1}',
                'tone_suggestion': tone_suggestion,
                'key_elements': key_elements
            }

            # Build topic item
            topic_item = {
                'channel_id': channel_id,
                'topic_id': topic_id,
                'topic_text': topic_text,
                'topic_description': topic_description,
                'priority': int(default_priority),
                'status': default_status,
                'source': 'bulk_manual',
                'created_at': timestamp_base,
                'updated_at': timestamp_base,
                'user_id': user_id
            }

            # Add series metadata if series_id provided
            if series_id:
                topic_item['series_id'] = series_id
                topic_item['season'] = int(season)
                if episode_number:
                    topic_item['episode_number'] = episode_number

            # Save to DynamoDB
            topics_table.put_item(Item=topic_item)
            created_topic_ids.append(topic_id)

        print(f"\n  Successfully added {len(created_topic_ids)} topics")
        if series_id:
            print(f"  Series: {series_id}, Season {season}")
        if episodes_detected > 0:
            print(f"  Auto-detected episode numbers: {episodes_detected}")

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
            },
            'body': json.dumps({
                'success': True,
                'topics_added': len(created_topic_ids),
                'topic_ids': created_topic_ids,
                'series_id': series_id,
                'season': season if series_id else None,
                'episodes_detected': episodes_detected if auto_detect_episode else None,
                'message': f'Successfully added {len(created_topic_ids)} topics'
            })
        }

    except Exception as e:
        print(f"  Error during bulk add: {e}")
        import traceback
        traceback.print_exc()

        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
            },
            'body': json.dumps({
                'success': False,
                'error': f'Failed to bulk add topics: {str(e)}',
                'topics_added_before_error': len(created_topic_ids)
            })
        }
