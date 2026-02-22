#!/usr/bin/env python3
"""Check YouTube Content Automation System Status"""

import boto3
from datetime import datetime, timedelta
import json

REGION = 'eu-central-1'

def check_lambda_functions():
    """Check Lambda functions status"""
    lambda_client = boto3.client('lambda', region_name=REGION)

    print("=" * 60)
    print("LAMBDA FUNCTIONS")
    print("=" * 60)

    response = lambda_client.list_functions()
    functions = response['Functions']

    print(f"Total functions: {len(functions)}")
    print("")

    # Group by category
    categories = {
        'content': [],
        'dashboard': [],
        'topics': [],
        'ec2': [],
        'infrastructure': [],
        'other': []
    }

    for func in functions:
        name = func['FunctionName']
        if name.startswith('content-'):
            categories['content'].append(name)
        elif name.startswith('dashboard-'):
            categories['dashboard'].append(name)
        elif 'topics' in name:
            categories['topics'].append(name)
        elif name.startswith('ec2-'):
            categories['ec2'].append(name)
        elif name in ['aws-costs-fetcher', 'backfill-costs', 'telegram-error-notifier',
                      'schema-validator', 'log-execution-error']:
            categories['infrastructure'].append(name)
        else:
            categories['other'].append(name)

    for category, funcs in categories.items():
        if funcs:
            print(f"{category.upper()}: {len(funcs)} functions")
            for f in sorted(funcs)[:5]:
                print(f"  - {f}")
            if len(funcs) > 5:
                print(f"  ... and {len(funcs) - 5} more")
            print("")

def check_ec2_instances():
    """Check EC2 instances status"""
    ec2_client = boto3.client('ec2', region_name=REGION)

    print("=" * 60)
    print("EC2 INSTANCES")
    print("=" * 60)

    response = ec2_client.describe_instances()

    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            state = instance['State']['Name']
            instance_type = instance['InstanceType']

            name = 'N/A'
            for tag in instance.get('Tags', []):
                if tag['Key'] == 'Name':
                    name = tag['Value']

            status_icon = "Running" if state == 'running' else "Stopped"
            print(f"{status_icon}: {name} ({instance_type}) - {instance_id}")

    print("")

def check_dynamodb_tables():
    """Check DynamoDB tables status"""
    dynamodb = boto3.client('dynamodb', region_name=REGION)

    print("=" * 60)
    print("DYNAMODB TABLES")
    print("=" * 60)

    response = dynamodb.list_tables()
    tables = response['TableNames']

    print(f"Total tables: {len(tables)}")
    print("")

    # Check key tables
    key_tables = ['GeneratedContent', 'ContentTopicsQueue', 'ChannelConfigs',
                  'CostTracking', 'SystemSettings']

    for table_name in key_tables:
        if table_name in tables:
            desc = dynamodb.describe_table(TableName=table_name)
            item_count = desc['Table'].get('ItemCount', 0)
            size_bytes = desc['Table'].get('TableSizeBytes', 0)
            size_kb = size_bytes / 1024

            print(f"{table_name}:")
            print(f"  Items: {item_count}")
            print(f"  Size: {size_kb:.1f} KB")
            print("")

def check_step_functions():
    """Check Step Functions status"""
    sfn_client = boto3.client('stepfunctions', region_name=REGION)

    print("=" * 60)
    print("STEP FUNCTIONS")
    print("=" * 60)

    response = sfn_client.list_state_machines()
    state_machines = response['stateMachines']

    print(f"Total state machines: {len(state_machines)}")
    print("")

    for sm in state_machines:
        name = sm['name']
        arn = sm['stateMachineArn']

        print(f"{name}:")

        # Get recent executions
        try:
            exec_response = sfn_client.list_executions(
                stateMachineArn=arn,
                maxResults=5
            )

            executions = exec_response['executions']

            if executions:
                print(f"  Recent executions: {len(executions)}")
                for ex in executions[:3]:
                    status = ex['status']
                    start = ex['startDate'].strftime('%Y-%m-%d %H:%M')
                    print(f"    {status}: {start}")
            else:
                print("  No recent executions")
        except Exception as e:
            print(f"  Error getting executions: {e}")

        print("")

def check_cloudwatch_logs():
    """Check CloudWatch logs"""
    logs_client = boto3.client('logs', region_name=REGION)

    print("=" * 60)
    print("CLOUDWATCH LOGS")
    print("=" * 60)

    response = logs_client.describe_log_groups(
        logGroupNamePrefix='/aws/lambda/'
    )

    log_groups = response['logGroups']
    total_size = sum(lg.get('storedBytes', 0) for lg in log_groups)
    total_mb = total_size / 1024 / 1024

    print(f"Lambda log groups: {len(log_groups)}")
    print(f"Total size: {total_mb:.1f} MB")
    print("")

if __name__ == '__main__':
    print("")
    print("YouTube Content Automation - System Status Check")
    print("Date:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("")

    try:
        check_lambda_functions()
        check_ec2_instances()
        check_dynamodb_tables()
        check_step_functions()
        check_cloudwatch_logs()

        print("=" * 60)
        print("STATUS CHECK COMPLETE")
        print("=" * 60)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
