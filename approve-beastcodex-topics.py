#!/usr/bin/env python3
"""
Change status from 'pending' to 'approved' for all BeastCodex topics
"""

import boto3

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
table = dynamodb.Table('ContentTopicsQueue')

CHANNEL_ID = "UCq4jkW2gvAq_qUPcWzSgEig"

# Query all topics for this channel
response = table.query(
    KeyConditionExpression=boto3.dynamodb.conditions.Key('channel_id').eq(CHANNEL_ID)
)

topics = response.get('Items', [])
print(f"Found {len(topics)} topics for channel {CHANNEL_ID}")

# Update each topic status to "approved"
for topic in topics:
    topic_id = topic['topic_id']
    current_status = topic.get('status', 'unknown')

    if current_status == 'approved':
        print(f"  {topic_id}: already approved, skipping")
        continue

    print(f"  {topic_id}: {current_status} -> approved")

    table.update_item(
        Key={
            'channel_id': CHANNEL_ID,
            'topic_id': topic_id
        },
        UpdateExpression='SET #status = :status',
        ExpressionAttributeNames={
            '#status': 'status'
        },
        ExpressionAttributeValues={
            ':status': 'approved'
        }
    )

print(f"\nAll topics approved!")
