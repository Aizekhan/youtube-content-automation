"""
Queue Failed EC2 Start
Adds workflow state to SQS queue when EC2 start fails
Called by Step Functions Catch block
"""
import json
import boto3
from datetime import datetime

sqs = boto3.client('sqs', region_name='eu-central-1')

QUEUE_URL = 'https://sqs.eu-central-1.amazonaws.com/599297130956/PendingImageGeneration'

def lambda_handler(event, context):
    """
    Saves workflow state to SQS queue for retry

    INPUT from Step Functions:
    {
        "execution_arn": "arn:aws:states:...",
        "collected_prompts": {...},
        "phase1_results": [...]
    }
    """
    print("📥 Adding failed EC2 start to retry queue")
    print(f"Event: {json.dumps(event, indent=2)}")

    try:
        # Extract workflow state
        execution_arn = event.get('execution_arn', '')
        collected_prompts = event.get('collectedPrompts', {}).get('Payload', {})
        phase1_results = event.get('phase1Results', [])

        # Build message
        message = {
            'execution_arn': execution_arn,
            'collected_prompts': collected_prompts,
            'phase1_results': phase1_results,
            'queued_at': datetime.utcnow().isoformat() + 'Z',
            'retry_count': 0
        }

        # Send to SQS queue
        response = sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=json.dumps(message),
            MessageAttributes={
                'execution_arn': {
                    'StringValue': execution_arn,
                    'DataType': 'String'
                },
                'total_images': {
                    'StringValue': str(collected_prompts.get('total_images', 0)),
                    'DataType': 'Number'
                }
            }
        )

        print(f"✅ Message added to queue")
        print(f"Message ID: {response['MessageId']}")
        print(f"Total images: {collected_prompts.get('total_images', 0)}")
        print(f"Will retry every 3 minutes (max 20 attempts = 1 hour)")

        return {
            'statusCode': 200,
            'message': 'Added to retry queue',
            'message_id': response['MessageId'],
            'queue_url': QUEUE_URL
        }

    except Exception as e:
        print(f"❌ Error adding to queue: {e}")
        import traceback
        traceback.print_exc()

        return {
            'statusCode': 500,
            'error': str(e)
        }
