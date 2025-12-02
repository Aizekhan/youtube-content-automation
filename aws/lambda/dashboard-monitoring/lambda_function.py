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


def safe_json_parse(json_str):
    try:
        data = json.loads(json_str)
        if isinstance(data, dict) and 'Payload' in data:
            return data['Payload']
        return data
    except:
        return {'raw': json_str}


def find_matching_entered_state(state_stack, current_event_id, target_type, event_lookup):
    for eid in reversed(sorted([k for k in state_stack.keys() if k < current_event_id])):
        if event_lookup.get(eid, {}).get('type') == target_type:
            return eid
    return None


def lambda_handler(event, context):
    """
    Dashboard Monitoring API - Multi-Tenant Version

    NOTE: Step Functions filtering by user_id requires additional logic:
    - Need to fetch execution input/output and check channel_id ownership
    - This is implemented as basic extraction for now
    - TODO: Add full execution filtering by user's channels
    """
    print(f"Event: {json.dumps(event, default=str)}")

    # Extract user_id for multi-tenant data isolation
    user_id = event.get('user_id')
    if not user_id:
        print("WARNING: No user_id provided")
        # For backward compatibility during migration
        raise ValueError('SECURITY ERROR: user_id is required for all requests')
        

    http_method = event.get('httpMethod', 'GET')
    path = event.get('path', '')
    query_params = event.get('queryStringParameters') or {}

    # Add user_id to params for downstream functions
    query_params['user_id'] = user_id

    try:
        if path.endswith('/monitoring/executions') or path.endswith('/executions'):
            response = handle_executions(query_params)
        elif path.endswith('/monitoring/execution-details') or path.endswith('/execution-details'):
            response = handle_execution_details(query_params)
        elif path.endswith('/monitoring/logs') or path.endswith('/logs'):
            response = handle_logs(query_params)
        else:
            response = {'statusCode': 404, 'body': json.dumps({'error': 'Not found'})}

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
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'error': str(e), 'type': 'InternalError'})
        }


