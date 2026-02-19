import json
import boto3
from datetime import datetime, timedelta
from decimal import Decimal
from botocore.config import Config

# WEEK 3.2: Import shared utilities
from validation_utils import validate_user_id
from response_utils import success_response, error_response, decimal_default
from dynamodb_utils import decimal_to_number, safe_query

# WEEK 2 FIX: Add timeout configuration
boto_config = Config(
    connect_timeout=5,
    read_timeout=60,
    retries={'max_attempts': 3, 'mode': 'standard'}
)

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1', config=boto_config)
s3_client = boto3.client('s3', region_name='eu-central-1', config=boto_config)
URL_EXPIRATION = 3600  # 1 hour

def generate_presigned_url(s3_url):
    """Convert s3:// URL to presigned HTTPS URL"""
    if not s3_url or not s3_url.startswith('s3://'):
        return s3_url
    
    # Parse s3://bucket/key
    parts = s3_url.replace('s3://', '').split('/', 1)
    if len(parts) != 2:
        return s3_url
    
    bucket, key = parts
    
    try:
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=URL_EXPIRATION
        )
        return presigned_url
    except Exception as e:
        print(f"Error generating presigned URL for {s3_url}: {e}")
        return s3_url

def convert_s3_urls_in_item(item):
    """Convert all s3:// URLs in item to presigned URLs"""
    # Convert audio_files
    if 'audio_files' in item and isinstance(item['audio_files'], list):
        for audio in item['audio_files']:
            if 's3_url' in audio:
                audio['s3_url'] = generate_presigned_url(audio['s3_url'])
    
    # Convert scene_images
    if 'scene_images' in item and isinstance(item['scene_images'], list):
        for img in item['scene_images']:
            if 's3_url' in img:
                img['s3_url'] = generate_presigned_url(img['s3_url'])
    
    # Convert thumbnail if exists
    if 'thumbnail' in item and isinstance(item['thumbnail'], dict):
        if 's3_url' in item['thumbnail']:
            item['thumbnail']['s3_url'] = generate_presigned_url(item['thumbnail']['s3_url'])
    
    # Convert final_video if exists
    if 'final_video' in item and isinstance(item['final_video'], dict):
        if 'video_url' in item['final_video'] and item['final_video']['video_url'].startswith('s3://'):
            item['final_video']['video_url'] = generate_presigned_url(item['final_video']['video_url'])
    
    return item

def lambda_handler(event, context):
    """
    Dashboard Content API - Multi-Tenant Version
    Endpoints:
    - GET /content/list - List all generated content for authenticated user

    Filters content by user_id to ensure data isolation.
    """

    print(f"Event: {json.dumps(event, default=str)}")

    # Handle OPTIONS preflight request for CORS
    request_context = event.get('requestContext', {})
    http_method = request_context.get('http', {}).get('method') or event.get('httpMethod', 'POST')

    if http_method == 'OPTIONS':
        print(" Handling OPTIONS preflight request")
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': 'https://n8n-creator.space',
                'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization, x-user-id',
                'Access-Control-Allow-Credentials': 'true',
                'Access-Control-Max-Age': '86400'
            },
            'body': ''
        }

    # WEEK 3.2: Use shared validation utility
    # Extract user_id from event (supports both API Gateway and Function URL formats)
    user_id = None

    # Try Function URL format (body is JSON string)
    if 'body' in event and event['body']:
        try:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            user_id = body.get('user_id')
            print(f" Extracted user_id from body: {user_id}")
        except json.JSONDecodeError:
            print(" Failed to parse body as JSON")

    # Try API Gateway format (direct user_id in event)
    if not user_id:
        user_id = event.get('user_id')
        if user_id:
            print(f" Extracted user_id from event: {user_id}")

    # WEEK 3.2: Validate user_id using shared utility
    try:
        # Create a dict with user_id for validation
        validate_user_id({'user_id': user_id} if user_id else {})
    except ValueError as e:
        print(f" Validation failed: {e}")
        return error_response(str(e), status_code=400)
        

    # Parse request
    http_method = event.get('httpMethod', 'GET')
    path = event.get('path', '')
    query_params = event.get('queryStringParameters') or {}

    try:
        # Get content list filtered by user_id
        print(f" Calling get_content_list for user {user_id} with params: {query_params}")
        response_data = get_content_list(user_id, query_params)
        print(f" Got {len(response_data.get('content', []))} items for user {user_id}")

        # WEEK 3.2: Use shared response utility
        return success_response(response_data)

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

        # WEEK 3.2: Use shared error response utility
        return error_response(str(e), status_code=500)

def get_content_list(user_id, params):
    """
    Get content from DynamoDB GeneratedContent table filtered by user_id

    Uses user_id-created_at-index for efficient queries.
    """

    table = dynamodb.Table('GeneratedContent')

    # Query by user_id using GSI (much more efficient than scan)
    print(f"Querying GeneratedContent for user_id: {user_id}")

    response = table.query(
        IndexName='user_id-created_at-index',
        KeyConditionExpression='user_id = :uid',
        ExpressionAttributeValues={':uid': user_id},
        ScanIndexForward=False  # Sort descending (newest first)
    )

    items = response.get('Items', [])

    # Handle pagination - get all items if there are more
    while 'LastEvaluatedKey' in response:
        response = table.query(
            IndexName='user_id-created_at-index',
            KeyConditionExpression='user_id = :uid',
            ExpressionAttributeValues={':uid': user_id},
            ScanIndexForward=False,
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        items.extend(response.get('Items', []))

    print(f"Found {len(items)} items for user {user_id}")

    # Defense in depth - double check user_id matches
    items = [item for item in items if item.get('user_id') == user_id]

    # Filter: only show complete content with narrative scenes
    items = [item for item in items if item.get('narrative_data', {}).get('scenes')]

    # Sort by created_at descending (newest first)
    items.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    # Take only the latest N items based on limit parameter
    limit = int(params.get('limit', 100))
    items = items[:limit]
    

    # Calculate stats
    stats = {
        'total': len(items),
        'themes': 0,
        'narratives': 0,
        'mega_narratives': 0,
        'today': 0
    }

    today = datetime.now().date()

    for item in items:
        # Convert S3 URLs to presigned URLs
        convert_s3_urls_in_item(item)

        # Count by type (MEGA MODE support)
        item_type = item.get('type', '')
        if item_type == 'theme_generation' or item_type == 'selected_topic':
            stats['themes'] += 1
        elif item_type == 'narrative_generation':
            stats['narratives'] += 1
        elif item_type in ['mega_narrative_generation', 'mega_generation']:
            stats['mega_narratives'] += 1
            stats['narratives'] += 1  # Count as narrative too

        # Count today
        created_at = item.get('created_at', '')
        if created_at:
            try:
                created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')).date()
                if created_date == today:
                    stats['today'] += 1
            except:
                pass

    # Already sorted earlier, no need to sort again

    return {
        'content': items,
        'stats': stats
    }
