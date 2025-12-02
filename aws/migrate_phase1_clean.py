#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Migration Phase 1 - Add user_id to critical tables
"""

import boto3
from datetime import datetime, timezone

REGION = 'eu-central-1'
ADMIN_USER_ID = 'admin-legacy-user'

dynamodb = boto3.client('dynamodb', region_name=REGION)
dynamodb_resource = boto3.resource('dynamodb', region_name=REGION)

print("Database Migration - Phase 1")
print("=" * 50)
print()

# Step 1: Add GSI to YouTubeCredentials
print("Step 1: Adding user_id GSI to YouTubeCredentials...")

try:
    response = dynamodb.update_table(
        TableName='YouTubeCredentials',
        AttributeDefinitions=[
            {'AttributeName': 'user_id', 'AttributeType': 'S'}
        ],
        GlobalSecondaryIndexUpdates=[
            {
                'Create': {
                    'IndexName': 'user_id-index',
                    'KeySchema': [
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            }
        ]
    )
    print("[OK] GSI creation initiated")
    print("   Waiting for index to build...")
    waiter = dynamodb.get_waiter('table_exists')
    waiter.wait(TableName='YouTubeCredentials')
    print("[OK] YouTubeCredentials GSI ready")
except Exception as e:
    if 'ResourceInUseException' in str(e) or 'already exists' in str(e):
        print("[SKIP] GSI already exists, skipping...")
    else:
        print(f"[WARN] Error: {e}")

print()

# Step 2: Update existing YouTubeCredentials records
print("Step 2: Adding user_id to existing YouTubeCredentials records...")

table = dynamodb_resource.Table('YouTubeCredentials')

try:
    response = table.scan()
    items = response.get('Items', [])

    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))

    print(f"Found {len(items)} records")

    updated_count = 0
    skipped_count = 0

    for item in items:
        channel_id = item.get('channel_id')

        if 'user_id' in item and item['user_id']:
            print(f"  [SKIP] {channel_id} - already has user_id")
            skipped_count += 1
            continue

        try:
            table.update_item(
                Key={'channel_id': channel_id},
                UpdateExpression='SET user_id = :uid, updated_at = :updated',
                ExpressionAttributeValues={
                    ':uid': ADMIN_USER_ID,
                    ':updated': datetime.now(timezone.utc).isoformat()
                }
            )
            print(f"  [OK] Updated {channel_id}")
            updated_count += 1
        except Exception as e:
            print(f"  [ERROR] Error updating {channel_id}: {e}")

    print(f"\n[OK] YouTubeCredentials migration complete:")
    print(f"   Updated: {updated_count}")
    print(f"   Skipped: {skipped_count}")
    print(f"   Total: {len(items)}")

except Exception as e:
    print(f"[ERROR] Error: {e}")

print()

# Step 3: Add GSI to ChannelConfigs
print("Step 3: Adding user_id GSI to ChannelConfigs...")

try:
    response = dynamodb.update_table(
        TableName='ChannelConfigs',
        AttributeDefinitions=[
            {'AttributeName': 'user_id', 'AttributeType': 'S'},
            {'AttributeName': 'channel_id', 'AttributeType': 'S'}
        ],
        GlobalSecondaryIndexUpdates=[
            {
                'Create': {
                    'IndexName': 'user_id-channel_id-index',
                    'KeySchema': [
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'channel_id', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            }
        ]
    )
    print("[OK] GSI creation initiated")
    print("   Waiting for index to build...")
    waiter = dynamodb.get_waiter('table_exists')
    waiter.wait(TableName='ChannelConfigs')
    print("[OK] ChannelConfigs GSI ready")
except Exception as e:
    if 'ResourceInUseException' in str(e) or 'already exists' in str(e):
        print("[SKIP] GSI already exists, skipping...")
    else:
        print(f"[WARN] Error: {e}")

print()

# Step 4: Update existing ChannelConfigs records
print("Step 4: Adding user_id to existing ChannelConfigs records...")

table = dynamodb_resource.Table('ChannelConfigs')

try:
    response = table.scan()
    items = response.get('Items', [])

    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))

    print(f"Found {len(items)} records")

    updated_count = 0
    skipped_count = 0

    for item in items:
        config_id = item.get('config_id')
        channel_id = item.get('channel_id', 'unknown')

        if 'user_id' in item and item['user_id']:
            print(f"  [SKIP] {channel_id} - already has user_id")
            skipped_count += 1
            continue

        try:
            table.update_item(
                Key={'config_id': config_id},
                UpdateExpression='SET user_id = :uid, updated_at = :updated',
                ExpressionAttributeValues={
                    ':uid': ADMIN_USER_ID,
                    ':updated': datetime.now(timezone.utc).isoformat()
                }
            )
            print(f"  [OK] Updated {channel_id} (config: {config_id})")
            updated_count += 1
        except Exception as e:
            print(f"  [ERROR] Error updating {config_id}: {e}")

    print(f"\n[OK] ChannelConfigs migration complete:")
    print(f"   Updated: {updated_count}")
    print(f"   Skipped: {skipped_count}")
    print(f"   Total: {len(items)}")

except Exception as e:
    print(f"[ERROR] Error: {e}")

print()
print("=" * 50)
print("[OK] Phase 1 Migration Complete!")
print("=" * 50)
print()
print(f"All existing data assigned to: {ADMIN_USER_ID}")
print()
