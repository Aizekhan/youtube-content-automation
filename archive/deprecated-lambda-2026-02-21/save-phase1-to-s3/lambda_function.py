import json
import boto3
import os
from datetime import datetime

s3_client = boto3.client('s3', region_name='eu-central-1')
BUCKET_NAME = 'youtube-automation-data-grucia'

def lambda_handler(event, context):
    """
    Save Phase1 result to S3 and return only reference
    This reduces Step Functions state size
    """
    print(f"Event: {json.dumps(event, default=str)}")

    try:
        # Extract data from event
        channel_id = event.get('channel_id')
        user_id = event.get('user_id')

        if not channel_id or not user_id:
            raise ValueError("Missing channel_id or user_id")

        # Generate S3 key
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        s3_key = f"phase1-results/{user_id}/{channel_id}/{timestamp}.json"

        # Save full result to S3
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Body=json.dumps(event, default=str),
            ContentType='application/json'
        )

        print(f"Saved Phase1 result to s3://{BUCKET_NAME}/{s3_key}")

        # Return minimal reference
        return {
            'channel_id': channel_id,
            'user_id': user_id,
            's3_bucket': BUCKET_NAME,
            's3_key': s3_key,
            'timestamp': timestamp,
            # Include minimal metadata for downstream processing
            'has_images': bool(event.get('narrativeResult', {}).get('Payload', {}).get('image_prompts')),
            'channel_name': event.get('channel_name', ''),
            'genre': event.get('genre', '')
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