def handle_execution_details(params):
    execution_arn = params.get('executionArn')
    if not execution_arn:
        return {'statusCode': 400, 'body': json.dumps({'error': 'executionArn parameter is required'})}

    try:
        all_events = []
        next_token = None

        while True:
            if next_token:
                history_response = stepfunctions.get_execution_history(
                    executionArn=execution_arn, maxResults=1000, reverseOrder=False, nextToken=next_token)
            else:
                history_response = stepfunctions.get_execution_history(
                    executionArn=execution_arn, maxResults=1000, reverseOrder=False)

            all_events.extend(history_response.get('events', []))
            next_token = history_response.get('nextToken')
            if not next_token:
                break

        print(f"Total events: {len(all_events)}")

        event_lookup = {e['id']: e for e in all_events}
        steps = []
        state_stack = {}

        for event in all_events:
            event_type = event['type']
            event_id = event['id']
            timestamp = event['timestamp'].isoformat()

            if event_type == 'TaskStateEntered':
                details = event.get('stateEnteredEventDetails', {})
                state_stack[event_id] = {
                    'name': details.get('name', 'Unknown'),
                    'type': 'Task',
                    'status': 'running',
                    'startTime': timestamp,
                    'input': safe_json_parse(details.get('input', '{}'))
                }

            elif event_type == 'TaskSucceeded':
                details = event.get('taskSucceededEventDetails', {})
                enter_id = find_matching_entered_state(state_stack, event_id, 'TaskStateEntered', event_lookup)
                if enter_id:
                    state = state_stack[enter_id]
                    state['status'] = 'succeeded'
                    state['endTime'] = timestamp
                    state['output'] = safe_json_parse(details.get('output', '{}'))
                    steps.append(state.copy())

            elif event_type == 'TaskFailed':
                details = event.get('taskFailedEventDetails', {})
                enter_id = find_matching_entered_state(state_stack, event_id, 'TaskStateEntered', event_lookup)
                if enter_id:
                    state = state_stack[enter_id]
                    state['status'] = 'failed'
                    state['endTime'] = timestamp
                    state['error'] = details.get('error', 'Unknown')
                    state['cause'] = details.get('cause', '')
                    steps.append(state.copy())

            elif event_type == 'MapStateEntered':
                details = event.get('stateEnteredEventDetails', {})
                state_stack[event_id] = {
                    'name': details.get('name', 'Unknown'),
                    'type': 'Map',
                    'status': 'running',
                    'startTime': timestamp,
                    'input': safe_json_parse(details.get('input', '{}'))
                }

            elif event_type == 'MapStateSucceeded':
                details = event.get('stateExitedEventDetails', {})
                enter_id = find_matching_entered_state(state_stack, event_id, 'MapStateEntered', event_lookup)
                if enter_id:
                    state = state_stack[enter_id]
                    state['status'] = 'succeeded'
                    state['endTime'] = timestamp
                    state['output'] = safe_json_parse(details.get('output', '{}'))
                    steps.append(state.copy())

            elif event_type == 'MapStateFailed':
                details = event.get('stateExitedEventDetails', {})
                enter_id = find_matching_entered_state(state_stack, event_id, 'MapStateEntered', event_lookup)
                if enter_id:
                    state = state_stack[enter_id]
                    state['status'] = 'failed'
                    state['endTime'] = timestamp
                    state['error'] = details.get('error', 'Map failed')
                    steps.append(state.copy())

            elif event_type == 'ChoiceStateEntered':
                details = event.get('stateEnteredEventDetails', {})
                steps.append({
                    'name': details.get('name', 'Unknown'),
                    'type': 'Choice',
                    'status': 'completed',
                    'startTime': timestamp,
                    'endTime': timestamp,
                    'input': safe_json_parse(details.get('input', '{}'))
                })

            elif event_type == 'PassStateEntered':
                details = event.get('stateEnteredEventDetails', {})
                input_data = safe_json_parse(details.get('input', '{}'))
                steps.append({
                    'name': details.get('name', 'Unknown'),
                    'type': 'Pass',
                    'status': 'completed',
                    'startTime': timestamp,
                    'endTime': timestamp,
                    'input': input_data,
                    'output': input_data
                })

        print(f"Parsed {len(steps)} steps")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'executionArn': execution_arn,
                'steps': steps,
                'totalEvents': len(all_events),
                'totalSteps': len(steps)
            }, default=str)
        }

    except Exception as e:
        print(f"Error getting execution details: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'statusCode': 500, 'body': json.dumps({'error': str(e), 'type': 'ExecutionDetailsError'})}


def handle_executions(params):
    state_machines_response = stepfunctions.list_state_machines()
    state_machines = state_machines_response.get('stateMachines', [])

    if not state_machines:
        return {
            'statusCode': 200,
            'body': json.dumps({
                'executions': [],
                'stats': {'running': 0, 'succeeded': 0, 'failed': 0, 'avgDuration': '-'}
            })
        }

    all_executions = []
    stats = {'running': 0, 'succeeded': 0, 'failed': 0, 'total_duration': 0, 'completed_count': 0}

    for sm in state_machines[:1]:
        sm_arn = sm['stateMachineArn']
        executions_response = stepfunctions.list_executions(stateMachineArn=sm_arn, maxResults=20)

        for exec_item in executions_response.get('executions', []):
            exec_data = {
                'name': exec_item.get('name', 'Unknown'),
                'executionArn': exec_item.get('executionArn', ''),
                'status': exec_item['status'],
                'startDate': exec_item['startDate'].isoformat(),
                'stopDate': exec_item.get('stopDate', datetime.now()).isoformat() if exec_item.get('stopDate') else None
            }

            all_executions.append(exec_data)

            if exec_item['status'] == 'RUNNING':
                stats['running'] += 1
            elif exec_item['status'] == 'SUCCEEDED':
                stats['succeeded'] += 1
                if exec_item.get('stopDate'):
                    duration = (exec_item['stopDate'] - exec_item['startDate']).total_seconds()
                    stats['total_duration'] += duration
                    stats['completed_count'] += 1
            elif exec_item['status'] == 'FAILED':
                stats['failed'] += 1

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
    limit = int(params.get('limit', 50))

    log_groups_response = logs_client.describe_log_groups(logGroupNamePrefix='/aws/lambda/content-', limit=10)
    log_groups = log_groups_response.get('logGroups', [])

    if not log_groups:
        return {'statusCode': 200, 'body': json.dumps({'logs': []})}

    all_logs = []

    for log_group in log_groups[:1]:
        log_group_name = log_group['logGroupName']

        try:
            streams_response = logs_client.describe_log_streams(
                logGroupName=log_group_name, orderBy='LastEventTime', descending=True, limit=1)

            if not streams_response.get('logStreams'):
                continue

            log_stream_name = streams_response['logStreams'][0]['logStreamName']

            events_response = logs_client.get_log_events(
                logGroupName=log_group_name, logStreamName=log_stream_name, limit=limit, startFromHead=False)

            for event in events_response.get('events', []):
                timestamp = datetime.fromtimestamp(event['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
                all_logs.append({'timestamp': timestamp, 'message': event['message'].strip()})

        except Exception as e:
            print(f"Error getting logs from {log_group_name}: {str(e)}")
            continue

    all_logs.sort(key=lambda x: x['timestamp'], reverse=True)

    return {'statusCode': 200, 'body': json.dumps({'logs': all_logs[:limit]})}
