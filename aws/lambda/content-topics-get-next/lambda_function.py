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


def is_function_url_invocation(event):
    """Detect if Lambda was invoked via Function URL (vs Step Functions/direct invoke)"""
    # Function URL requests have 'requestContext' or 'body' as string
    return ('requestContext' in event or
            ('body' in event and isinstance(event.get('body'), str)) or
            'queryStringParameters' in event)


def create_response(status_code, data, event):
    """Create response in appropriate format (Function URL vs Step Functions)"""
    if is_function_url_invocation(event):
        # Function URL format: with statusCode, headers, body
        return {
            'statusCode': status_code,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(data, default=decimal_default)
        }
    else:
        # Step Functions / direct invoke format: plain object
        return data


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
        return create_response(400, {
            'success': False,
            'error': 'user_id is required'
        }, event)

    if not channel_id:
        return create_response(400, {
            'success': False,
            'error': 'channel_id is required'
        }, event)

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
            return create_response(404, {
                'success': False,
                'error': 'NO_TOPICS_AVAILABLE',
                'message': 'No approved or queued topics found for this channel'
            }, event)

        # Sort by priority DESC, then by episode_number ASC (for series)
        # This ensures:
        # 1. Higher priority topics come first
        # 2. Within same priority, episodes are processed in order (ep1, ep2, ep3...)
        filtered_topics.sort(
            key=lambda x: (
                -x.get('priority', 0),  # Negative for DESC
                x.get('episode_number', 9999)  # ASC, non-episodes go last
            )
        )

        # Get the first topic (highest priority, or earliest episode in series)
        next_topic = filtered_topics[0]

        print(f"\n  Selected topic: {next_topic['topic_id']}")
        print(f"    priority: {next_topic.get('priority')}")
        print(f"    status: {next_topic.get('status')} -> in_progress")

        # Log series information if present
        if next_topic.get('series_id'):
            print(f"    series_id: {next_topic.get('series_id')}")
            print(f"    season: {next_topic.get('season', 1)}")
            print(f"    episode_number: {next_topic.get('episode_number', 'N/A')}")

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

        # Add series metadata if present
        if next_topic.get('series_id'):
            topic_response['series_id'] = next_topic.get('series_id')
            topic_response['season'] = int(next_topic.get('season', 1))
            if next_topic.get('episode_number'):
                topic_response['episode_number'] = int(next_topic.get('episode_number'))

        print(f"\n  Topic marked as in_progress")

        return create_response(200, {
            'success': True,
            'topic': topic_response
        }, event)

    except Exception as e:
        print(f"  Error getting next topic: {e}")
        import traceback
        traceback.print_exc()

        return create_response(500, {
            'success': False,
            'error': f'Failed to get next topic: {str(e)}'
        }, event)
