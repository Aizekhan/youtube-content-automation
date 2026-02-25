"""
Re-migrate two test channels with fixed genre matching
"""
import boto3
import sys

# Add shared directory to path
sys.path.append('./aws/lambda/content-narrative/shared')
from archetype_mechanics import DEFAULT_POOLS, get_archetype_pool

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
table = dynamodb.Table('ChannelConfigs')

# Two test channels
channels = [
    {
        'channel_id': 'UCLFeJMO2Mbh-bwAQWya4-dw',
        'name': 'LifeSeeds Hub',
        'genre': 'Motivational / Parables'
    },
    {
        'channel_id': 'UC9KUaoTY4vyGGHzCccqHnAA',
        'name': 'NeuralTales Station',
        'genre': 'Science Fiction'
    }
]

for ch in channels:
    print(f"\n{ch['name']} ({ch['channel_id']})")
    print(f"  Genre: {ch['genre']}")

    # Get archetype pool with fixed genre matching
    archetype_pool = get_archetype_pool(genre=ch['genre'], custom_pool=None)
    print(f"  New Archetype Pool: {archetype_pool}")

    # Update DynamoDB
    response = table.scan(
        FilterExpression='channel_id = :cid',
        ExpressionAttributeValues={':cid': ch['channel_id']}
    )

    if response['Items']:
        config_id = response['Items'][0]['config_id']
        print(f"  Config ID: {config_id}")

        table.update_item(
            Key={'config_id': config_id},
            UpdateExpression="SET archetype_pool = :ap",
            ExpressionAttributeValues={':ap': archetype_pool}
        )

        print(f"  [OK] Updated")
    else:
        print(f"  [ERROR] Channel not found in DB")

print("\n" + "="*80)
print("RE-MIGRATION COMPLETE")
print("="*80)
