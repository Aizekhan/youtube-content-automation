import boto3
import json

dynamodb = boto3.client('dynamodb', region_name='eu-central-1')

# Scan all channels
response = dynamodb.scan(TableName='ChannelConfigs')

channels = response['Items']
print(f"Found {len(channels)} channels")

updated_count = 0
skipped_count = 0

for channel in channels:
    config_id = channel['config_id']['S']
    channel_id = channel.get('channel_id', {}).get('S', 'Unknown')

    # Check if channel has variation_sets fields
    has_variation_sets = 'variation_sets' in channel
    has_rotation_mode = 'rotation_mode' in channel
    has_generation_count = 'generation_count' in channel

    if not (has_variation_sets or has_rotation_mode or has_generation_count):
        skipped_count += 1
        continue

    print(f"\nUpdating: {channel_id} ({config_id})")
    if has_variation_sets:
        print(f"  - Removing variation_sets")
    if has_rotation_mode:
        print(f"  - Removing rotation_mode")
    if has_generation_count:
        print(f"  - Removing generation_count")

    # Build REMOVE expression
    remove_fields = []
    if has_variation_sets:
        remove_fields.append('variation_sets')
    if has_rotation_mode:
        remove_fields.append('rotation_mode')
    if has_generation_count:
        remove_fields.append('generation_count')

    update_expression = 'REMOVE ' + ', '.join(remove_fields)

    # Update DynamoDB
    dynamodb.update_item(
        TableName='ChannelConfigs',
        Key={'config_id': {'S': config_id}},
        UpdateExpression=update_expression
    )

    updated_count += 1

print(f"\n=== COMPLETE ===")
print(f"Updated: {updated_count} channels")
print(f"Skipped: {skipped_count} channels (no variation_sets fields)")
print(f"Total: {len(channels)} channels")
