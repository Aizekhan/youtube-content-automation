#!/usr/bin/env python3
"""
Start Episode 3 generation for mask-of-gods-s1
"""

import boto3
import json
from datetime import datetime

stepfunctions = boto3.client('stepfunctions', region_name='eu-central-1')
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')

# Get Episode 3 topic from ContentTopicsQueue
topics_table = dynamodb.Table('ContentTopicsQueue')

print("=" * 80)
print("Starting Episode 3 Generation - mask-of-gods-s1")
print("=" * 80)
print()

# Find Episode 3 topic
print("1. Fetching Episode 3 topic from DynamoDB...")
response = topics_table.scan(
    FilterExpression='series_id = :sid AND episode_number = :ep',
    ExpressionAttributeValues={
        ':sid': 'mask-of-gods-s1',
        ':ep': 3
    }
)

if not response.get('Items'):
    print("[ERROR] Episode 3 topic not found!")
    exit(1)

topic_item = response['Items'][0]
topic_id = topic_item['topic_id']
channel_id = topic_item['channel_id']
topic_text = topic_item.get('topic', topic_item.get('topic_text', ''))

print(f"  Channel ID: {channel_id}")
print(f"  Topic ID: {topic_id}")
print(f"  Topic: {topic_text[:80]}...")
print()

# Create Step Functions execution input
print("2. Creating Step Functions execution...")

execution_name = f"mask-of-gods-ep3-{int(datetime.utcnow().timestamp())}"

execution_input = {
    "user_id": "c334d862-4031-7097-4207-84856b59d3ed",
    "channel_id": channel_id,
    "topic_id": topic_id,
    "generate_immediately": True
}

state_machine_arn = "arn:aws:states:eu-central-1:599297130956:stateMachine:ContentGenerator"

try:
    response = stepfunctions.start_execution(
        stateMachineArn=state_machine_arn,
        name=execution_name,
        input=json.dumps(execution_input)
    )

    execution_arn = response['executionArn']

    print(f"[OK] Execution started: {execution_name}")
    print(f"  ARN: {execution_arn}")
    print()
    print("=" * 80)
    print("EPISODE 3 STARTED")
    print("=" * 80)
    print()
    print("Monitor progress:")
    print(f"  aws stepfunctions describe-execution --execution-arn '{execution_arn}' --region eu-central-1")
    print()

except Exception as e:
    print(f"[ERROR] Failed to start execution: {e}")
    exit(1)
