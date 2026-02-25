#!/usr/bin/env python3
"""
Create 10 episodes for Mask of Gods series in ContentTopicsQueue
"""
import boto3
import uuid
from datetime import datetime

dynamodb = boto3.client('dynamodb', region_name='eu-central-1')

channel_id = "UCwohlVtx4LVoo4qfrTIb6jw"
series_id = "mask-of-gods-s1"
series_title = "Mask of Gods: The Truth Behind the Divine"

# Episode topics - psychological/philosophical themes
episode_topics = [
    "The nature of belief and how it shapes reality",
    "Self-deception as a survival mechanism",
    "The masks we wear to hide our true selves",
    "When comfort becomes a prison",
    "The fear of facing uncomfortable truths",
    "How we rationalize away cognitive dissonance",
    "The mirror effect - seeing ourselves in others",
    "The moment everything clicks into place",
    "Integration of shadow and light",
    "Living authentically after awakening"
]

print(f"Creating 10 episodes for series: {series_title}")
print(f"Channel: {channel_id}")
print(f"Series ID: {series_id}\n")

for ep_num in range(1, 11):
    topic_id = f"mask-of-gods-ep{ep_num}-{int(datetime.now().timestamp())}"
    topic_text = episode_topics[ep_num - 1]

    item = {
        'topic_id': {'S': topic_id},
        'channel_id': {'S': channel_id},
        'topic': {'S': topic_text},
        'created_at': {'S': datetime.now().isoformat()},
        'priority': {'N': '5'},
        'status': {'S': 'pending'},
        'series_metadata': {
            'M': {
                'series_id': {'S': series_id},
                'series_title': {'S': series_title},
                'episode_number': {'N': str(ep_num)},
                'total_episodes': {'N': '10'}
            }
        }
    }

    dynamodb.put_item(TableName='ContentTopicsQueue', Item=item)
    print(f"Episode {ep_num}/10: {topic_text[:50]}...")

print("\nAll episodes created successfully!")
print("Ready to generate Episode 1")
