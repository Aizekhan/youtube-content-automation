#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Migration Phase 2 - Add user_id to remaining tables
"""

import boto3
from datetime import datetime, timezone

REGION = 'eu-central-1'
ADMIN_USER_ID = 'admin-legacy-user'

dynamodb = boto3.client('dynamodb', region_name=REGION)
dynamodb_resource = boto3.resource('dynamodb', region_name=REGION)

print("Database Migration - Phase 2")
print("=" * 50)
print()

# ==============================================
# GeneratedContent
# ==============================================
print("Step 1: Migrating GeneratedContent...")
print()

print("  Creating user_id-created_at GSI...")
try:
    response = dynamodb.update_table(
        TableName='GeneratedContent',
        AttributeDefinitions=[
            {'AttributeName': 'user_id', 'AttributeType': 'S'},
            {'AttributeName': 'created_at', 'AttributeType': 'S'}
        ],
        GlobalSecondaryIndexUpdates=[
            {
                'Create': {
                    'IndexName': 'user_id-created_at-index',
                    'KeySchema': [
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            }
        ]
    )
    print("  [OK] GSI creation initiated")
    waiter = dynamodb.get_waiter('table_exists')
    waiter.wait(TableName='GeneratedContent')
    print("  [OK] GSI ready")
except Exception as e:
    if 'ResourceInUseException' in str(e) or 'already exists' in str(e):
        print("  [SKIP] GSI already exists")
    else:
        print(f"  [WARN] Error: {e}")

# Update records
table = dynamodb_resource.Table('GeneratedContent')

print("\n  Scanning records...")
try:
    response = table.scan()
    items = response.get('Items', [])

    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))

    print(f"  Found {len(items)} records")

    updated = 0
    skipped = 0
    for item in items:
        if 'user_id' in item:
            skipped += 1
            continue

        try:
            table.update_item(
                Key={
                    'channel_id': item['channel_id'],
                    'created_at': item['created_at']
                },
                UpdateExpression='SET user_id = :uid',
                ExpressionAttributeValues={':uid': ADMIN_USER_ID}
            )
            updated += 1
            if updated % 10 == 0:
                print(f"    Progress: {updated}/{len(items)}")
        except Exception as e:
            print(f"    [ERROR]: {e}")

    print(f"\n  [OK] GeneratedContent: Updated {updated}, Skipped {skipped}")
except Exception as e:
    print(f"  [ERROR] {e}")

print("\n[OK] GeneratedContent migrated")
print()

# ==============================================
# CostTracking
# ==============================================
print("Step 2: Migrating CostTracking...")
print()

print("  Creating user_id-date GSI...")
try:
    response = dynamodb.update_table(
        TableName='CostTracking',
        AttributeDefinitions=[
            {'AttributeName': 'user_id', 'AttributeType': 'S'},
            {'AttributeName': 'date', 'AttributeType': 'S'}
        ],
        GlobalSecondaryIndexUpdates=[
            {
                'Create': {
                    'IndexName': 'user_id-date-index',
                    'KeySchema': [
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'date', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            }
        ]
    )
    print("  [OK] GSI creation initiated")
    waiter = dynamodb.get_waiter('table_exists')
    waiter.wait(TableName='CostTracking')
    print("  [OK] GSI ready")
except Exception as e:
    if 'ResourceInUseException' in str(e) or 'already exists' in str(e):
        print("  [SKIP] GSI already exists")
    else:
        print(f"  [WARN] Error: {e}")

# Update records
table = dynamodb_resource.Table('CostTracking')

print("\n  Scanning records...")
try:
    response = table.scan()
    items = response.get('Items', [])

    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))

    print(f"  Found {len(items)} records")

    updated = 0
    skipped = 0
    for item in items:
        if 'user_id' in item:
            skipped += 1
            continue

        try:
            table.update_item(
                Key={
                    'date': item['date'],
                    'timestamp': item['timestamp']
                },
                UpdateExpression='SET user_id = :uid',
                ExpressionAttributeValues={':uid': ADMIN_USER_ID}
            )
            updated += 1
            if updated % 50 == 0:
                print(f"    Progress: {updated}/{len(items)}")
        except Exception as e:
            print(f"    [ERROR]: {e}")

    print(f"\n  [OK] CostTracking: Updated {updated}, Skipped {skipped}")
except Exception as e:
    print(f"  [ERROR] {e}")

print("\n[OK] CostTracking migrated")
print()

# ==============================================
# AIPromptConfigs (mark as system templates)
# ==============================================
print("Step 3: Migrating AIPromptConfigs...")
print()

print("  Creating user_id-template_type GSI...")
try:
    # Check if table exists first
    try:
        table_desc = dynamodb.describe_table(TableName='AIPromptConfigs')

        response = dynamodb.update_table(
            TableName='AIPromptConfigs',
            AttributeDefinitions=[
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'template_type', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexUpdates=[
                {
                    'Create': {
                        'IndexName': 'user_id-template_type-index',
                        'KeySchema': [
                            {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                            {'AttributeName': 'template_type', 'KeyType': 'RANGE'}
                        ],
                        'Projection': {'ProjectionType': 'ALL'}
                    }
                }
            ]
        )
        print("  [OK] GSI creation initiated")
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName='AIPromptConfigs')
        print("  [OK] GSI ready")
    except dynamodb.exceptions.ResourceNotFoundException:
        print("  [SKIP] Table AIPromptConfigs does not exist")
except Exception as e:
    if 'ResourceInUseException' in str(e) or 'already exists' in str(e):
        print("  [SKIP] GSI already exists or table updating")
    else:
        print(f"  [WARN] Error: {e}")

# Mark as system templates
try:
    table = dynamodb_resource.Table('AIPromptConfigs')

    print("\n  Scanning records...")
    response = table.scan()
    items = response.get('Items', [])

    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))

    print(f"  Found {len(items)} records")

    updated = 0
    skipped = 0
    for item in items:
        if 'user_id' in item:
            skipped += 1
            continue

        try:
            table.update_item(
                Key={'template_id': item['template_id']},
                UpdateExpression='SET visibility = :vis',
                ExpressionAttributeValues={':vis': 'system'}
            )
            updated += 1
        except Exception as e:
            print(f"    [ERROR]: {e}")

    print(f"\n  [OK] AIPromptConfigs: Marked {updated} as system, Skipped {skipped}")
except Exception as e:
    if 'ResourceNotFoundException' in str(e):
        print("  [SKIP] Table does not exist")
    else:
        print(f"  [ERROR] {e}")

print("\n[OK] AIPromptConfigs migrated")
print()

# Summary
print("=" * 50)
print("[OK] Phase 2 Migration Complete!")
print("=" * 50)
print()
print("All tables migrated:")
print("  - GeneratedContent")
print("  - CostTracking")
print("  - AIPromptConfigs")
print()
