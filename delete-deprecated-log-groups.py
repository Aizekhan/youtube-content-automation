#!/usr/bin/env python3
"""Delete CloudWatch log groups for deprecated Lambda functions"""

import boto3
from botocore.exceptions import ClientError

REGION = 'eu-central-1'

DEPRECATED_LOG_GROUPS = [
    "/aws/lambda/content-cta-audio",
    "/aws/lambda/ssml-generator",
    "/aws/lambda/merge-image-batches",
    "/aws/lambda/prepare-image-batches",
    "/aws/lambda/save-phase1-to-s3",
    "/aws/lambda/load-phase1-from-s3",
    "/aws/lambda/queue-failed-ec2",
    "/aws/lambda/retry-ec2-queue",
    "/aws/lambda/content-audio-tts",
    "/aws/lambda/content-audio-polly",
    "/aws/lambda/content-theme-agent",
    "/aws/lambda/prompts-api",
    "/aws/lambda/ec2-sd35-control",
]

def delete_log_groups():
    """Delete deprecated CloudWatch log groups"""

    logs_client = boto3.client('logs', region_name=REGION)

    print("Deleting CloudWatch log groups for deprecated Lambda functions...")
    print("")

    deleted = 0
    not_found = 0
    failed = 0

    for log_group in DEPRECATED_LOG_GROUPS:
        print(f"Checking: {log_group}")

        try:
            # Check if log group exists
            logs_client.describe_log_groups(logGroupNamePrefix=log_group)

            # Delete log group
            logs_client.delete_log_group(logGroupName=log_group)
            print(f"  Deleted")
            deleted += 1

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                print(f"  Does not exist")
                not_found += 1
            else:
                print(f"  Failed: {e}")
                failed += 1

    print("")
    print("=== Summary ===")
    print(f"Deleted: {deleted} log groups")
    print(f"Not found: {not_found} log groups")
    if failed > 0:
        print(f"Failed: {failed} log groups")
    print("")

if __name__ == '__main__':
    delete_log_groups()
