#!/usr/bin/env python3
"""
Cleanup Story Threads Script
Removes threads about non-existent characters from SeriesState
"""

import boto3
import json
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
table = dynamodb.Table('SeriesState')

def get_all_series():
    """Get all series IDs"""
    response = table.scan(ProjectionExpression='series_id')
    return [item['series_id'] for item in response['Items']]

def cleanup_series_threads(series_id, dry_run=True):
    """
    Clean up threads for a specific series

    Args:
        series_id: Series ID to clean
        dry_run: If True, only print what would be removed
    """
    print(f"\n{'-'*60}")
    print(f"Processing series: {series_id}")
    print(f"{'-'*60}")

    # Get series data
    response = table.get_item(Key={'series_id': series_id})
    if 'Item' not in response:
        print(f"[ERROR] Series not found: {series_id}")
        return

    series = response['Item']

    # Extract Bible characters (the "real" characters)
    bible = series.get('bible', {})
    real_characters = set()

    if 'characters' in bible and isinstance(bible['characters'], dict):
        real_characters = set(bible['characters'].keys())
        print(f"[OK] Found {len(real_characters)} real characters in Bible:")
        for char in real_characters:
            print(f"   - {char}")
    else:
        print(f"[WARN] No characters found in Bible")

    # Get threads from plot_threads (correct location!)
    plot_threads = series.get('plot_threads', [])

    if not plot_threads:
        print(f"[INFO] No plot_threads found in series")
        return

    print(f"\n[THREADS] Found {len(plot_threads)} plot_threads")

    # Analyze threads
    clean_threads = []
    removed_threads = []

    for idx, thread in enumerate(plot_threads):
        if not isinstance(thread, dict):
            continue

        thread_desc = thread.get('description', '')
        thread_id = thread.get('thread_id', f'thread_{idx}')
        thread_status = thread.get('status', 'open')

        # Remove if closed
        if thread_status == 'closed':
            removed_threads.append(thread)
            print(f"   [REMOVE] CLOSED: {thread_desc[:60]}...")
            continue

        # Remove if mentions non-existent character
        mentions_real_char = False
        mentions_fake_char = False

        for char in real_characters:
            if char.lower() in thread_desc.lower():
                mentions_real_char = True
                break

        # Check for common fake names (Alexei, Elena, Maya, etc.)
        fake_names = ['alexei', 'elena', 'maya', 'ivan', 'dmitri', 'viktor']
        for fake in fake_names:
            if fake in thread_desc.lower() and fake not in [c.lower() for c in real_characters]:
                mentions_fake_char = True
                break

        if mentions_fake_char:
            removed_threads.append(thread)
            print(f"   [REMOVE] FAKE CHAR: {thread_desc[:60]}...")
        elif not mentions_real_char and real_characters:
            removed_threads.append(thread)
            print(f"   [REMOVE] NO REAL CHAR: {thread_desc[:60]}...")
        else:
            # Keep thread
            clean_threads.append(thread)
            print(f"   [KEEP] {thread_desc[:60]}...")

    # Summary
    print(f"\n[SUMMARY]")
    print(f"   Threads before: {len(plot_threads)}")
    print(f"   Threads after:  {len(clean_threads)}")
    print(f"   Removed:        {len(removed_threads)}")

    # Update database (if not dry run)
    if not dry_run and removed_threads:
        print(f"\n[UPDATE] Writing to database...")

        table.update_item(
            Key={'series_id': series_id},
            UpdateExpression='SET plot_threads = :t, last_cleanup = :now',
            ExpressionAttributeValues={
                ':t': clean_threads,
                ':now': datetime.utcnow().isoformat() + 'Z'
            }
        )

        print(f"[OK] Database updated")
    elif dry_run:
        print(f"\n[DRY RUN] No changes made to database")
        print(f"Run with --apply to make actual changes")

def main():
    import sys

    dry_run = '--apply' not in sys.argv

    if dry_run:
        print("[DRY RUN] No changes will be made")
        print("Run with --apply flag to make actual changes\n")
    else:
        print("[APPLY MODE] Changes will be written to database\n")

    # Get all series
    series_list = get_all_series()
    print(f"Found {len(series_list)} series:")
    for sid in series_list:
        print(f"  - {sid}")

    # Process each series
    for series_id in series_list:
        cleanup_series_threads(series_id, dry_run=dry_run)

    print(f"\n{'-'*60}")
    print(f"[COMPLETE] Cleanup finished")
    print(f"{'-'*60}\n")

if __name__ == '__main__':
    main()
