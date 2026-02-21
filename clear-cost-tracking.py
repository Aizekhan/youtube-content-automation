#!/usr/bin/env python3
"""Clear all items from CostTracking table"""

import boto3
from botocore.exceptions import ClientError

REGION = 'eu-central-1'
TABLE_NAME = 'CostTracking'

def clear_table():
    """Scan and delete all items from CostTracking table"""

    dynamodb = boto3.resource('dynamodb', region_name=REGION)
    table = dynamodb.Table(TABLE_NAME)

    print(f"Clearing {TABLE_NAME} table...")
    print("")

    # Scan table
    response = table.scan()
    items = response.get('Items', [])

    # Handle pagination
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))

    print(f"Found {len(items)} items to delete")
    print("")

    # Delete items in batches
    deleted = 0
    with table.batch_writer() as batch:
        for item in items:
            batch.delete_item(
                Key={
                    'date': item['date'],
                    'timestamp': item['timestamp']
                }
            )
            deleted += 1
            if deleted % 50 == 0:
                print(f"Deleted {deleted}/{len(items)} items...")

    print("")
    print(f"✓ Successfully deleted {deleted} items")
    print("")

    # Verify
    response = table.scan(Select='COUNT')
    remaining = response.get('Count', 0)

    if remaining == 0:
        print("✓ CostTracking table is now empty!")
    else:
        print(f"⚠️  Warning: {remaining} items still remain")

    return deleted

if __name__ == '__main__':
    try:
        deleted_count = clear_table()
    except ClientError as e:
        print(f"Error: {e}")
        exit(1)
