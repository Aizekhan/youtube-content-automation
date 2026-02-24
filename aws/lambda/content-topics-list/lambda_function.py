"""
Content Topics List Lambda
Sprint 1 - Task 1.3

Functionality:
- List all topics for channel
- Filter by status (optional)
- Sort by priority DESC + created_at DESC
- Pagination support
"""

import json
import boto3
from datetime import datetime
from decimal import Decimal
from boto3.dynamodb.conditions import Key
from botocore.config import Config

# AWS clients with timeout configuration
boto_config = Config(
    connect_timeout=5,
    read_timeout=60,
    retries={'max_attempts': 3, 'mode': 'standard'}
)

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1', config=boto_config)
topics_table = dynamodb.Table('ContentTopicsQueue')


def decimal_default(obj):
    """Helper to convert Decimal to int/float for JSON serialization"""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError


def lambda_handler(event, context):
    """
    List topics for channel

    Input:
    {
      "user_id": "xxx",
      "channel_id": "UCxxx",
      "status": "draft",  // optional filter
      "limit": 50
    }

    Output:
    {
      "topics": [
        {
          "topic_id": "...",
          "topic_text": "...",
          "status": "draft",
          "priority": 100,
          "created_at": "..."
        }
      ],
      "count": 15
    }
    """

    print("=" * 80)
    print("Content Topics List Lambda")
    print("=" * 80)
    print(f"Event: {json.dumps(event, default=str)[:500]}")

    # Extract parameters from different sources (API Gateway, Function URL, Step Functions)
    user_id = None
    channel_id = None
    status_filter = None
    limit = 50

    # Try queryStringParameters (GET request)
    if 'queryStringParameters' in event and event['queryStringParameters']:
        params = event['queryStringParameters']
        user_id = params.get('user_id')
        channel_id = params.get('channel_id')
        status_filter = params.get('status')
        limit = int(params.get('limit', 50))

    # Try body (POST request)
    if not channel_id and 'body' in event and event['body']:
        try:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            user_id = body.get('user_id')
            channel_id = body.get('channel_id')
            status_filter = body.get('status')
            limit = int(body.get('limit', 50))
        except json.JSONDecodeError:
            pass

    # Try direct parameters (Step Functions / Lambda invoke)
    if not channel_id:
        user_id = event.get('user_id')
        channel_id = event.get('channel_id')
        status_filter = event.get('status')
        limit = int(event.get('limit', 50))

    # Validation
    if not user_id:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json'
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

    print(f"\n📋 Listing topics:")
    print(f"  channel_id: {channel_id}")
    print(f"  user_id: {user_id}")
    print(f"  status filter: {status_filter or 'all'}")
    print(f"  limit: {limit}")

    try:
        # Query topics for channel
        if status_filter and status_filter != 'all':
            # Use GSI to filter by status
            print(f"  Using status-index GSI for status: {status_filter}")

            response = topics_table.query(
                IndexName='status-index',
                KeyConditionExpression=Key('channel_id').eq(channel_id) & Key('status').eq(status_filter),
                Limit=limit,
                ScanIndexForward=False  # Sort DESC by status (SK)
            )
        else:
            # Query all topics for channel
            print(f"  Querying all topics for channel")

            response = topics_table.query(
                KeyConditionExpression=Key('channel_id').eq(channel_id),
                Limit=limit,
                ScanIndexForward=False  # Sort DESC by topic_id (SK)
            )

        items = response.get('Items', [])

        # Security check: Filter only topics belonging to user
        filtered_items = []
        for item in items:
            if item.get('user_id') == user_id:
                filtered_items.append(item)
            else:
                print(f"⚠️ Skipping topic {item.get('topic_id')} - wrong user_id")

        # Sort by priority DESC, then created_at DESC
        filtered_items.sort(
            key=lambda x: (x.get('priority', 0), x.get('created_at', '')),
            reverse=True
        )

        print(f"\n✅ Found {len(filtered_items)} topics (filtered from {len(items)} total)")

        # Format topics for response
        topics = []
        for item in filtered_items:
            topic = {
                'topic_id': item.get('topic_id'),
                'topic_text': item.get('topic_text'),
                'topic_description': item.get('topic_description', {}),
                'status': item.get('status'),
                'priority': int(item.get('priority', 100)),
                'source': item.get('source'),
                'created_at': item.get('created_at'),
                'updated_at': item.get('updated_at'),
                # Series fields for Topics Manager UI
                'series_id': item.get('series_id'),
                'episode_number': int(item.get('episode_number')) if item.get('episode_number') else None,
                'channel_id': item.get('channel_id')
            }
            topics.append(topic)

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
            },
            'body': json.dumps({
                'success': True,
                'topics': topics,
                'count': len(topics),
                'channel_id': channel_id
            }, default=decimal_default)
        }

    except Exception as e:
        print(f"❌ Error listing topics: {e}")
        import traceback
        traceback.print_exc()

        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
            },
            'body': json.dumps({
                'success': False,
                'error': f'Failed to list topics: {str(e)}'
            })
        }
