import json
import boto3
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
table = dynamodb.Table('ChannelConfigs')

def decimal_default(obj):
    """Helper to convert Decimal to int/float for JSON serialization"""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError

def lambda_handler(event, context):
    """
    Get Active Channels - Multi-Tenant Version with Active Filter

    Filters channels by user_id to ensure data isolation.
    Optionally filters for active channels only (default: true).
    Returns only channels belonging to the authenticated user.
    """
    print(f"Get Active Channels - Multi-Tenant + Active Filter")
    print(f"Event: {json.dumps(event, default=str)}")

    # Extract user_id and active_only from event (supports multiple formats)
    user_id = None
    active_only = True  # Default to True

    # Try queryStringParameters (GET request from API Gateway/Function URL)
    if 'queryStringParameters' in event and event['queryStringParameters']:
        params = event['queryStringParameters']
        user_id = params.get('user_id')
        if 'active_only' in params:
            active_only = params.get('active_only', 'true').lower() == 'true'
        if user_id:
            print(f"Extracted from queryStringParameters - user_id: {user_id}, active_only: {active_only}")

    # Try Function URL format (body is JSON string)
    if not user_id and 'body' in event and event['body']:
        try:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            user_id = body.get('user_id')
            # Also extract active_only from body
            if 'active_only' in body:
                active_only = body.get('active_only')
                # Handle string "false" or "true"
                if isinstance(active_only, str):
                    active_only = active_only.lower() == 'true'
            print(f"Extracted from body - user_id: {user_id}, active_only: {active_only}")
        except json.JSONDecodeError:
            print("Failed to parse body as JSON")

    # Try API Gateway format (direct user_id in event)
    if not user_id:
        user_id = event.get('user_id')
        if user_id:
            print(f"Extracted user_id from event: {user_id}")

    # Try to get active_only from event if not already set
    if 'active_only' in event and user_id:
        active_only = event.get('active_only', True)
        if isinstance(active_only, str):
            active_only = active_only.lower() == 'true'

    # Require user_id for security (return error instead of raising exception)
    if not user_id:
        error_msg = "SECURITY ERROR: user_id is required for all requests"
        print(f"ERROR: {error_msg}")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': error_msg, 'success': False})
        }

    print(f"Final filter - active_only: {active_only}")

    try:
        # Query by user_id using GSI
        print(f"Querying channels for user_id: {user_id}")

        response = table.query(
            IndexName='user_id-channel_id-index',
            KeyConditionExpression='user_id = :uid',
            ExpressionAttributeValues={
                ':uid': user_id
            }
        )

        items = response.get('Items', [])
        print(f"Found {len(items)} channels for user {user_id}")

        channels = []
        for item in items:
            # Double-check user_id matches
            if item.get('user_id') != user_id:
                print(f"WARNING: Skipping channel {item.get('channel_id')} - wrong user_id")
                continue

            # Filter by active status if requested
            is_channel_active = item.get('is_active', False) or item.get('active', False)
            if active_only and not is_channel_active:
                continue

            channel_id = item.get('channel_id', '')
            config_id = item.get('config_id', '')

            # Handle empty channel names
            channel_title = item.get('channel_title', '').strip()
            channel_name = item.get('channel_name', '').strip()
            display_name = channel_title or channel_name or f"Channel_{channel_id[:10]}"

            genre = item.get('genre', 'General')

            # Build channel object with ALL fields
            channel = {
                'channel_id': channel_id,
                'config_id': config_id,
                'channel_name': display_name,
                'channel_title': display_name,
                'genre': genre,
                'is_active': is_channel_active,
                'user_id': user_id,
                'daily_upload_count': item.get('daily_upload_count', 1),
                'videos_per_week': item.get('videos_per_week', 3),
                'publish_times': item.get('publish_times', ''),
                'publish_days': item.get('publish_days', ''),
                'view_count': item.get('view_count', 0),
                'subscriber_count': item.get('subscriber_count', 0),
                'video_count': item.get('video_count', 0),
                'statistics': item.get('statistics', {}),
                'token_expiry': item.get('token_expiry', ''),
                'content_count': item.get('content_count', 0),
                'factual_mode': item.get('factual_mode', 'fictional'),
                'language': item.get('language', 'en')
            }

            channels.append(channel)

        print(f"Returning {len(channels)} channels (active_only={active_only})")

        # Convert Decimals to int/float for JSON serialization
        channels_json = json.loads(json.dumps(channels, default=decimal_default))

        return channels_json

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return []
