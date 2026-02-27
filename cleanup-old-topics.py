#!/usr/bin/env python3
"""
Cleanup old/test topics from ContentTopicsQueue
Keep only mask-of-gods-s1 series topics
"""

import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
table = dynamodb.Table('ContentTopicsQueue')

def cleanup_topics():
    print("=" * 80)
    print("CLEANUP OLD TOPICS")
    print("=" * 80)

    # Scan all topics
    result = table.scan()
    items = result['Items']

    print(f"\nFound {len(items)} total topics")

    # Categorize topics
    keep_topics = []
    delete_topics = []

    for item in items:
        topic_id = item.get('topic_id', '')
        series_id = item.get('series_id', '')
        status = item.get('status', '')
        channel_id = item.get('channel_id', '')

        # Keep mask-of-gods-s1 topics that are queued or draft
        if series_id == 'mask-of-gods-s1' and status in ['queued', 'draft']:
            keep_topics.append(item)
        # Also keep done topics for reference
        elif series_id == 'mask-of-gods-s1' and status == 'done':
            keep_topics.append(item)
        # Delete everything else
        else:
            delete_topics.append(item)

    print(f"\nTopics to KEEP: {len(keep_topics)}")
    print(f"Topics to DELETE: {len(delete_topics)}\n")

    # Show what will be deleted
    print("Will DELETE:")
    for item in delete_topics[:20]:  # Show first 20
        topic_id = item.get('topic_id', '')[:40]
        series_id = item.get('series_id', 'no-series')
        status = item.get('status', '')
        print(f"  {status:10} | {series_id:25} | {topic_id}")

    if len(delete_topics) > 20:
        print(f"  ... and {len(delete_topics) - 20} more")

    # Confirmation
    print(f"\n{'='*80}")
    response = input(f"Delete {len(delete_topics)} topics? (yes/no): ")
    if response.lower() != 'yes':
        print("Cancelled")
        return

    # Delete topics by setting status to 'deleted'
    print(f"\n{'='*80}")
    print("Deleting topics...\n")

    deleted_count = 0
    for item in delete_topics:
        try:
            # Hard delete from DynamoDB
            table.delete_item(
                Key={
                    'channel_id': item['channel_id'],
                    'topic_id': item['topic_id']
                }
            )
            topic_preview = item['topic_id'][:30]
            series = item.get('series_id', 'no-series')[:20]
            print(f"[DELETED] {series:20} | {topic_preview}")
            deleted_count += 1
        except Exception as e:
            print(f"[ERROR] {item['topic_id']}: {e}")

    print(f"\n{'='*80}")
    print(f"COMPLETED:")
    print(f"  Deleted: {deleted_count}")
    print(f"  Kept:    {len(keep_topics)}")
    print(f"  Total:   {len(items)}")

    # Show remaining topics
    print(f"\n{'='*80}")
    print("REMAINING TOPICS (mask-of-gods-s1 only):")

    result_after = table.scan(
        FilterExpression='series_id = :sid',
        ExpressionAttributeValues={':sid': 'mask-of-gods-s1'}
    )

    remaining = result_after['Items']
    for item in sorted(remaining, key=lambda x: x.get('topic_id', '')):
        topic_id = item.get('topic_id', '')[:40]
        status = item.get('status', '')
        topic_text = item.get('topic_text', '')[:50]
        print(f"  {status:10} | {topic_id:40} | {topic_text}")

    print(f"\nTotal remaining: {len(remaining)}")

if __name__ == '__main__':
    cleanup_topics()
