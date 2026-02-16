"""
Lambda: log-execution-error
Logs critical Step Functions execution errors to DynamoDB for monitoring
"""

import json
import boto3
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('ExecutionErrors')  # Create this table if needed


def lambda_handler(event, context):
    """
    Log execution error to DynamoDB

    Input:
    {
        "error": {...},
        "timestamp": "2026-02-13T16:00:00Z",
        "state": "StateName",
        "execution": "execution-name",
        "context": {...}
    }
    """

    try:
        # Extract error info
        error_info = event.get('error', {})
        timestamp = event.get('timestamp', datetime.utcnow().isoformat())
        state_name = event.get('state', 'Unknown')
        execution_name = event.get('execution', 'Unknown')

        # Prepare item for DynamoDB
        error_item = {
            'executionName': execution_name,
            'timestamp': timestamp,
            'stateName': state_name,
            'errorType': error_info.get('Error', 'UnknownError'),
            'errorCause': error_info.get('Cause', 'No cause provided'),
            'context': json.dumps(event.get('context', {}), default=str)
        }

        # Log to CloudWatch
        print(f"CRITICAL ERROR in execution: {execution_name}")
        print(f"State: {state_name}")
        print(f"Error: {error_info.get('Error', 'Unknown')}")
        print(f"Cause: {error_info.get('Cause', 'No cause')}")

        # Save to DynamoDB (if table exists)
        try:
            table.put_item(Item=error_item)
            print(f"Error logged to DynamoDB: ExecutionErrors table")
        except Exception as e:
            print(f"Warning: Could not save to DynamoDB: {str(e)}")
            print("Error logged to CloudWatch only")

        return {
            'statusCode': 200,
            'logged': True,
            'executionName': execution_name,
            'timestamp': timestamp
        }

    except Exception as e:
        print(f"ERROR in log-execution-error Lambda: {str(e)}")
        # Don't fail - just log and continue
        return {
            'statusCode': 500,
            'logged': False,
            'error': str(e)
        }
