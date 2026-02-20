#!/usr/bin/env python3
"""
Cleanup Script - Delete ALL records from GeneratedContent table
Date: 2026-02-20
Backup: backups/20260220_cleanup/
"""

import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
table = dynamodb.Table('GeneratedContent')

def delete_all_items():
    """Delete all items from GeneratedContent table"""
    print("[DELETE] Starting cleanup of GeneratedContent table...")

    # Scan all items
    response = table.scan(
        ProjectionExpression='channel_id, created_at'  # Only get keys
    )

    items = response['Items']
    total_count = len(items)
    deleted_count = 0

    print(f"[INFO] Found {total_count} items to delete")

    # Delete items in batches
    with table.batch_writer() as batch:
        for item in items:
            batch.delete_item(
                Key={
                    'channel_id': item['channel_id'],
                    'created_at': item['created_at']
                }
            )
            deleted_count += 1

            if deleted_count % 50 == 0:
                print(f"   Deleted {deleted_count}/{total_count} items...")

    # Handle pagination if more than 1MB
    while 'LastEvaluatedKey' in response:
        response = table.scan(
            ProjectionExpression='channel_id, created_at',
            ExclusiveStartKey=response['LastEvaluatedKey']
        )

        items = response['Items']

        with table.batch_writer() as batch:
            for item in items:
                batch.delete_item(
                    Key={
                        'channel_id': item['channel_id'],
                        'created_at': item['created_at']
                    }
                )
                deleted_count += 1

                if deleted_count % 50 == 0:
                    print(f"   Deleted {deleted_count} items...")

    print(f"[SUCCESS] Deleted {deleted_count} items from GeneratedContent")
    return deleted_count

if __name__ == '__main__':
    try:
        deleted = delete_all_items()
        print(f"\n[SUCCESS] Deleted {deleted} items from GeneratedContent table")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
