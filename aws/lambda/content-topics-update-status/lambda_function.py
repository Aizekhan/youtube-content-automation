"""
Content Topics Update Status Lambda
Sprint 1 - Task 1.5

Functionality:
- Update topic status
- Validate state transitions
- Security: check user_id ownership

Simplified State machine:
- draft -> queued, deleted
- queued -> draft, deleted
- done -> queued (regenerate)
- failed -> queued (retry), deleted
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

# Valid status transitions (simplified workflow)
VALID_TRANSITIONS = {
    'draft': ['queued', 'deleted'],
    'queued': ['draft', 'deleted'],
    'done': ['queued'],  # Allow regenerate
    'failed': ['queued', 'deleted']  # Allow retry
}


def decimal_default(obj):
    """Helper to convert Decimal to int/float for JSON serialization"""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError


def lambda_handler(event, context):
    """
    Update topic status

    Input:
    {
      "user_id": "xxx",
      "channel_id": "UCxxx",
      "topic_id": "topic_xxx",
      "new_status": "approved",
      "metadata": {  // optional
        "failure_reason": "...",
        "video_id": "...",
        ...
      }
    }

    Output:
    {
      "success": true,
      "topic": {
        "topic_id": "...",
        "status": "approved",
        "updated_at": "..."
      }
    }
    """

    print("=" * 80)
    print("Content Topics Update Status Lambda")
    print("=" * 80)
    print(f"Event: {json.dumps(event, default=str)[:500]}")

    # Extract parameters from different sources (API Gateway, Function URL, Step Functions)
    user_id = None
    channel_id = None
    topic_id = None
    new_status = None
    metadata = {}

    # Try queryStringParameters (GET request)
    if 'queryStringParameters' in event and event['queryStringParameters']:
        params = event['queryStringParameters']
        user_id = params.get('user_id')
        channel_id = params.get('channel_id')
        topic_id = params.get('topic_id')
        new_status = params.get('new_status')

    # Try body (POST request)
    if not topic_id and 'body' in event and event['body']:
        try:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            user_id = body.get('user_id')
            channel_id = body.get('channel_id')
            topic_id = body.get('topic_id')
            new_status = body.get('new_status')
            metadata = body.get('metadata', {})
        except json.JSONDecodeError:
            pass

    # Try direct parameters (Step Functions / Lambda invoke)
    if not topic_id:
        user_id = event.get('user_id')
        channel_id = event.get('channel_id')
        topic_id = event.get('topic_id')
        new_status = event.get('new_status')
        metadata = event.get('metadata', {})

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

    if not topic_id:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
            },
            'body': json.dumps({
                'success': False,
                'error': 'topic_id is required'
            })
        }

    if not new_status:
        return {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json',
            },
            'body': json.dumps({
                'success': False,
                'error': 'new_status is required'
            })
        }

    print(f"\nUpdating topic status:")
    print(f"  channel_id: {channel_id}")
    print(f"  topic_id: {topic_id}")
    print(f"  new_status: {new_status}")
    print(f"  user_id: {user_id}")

    try:
        # Get current topic to check ownership and current status
        response = topics_table.get_item(
            Key={
                'channel_id': channel_id,
                'topic_id': topic_id
            }
        )

        if 'Item' not in response:
            print(f"  TOPIC_NOT_FOUND")
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                },
                'body': json.dumps({
                    'success': False,
                    'error': 'TOPIC_NOT_FOUND',
                    'message': 'Topic not found'
                })
            }

        topic = response['Item']

        # Security check: verify user_id ownership
        if topic.get('user_id') != user_id:
            print(f"  ACCESS_DENIED - wrong user_id")
            return {
                'statusCode': 403,
                'headers': {
                    'Content-Type': 'application/json',
                },
                'body': json.dumps({
                    'success': False,
                    'error': 'ACCESS_DENIED',
                    'message': 'You do not have permission to update this topic'
                })
            }

        current_status = topic.get('status', 'draft')
        print(f"  current_status: {current_status}")

        # Validate state transition
        if current_status not in VALID_TRANSITIONS:
            print(f"  INVALID_CURRENT_STATUS: {current_status}")
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                },
                'body': json.dumps({
                    'success': False,
                    'error': 'INVALID_CURRENT_STATUS',
                    'message': f'Unknown current status: {current_status}'
                })
            }

        if new_status not in VALID_TRANSITIONS[current_status]:
            print(f"  INVALID_TRANSITION: {current_status} -> {new_status}")
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                },
                'body': json.dumps({
                    'success': False,
                    'error': 'INVALID_TRANSITION',
                    'message': f'Cannot transition from {current_status} to {new_status}',
                    'valid_transitions': VALID_TRANSITIONS[current_status]
                })
            }

        print(f"  Transition valid: {current_status} -> {new_status}")

        # Update status
        timestamp = datetime.utcnow().isoformat() + 'Z'

        update_expr = 'SET #status = :status, updated_at = :updated_at'
        expr_attr_names = {'#status': 'status'}
        expr_attr_values = {
            ':status': new_status,
            ':updated_at': timestamp
        }

        # Add metadata if provided (store as single map attribute)
        if metadata and isinstance(metadata, dict) and len(metadata) > 0:
            update_expr += ', metadata = :metadata'
            expr_attr_values[':metadata'] = metadata
            print(f"  metadata = {metadata}")

        topics_table.update_item(
            Key={
                'channel_id': channel_id,
                'topic_id': topic_id
            },
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_attr_names,
            ExpressionAttributeValues=expr_attr_values
        )

        print(f"\n  Status updated successfully")

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
            },
            'body': json.dumps({
                'success': True,
                'topic': {
                    'topic_id': topic_id,
                    'status': new_status,
                    'updated_at': timestamp,
                    'previous_status': current_status
                },
                'message': f'Topic status updated from {current_status} to {new_status}'
            }, default=decimal_default)
        }

    except Exception as e:
        print(f"  Error updating topic status: {e}")
        import traceback
        traceback.print_exc()

        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
            },
            'body': json.dumps({
                'success': False,
                'error': f'Failed to update topic status: {str(e)}'
            })
        }
