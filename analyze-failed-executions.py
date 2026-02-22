#!/usr/bin/env python3
"""Check failed Step Functions executions"""

import boto3
import json
from datetime import datetime

REGION = 'eu-central-1'

def check_failed_executions():
    """Analyze failed Step Functions executions"""
    sfn_client = boto3.client('stepfunctions', region_name=REGION)
    logs_client = boto3.client('logs', region_name=REGION)

    print("=" * 70)
    print("STEP FUNCTIONS - FAILED EXECUTIONS ANALYSIS")
    print("=" * 70)
    print("")

    # Get ContentGenerator state machine ARN
    response = sfn_client.list_state_machines()
    state_machines = response['stateMachines']

    for sm in state_machines:
        if sm['name'] == 'ContentGenerator':
            arn = sm['stateMachineArn']

            print(f"State Machine: {sm['name']}")
            print(f"ARN: {arn}")
            print("")

            # Get recent executions
            exec_response = sfn_client.list_executions(
                stateMachineArn=arn,
                maxResults=10
            )

            executions = exec_response['executions']

            print(f"Total recent executions: {len(executions)}")
            print("")

            # Analyze each execution
            for ex in executions:
                exec_arn = ex['executionArn']
                name = ex['name']
                status = ex['status']
                start = ex['startDate'].strftime('%Y-%m-%d %H:%M:%S')

                print(f"{'=' * 70}")
                print(f"Execution: {name}")
                print(f"Status: {status}")
                print(f"Started: {start}")

                if 'stopDate' in ex:
                    stop = ex['stopDate'].strftime('%Y-%m-%d %H:%M:%S')
                    duration = (ex['stopDate'] - ex['startDate']).total_seconds()
                    print(f"Stopped: {stop}")
                    print(f"Duration: {duration:.1f} seconds")

                print("")

                # Get execution history for failed executions
                if status == 'FAILED':
                    try:
                        history = sfn_client.get_execution_history(
                            executionArn=exec_arn,
                            maxResults=100,
                            reverseOrder=True  # Get most recent events first
                        )

                        # Find failure event
                        for event in history['events']:
                            event_type = event['type']

                            if event_type == 'ExecutionFailed':
                                details = event.get('executionFailedEventDetails', {})
                                error = details.get('error', 'Unknown')
                                cause = details.get('cause', 'Unknown')

                                print(f"FAILURE DETAILS:")
                                print(f"  Error: {error}")
                                print(f"  Cause: {cause[:500]}...")  # Truncate long messages
                                print("")

                            elif event_type == 'LambdaFunctionFailed':
                                details = event.get('lambdaFunctionFailedEventDetails', {})
                                error = details.get('error', 'Unknown')
                                cause = details.get('cause', 'Unknown')

                                print(f"LAMBDA FAILURE:")
                                print(f"  Error: {error}")
                                print(f"  Cause: {cause[:500]}...")
                                print("")

                            elif event_type == 'TaskFailed':
                                details = event.get('taskFailedEventDetails', {})
                                error = details.get('error', 'Unknown')
                                cause = details.get('cause', 'Unknown')
                                resource = details.get('resource', 'Unknown')

                                print(f"TASK FAILURE:")
                                print(f"  Resource: {resource}")
                                print(f"  Error: {error}")
                                print(f"  Cause: {cause[:500]}...")
                                print("")

                    except Exception as e:
                        print(f"Error getting execution history: {e}")

                elif status == 'SUCCEEDED':
                    # Get input/output for successful execution
                    try:
                        exec_details = sfn_client.describe_execution(
                            executionArn=exec_arn
                        )

                        input_data = json.loads(exec_details.get('input', '{}'))
                        channel_id = input_data.get('channel_id', 'N/A')
                        topic = input_data.get('topic', 'N/A')

                        print(f"SUCCESS DETAILS:")
                        print(f"  Channel: {channel_id}")
                        print(f"  Topic: {topic}")
                        print("")

                    except Exception as e:
                        print(f"Error getting execution details: {e}")

                print("")

if __name__ == '__main__':
    print("")
    print("Failed Executions Analysis - YouTube Content Automation")
    print("Date:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("")

    try:
        check_failed_executions()

        print("=" * 70)
        print("ANALYSIS COMPLETE")
        print("=" * 70)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
