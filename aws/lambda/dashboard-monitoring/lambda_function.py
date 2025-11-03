import json
import boto3
from datetime import datetime, timedelta
from decimal import Decimal

stepfunctions = boto3.client('stepfunctions', region_name='eu-central-1')
logs_client = boto3.client('logs', region_name='eu-central-1')

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def lambda_handler(event, context):
    """
    Dashboard Monitoring API
    Endpoints:
    - GET /monitoring/executions - Step Functions executions
    - GET /monitoring/logs - CloudWatch logs
    """

    print(f"Event: {json.dumps(event, default=str)}")

    # Parse request
    http_method = event.get('httpMethod', 'GET')
    path = event.get('path', '')
    query_params = event.get('queryStringParameters') or {}

    try:
        # Route to handler
        if path.endswith('/monitoring/executions') or path.endswith('/executions'):
            response = handle_executions(query_params)
        elif path.endswith('/monitoring/logs') or path.endswith('/logs'):
            response = handle_logs(query_params)
        else:
            response = {
                'statusCode': 404,
                'body': json.dumps({'error': 'Not found'})
            }

        # Add CORS headers
        response['headers'] = {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'GET,OPTIONS'
        }

        return response

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e),
                'type': 'InternalError'
            })
        }

def handle_executions(params):
    """Get Step Functions executions"""

    # List all state machines
    state_machines_response = stepfunctions.list_state_machines()
    state_machines = state_machines_response.get('stateMachines', [])

    if not state_machines:
        return {
            'statusCode': 200,
            'body': json.dumps({
                'executions': [],
                'stats': {
                    'running': 0,
                    'succeeded': 0,
                    'failed': 0,
                    'avgDuration': '-'
                }
            })
        }

    # Get executions for the first state machine (or you can loop through all)
    all_executions = []
    stats = {'running': 0, 'succeeded': 0, 'failed': 0, 'total_duration': 0, 'completed_count': 0}

    for sm in state_machines[:1]:  # For now, just get first state machine
        sm_arn = sm['stateMachineArn']

        # Get recent executions
        executions_response = stepfunctions.list_executions(
            stateMachineArn=sm_arn,
            maxResults=20
        )

        for exec_item in executions_response.get('executions', []):
            exec_data = {
                'name': exec_item.get('name', 'Unknown'),
                'status': exec_item['status'],
                'startDate': exec_item['startDate'].isoformat(),
                'stopDate': exec_item.get('stopDate', datetime.now()).isoformat() if exec_item.get('stopDate') else None
            }

            all_executions.append(exec_data)

            # Update stats
            if exec_item['status'] == 'RUNNING':
                stats['running'] += 1
            elif exec_item['status'] == 'SUCCEEDED':
                stats['succeeded'] += 1
                # Calculate duration
                if exec_item.get('stopDate'):
                    duration = (exec_item['stopDate'] - exec_item['startDate']).total_seconds()
                    stats['total_duration'] += duration
                    stats['completed_count'] += 1
            elif exec_item['status'] == 'FAILED':
                stats['failed'] += 1

    # Calculate average duration
    avg_duration = '-'
    if stats['completed_count'] > 0:
        avg_minutes = (stats['total_duration'] / stats['completed_count']) / 60
        avg_duration = f"{avg_minutes:.1f}"

    return {
        'statusCode': 200,
        'body': json.dumps({
            'executions': all_executions,
            'stats': {
                'running': stats['running'],
                'succeeded': stats['succeeded'],
                'failed': stats['failed'],
                'avgDuration': avg_duration
            }
        }, default=str)
    }

def handle_logs(params):
    """Get CloudWatch logs"""

    limit = int(params.get('limit', 50))

    # Get log groups for Lambda functions
    log_groups_response = logs_client.describe_log_groups(
        logGroupNamePrefix='/aws/lambda/content-',
        limit=10
    )

    log_groups = log_groups_response.get('logGroups', [])

    if not log_groups:
        return {
            'statusCode': 200,
            'body': json.dumps({'logs': []})
        }

    all_logs = []

    # Get logs from first log group
    for log_group in log_groups[:1]:
        log_group_name = log_group['logGroupName']

        try:
            # Get latest log stream
            streams_response = logs_client.describe_log_streams(
                logGroupName=log_group_name,
                orderBy='LastEventTime',
                descending=True,
                limit=1
            )

            if not streams_response.get('logStreams'):
                continue

            log_stream_name = streams_response['logStreams'][0]['logStreamName']

            # Get log events
            events_response = logs_client.get_log_events(
                logGroupName=log_group_name,
                logStreamName=log_stream_name,
                limit=limit,
                startFromHead=False
            )

            for event in events_response.get('events', []):
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
                all_logs.append({
                    'timestamp': timestamp,
                    'message': event['message'].strip()
                })

        except Exception as e:
            print(f"Error getting logs from {log_group_name}: {str(e)}")
            continue

    # Sort by timestamp descending
    all_logs.sort(key=lambda x: x['timestamp'], reverse=True)

    return {
        'statusCode': 200,
        'body': json.dumps({
            'logs': all_logs[:limit]
        })
    }
