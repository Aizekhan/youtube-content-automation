import json
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
table = dynamodb.Table('ChannelConfigs')

def lambda_handler(event, context):
    print(f"Get Active Channels - Fixed Version")

    try:
        response = table.scan(
            FilterExpression='attribute_exists(is_active) AND is_active = :active',
            ExpressionAttributeValues={':active': True}
        )
        items = response.get('Items', [])

        channels = []
        for item in items:
            # Беремо channel_id з config_id якщо channel_name порожній
            channel_id = item.get('channel_id', '')
            config_id = item.get('config_id', '')

            # Якщо channel_name порожній - пропускаємо, але логуємо
            channel_name = item.get('channel_name', '').strip()
            if not channel_name:
                channel_name = f"Channel_{channel_id[:10]}"

            genre = item.get('genre', 'General')

            channels.append({
                'channel_id': channel_id,
                'config_id': config_id,
                'channel_name': channel_name,
                'genre': genre
            })

        result = channels[:10]  # Беремо перші 10
        print(f"Found {len(result)} active channels")
        print(f"Channels: {json.dumps(result, ensure_ascii=False)}")

        # Return proper Lambda Function URL response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'channels': result}, ensure_ascii=False)
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

        # Return error response
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e), 'channels': []})
        }
