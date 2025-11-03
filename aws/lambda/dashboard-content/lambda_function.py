import json
import boto3
from datetime import datetime, timedelta
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def lambda_handler(event, context):
    """
    Dashboard Content API
    Endpoints:
    - GET /content/list - List all generated content
    """

    print(f"Event: {json.dumps(event, default=str)}")

    # Parse request
    http_method = event.get('httpMethod', 'GET')
    path = event.get('path', '')
    query_params = event.get('queryStringParameters') or {}

    try:
        # Get content list
        response_data = get_content_list(query_params)

        response = {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'GET,OPTIONS,DELETE'
            },
            'body': json.dumps(response_data, default=decimal_default)
        }

        return response

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e),
                'type': 'InternalError'
            })
        }

def get_content_list(params):
    """Get content from DynamoDB GeneratedContent table"""

    table = dynamodb.Table('GeneratedContent')

    # Scan the table (for now, we'll scan all items)
    # In production, you'd want to use pagination
    scan_params = {
        'Limit': int(params.get('limit', 100))
    }

    response = table.scan(**scan_params)
    items = response.get('Items', [])

    # Calculate stats
    stats = {
        'total': len(items),
        'themes': 0,
        'narratives': 0,
        'today': 0
    }

    today = datetime.now().date()

    for item in items:
        # Count by type
        if item.get('type') == 'theme_generation':
            stats['themes'] += 1
        elif item.get('type') == 'narrative_generation':
            stats['narratives'] += 1

        # Count today
        created_at = item.get('created_at', '')
        if created_at:
            try:
                created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')).date()
                if created_date == today:
                    stats['today'] += 1
            except:
                pass

    # Sort by created_at descending
    items.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    return {
        'content': items,
        'stats': stats
    }
