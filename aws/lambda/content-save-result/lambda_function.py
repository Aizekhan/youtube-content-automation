import json
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
table = dynamodb.Table('GeneratedContent')

def lambda_handler(event, context):
    print(f"Save Result - Python Version")
    print(f"Event: {json.dumps(event, ensure_ascii=False)}")
    
    channel_id = event.get('channel_id')
    topic = event.get('topic', 'Unknown')
    narrative = event.get('narrative', 'No content')
    status = event.get('status', 'completed')
    
    created_at = datetime.utcnow().isoformat() + 'Z'
    
    try:
        table.put_item(
            Item={
                'channel_id': channel_id,
                'created_at': created_at,
                'topic': topic,
                'narrative_content': narrative,
                'status': status
            }
        )
        
        result = {
            'channel_id': channel_id,
            'status': 'saved',
            'timestamp': created_at
        }
        
        print(f"Saved to DynamoDB: {json.dumps(result, ensure_ascii=False)}")
        return result
        
    except Exception as e:
        print(f"Error saving: {str(e)}")
        return {
            'channel_id': channel_id,
            'status': 'error',
            'error': str(e)
        }
