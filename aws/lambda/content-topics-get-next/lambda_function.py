"""
Content Topics Get Next Lambda
Sprint 1 - Task 1.4

Functionality:
- Get next topic from queue (status = "approved" or "queued")
- Sort by priority DESC
- Update status to "in_progress"
- Return topic data
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
    Get next topic from queue

    Input:
    {
      "user_id": "xxx",
      "channel_id": "UCxxx"
    }

    Output:
    {
      "success": true,
      "topic": {
        "topic_id": "...",
        "topic_text": "...",
        "topic_description": {...},
        "status": "in_progress",
        "priority": 100
      }
    }

    If no topics available:
    {
      "success": false,
      "error": "NO_TOPICS_AVAILABLE"
    }
    """

    print("=" * 80)
    print("Content Topics Get Next Lambda")
    print("=" * 80)
    print(f"Event: {json.dumps(event, default=str)[:500]}")

    # Extract parameters from different sources (API Gateway, Function URL, Step Functions)
    user_id = None
    channel_id = None

    # Try queryStringParameters (GET request)
    if 'queryStringParameters' in event and event['queryStringParameters']:
        params = event['queryStringParameters']
        user_id = params.get('user_id')
        channel_id = params.get('channel_id')

    # Try body (POST request)
    if not channel_id and 'body' in event and event['body']:
        try:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            user_id = body.get('user_id')
            channel_id = body.get('channel_id')
        except json.JSONDecodeError:
            pass

    # Try direct parameters (Step Functions / Lambda invoke)
    if not channel_id:
        user_id = event.get('user_id')
        channel_id = event.get('channel_id')

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

    print(f"\nGetting next topic for:")
    print(f"  channel_id: {channel_id}")
    print(f"  user_id: {user_id}")

    try:
        # Query topics with status "approved" or "queued"
        # First try "approved"
        print(f"\n  Querying topics with status='approved'")

        response_approved = topics_table.query(
            IndexName='status-index',
            KeyConditionExpression=Key('channel_id').eq(channel_id) & Key('status').eq('approved'),
            Limit=50,
            ScanIndexForward=False
        )

        # Then try "queued"
        print(f"  Querying topics with status='queued'")

        response_queued = topics_table.query(
            IndexName='status-index',
            KeyConditionExpression=Key('channel_id').eq(channel_id) & Key('status').eq('queued'),
            Limit=50,
            ScanIndexForward=False
        )

        # Combine results
        all_topics = response_approved.get('Items', []) + response_queued.get('Items', [])

        print(f"\n  Found {len(all_topics)} topics (approved + queued)")

        # Security check: Filter only topics belonging to user
        filtered_topics = []
        for item in all_topics:
            if item.get('user_id') == user_id:
                filtered_topics.append(item)
            else:
                print(f"  Skipping topic {item.get('topic_id')} - wrong user_id")

        if len(filtered_topics) == 0:
            print("\n  NO_TOPICS_AVAILABLE")
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                },
                'body': json.dumps({
                    'success': False,
                    'error': 'NO_TOPICS_AVAILABLE',
                    'message': 'No approved or queued topics found for this channel'
                })
            }

        # Sort by priority DESC
        filtered_topics.sort(key=lambda x: x.get('priority', 0), reverse=True)

        # Get the first topic (highest priority)
        next_topic = filtered_topics[0]

        print(f"\n  Selected topic: {next_topic['topic_id']}")
        print(f"    priority: {next_topic.get('priority')}")
        print(f"    status: {next_topic.get('status')} -> in_progress")

        # Update status to "in_progress"
        timestamp = datetime.utcnow().isoformat() + 'Z'

        topics_table.update_item(
            Key={
                'channel_id': channel_id,
                'topic_id': next_topic['topic_id']
            },
            UpdateExpression='SET #status = :status, updated_at = :updated_at',
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':status': 'in_progress',
                ':updated_at': timestamp
            }
        )

        # Prepare response topic
        topic_response = {
            'topic_id': next_topic.get('topic_id'),
            'topic_text': next_topic.get('topic_text'),
            'topic_description': next_topic.get('topic_description', {}),
            'status': 'in_progress',
            'priority': int(next_topic.get('priority', 100)),
            'source': next_topic.get('source'),
            'created_at': next_topic.get('created_at'),
            'updated_at': timestamp
        }

        print(f"\n  Topic marked as in_progress")

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
            },
            'body': json.dumps({
                'success': True,
                'topic': topic_response
            }, default=decimal_default)
        }

    except Exception as e:
        print(f"  Error getting next topic: {e}")
        import traceback
        traceback.print_exc()

        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
            },
            'body': json.dumps({
                'success': False,
                'error': f'Failed to get next topic: {str(e)}'
            })
        }
