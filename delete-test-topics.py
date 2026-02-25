import boto3
import json

dynamodb = boto3.client('dynamodb', region_name='eu-central-1')

# Test channels to delete
test_channels = [
    'series_test_channel',
    'test_channel',
    'live_test_channel',
    'sprint1_test_channel'
]

# Scan for all test topics
response = dynamodb.scan(
    TableName='ContentTopicsQueue',
    FilterExpression='channel_id IN (:ch1, :ch2, :ch3, :ch4)',
    ExpressionAttributeValues={
        ':ch1': {'S': 'series_test_channel'},
        ':ch2': {'S': 'test_channel'},
        ':ch3': {'S': 'live_test_channel'},
        ':ch4': {'S': 'sprint1_test_channel'}
    }
)

deleted_count = 0
for item in response['Items']:
    topic_id = item['topic_id']['S']
    channel_id = item['channel_id']['S']
    topic_text = item.get('topic_text', {}).get('S', 'Unknown')

    print(f"Deleting: {topic_text} ({topic_id}) from {channel_id}")

    dynamodb.delete_item(
        TableName='ContentTopicsQueue',
        Key={
            'topic_id': {'S': topic_id},
            'channel_id': {'S': channel_id}
        }
    )
    deleted_count += 1

print(f"\n✓ Deleted {deleted_count} test topics!")
