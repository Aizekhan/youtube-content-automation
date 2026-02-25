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


def cors_response(status_code, body):
    """Helper to ensure CORS headers on ALL responses"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            'Access-Control-Allow-Methods': 'GET,OPTIONS'
        },
        'body': json.dumps(body, default=str) if isinstance(body, (dict, list)) else body
    }


def extract_user_id(event):
    """
    Extract user_id from multiple sources (flexible for different auth setups)

    Priority:
    1. Cognito Authorizer claims (when API Gateway Authorizer is configured)
    2. Query parameters (temporary fallback)
    3. Default DEBUG_USER (permissive mode for development)
    """
    # Try Cognito Authorizer claims (proper way)
    if 'requestContext' in event:
        authorizer = event['requestContext'].get('authorizer', {})
        claims = authorizer.get('claims', {})
        if claims and 'sub' in claims:
            return claims['sub']

    # Fallback: Query parameters (for now, until Authorizer is configured)
    query_params = event.get('queryStringParameters') or {}
    if 'user_id' in query_params:
        return query_params['user_id']

    # Default: Permissive mode (single-user system)
    print("WARNING: No user_id found - using DEBUG_USER (permissive mode)")
    return 'DEBUG_USER'


def lambda_handler(event, context):
    """
    Dashboard Monitoring API

    Features:
    - Dynamic Lambda discovery from Step Function
    - Dynamic state tracking for ANY state type
    - Flexible authentication (Cognito, query params, or permissive)
    - Automatic CORS handling
    """
    # Handle OPTIONS (CORS preflight)
    if event.get('httpMethod') == 'OPTIONS':
        return cors_response(200, {})

    user_id = extract_user_id(event)
    http_method = event.get('httpMethod') or event.get('requestContext', {}).get('http', {}).get('method', 'GET')
    # Support both API Gateway (path) and Function URL (rawPath)
    path = event.get('path') or event.get('rawPath', '')
    query_params = event.get('queryStringParameters') or {}
    query_params['user_id'] = user_id

    try:
        if path.endswith('/monitoring/executions') or path.endswith('/executions'):
            return handle_executions(query_params)
        elif path.endswith('/monitoring/execution-details') or path.endswith('/execution-details'):
            return handle_execution_details(query_params)
        elif path.endswith('/monitoring/logs') or path.endswith('/logs'):
            return handle_logs(query_params)
        else:
            return cors_response(404, {'error': 'Not found'})

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return cors_response(500, {'error': str(e), 'type': 'InternalError'})


def handle_execution_details(params):
    execution_arn = params.get('executionArn')
    if not execution_arn:
        return cors_response(400, {'error': 'executionArn parameter is required'})

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

        # ARCHITECTURAL FIX: Dynamic state tracking for ANY Step Functions state type
        # Maps event types to their state types automatically
        STATE_TYPE_MAP = {
            'TaskStateEntered': 'Task',
            'MapStateEntered': 'Map',
            'ParallelStateEntered': 'Parallel',  # Auto-detect Parallel states
            'ChoiceStateEntered': 'Choice',
            'PassStateEntered': 'Pass',
            'WaitStateEntered': 'Wait',
            'SucceedStateEntered': 'Succeed',
            'FailStateEntered': 'Fail'
        }

        for event in all_events:
            event_type = event['type']
            event_id = event['id']
            timestamp = event['timestamp'].isoformat()

            # Generic StateEntered handler - works for ANY state type
            if event_type.endswith('StateEntered'):
                details = event.get('stateEnteredEventDetails', {})
                state_type = STATE_TYPE_MAP.get(event_type, event_type.replace('StateEntered', ''))

                state_stack[event_id] = {
                    'name': details.get('name', 'Unknown'),
                    'type': state_type,
                    'status': 'running',
                    'startTime': timestamp,
                    'input': safe_json_parse(details.get('input', '{}'))
                }

                # Instant-complete states (Choice, Pass, etc.)
                if state_type in ['Choice', 'Pass']:
                    state = state_stack[event_id]
                    state['status'] = 'completed'
                    state['endTime'] = timestamp
                    if state_type == 'Pass':
                        state['output'] = state['input']
                    steps.append(state.copy())

            # Generic success handler - works for ANY state type
            elif event_type.endswith('Succeeded') or event_type.endswith('StateSucceeded'):
                details = event.get('taskSucceededEventDetails') or event.get('stateExitedEventDetails', {})
                # Find matching entered event
                enter_event_type = event_type.replace('Succeeded', 'Entered').replace('StateSucceeded', 'StateEntered')
                enter_id = find_matching_entered_state(state_stack, event_id, enter_event_type, event_lookup)

                if enter_id:
                    state = state_stack[enter_id]
                    state['status'] = 'succeeded'
                    state['endTime'] = timestamp
                    state['output'] = safe_json_parse(details.get('output', '{}'))
                    steps.append(state.copy())

            # Generic failure handler - works for ANY state type
            elif event_type.endswith('Failed') or event_type.endswith('StateFailed'):
                details = event.get('taskFailedEventDetails') or event.get('stateExitedEventDetails', {})
                enter_event_type = event_type.replace('Failed', 'Entered').replace('StateFailed', 'StateEntered')
                enter_id = find_matching_entered_state(state_stack, event_id, enter_event_type, event_lookup)

                if enter_id:
                    state = state_stack[enter_id]
                    state['status'] = 'failed'
                    state['endTime'] = timestamp
                    state['error'] = details.get('error', 'Unknown')
                    state['cause'] = details.get('cause', '')
                    steps.append(state.copy())

        print(f"Parsed {len(steps)} steps")

        return cors_response(200, {
            'executionArn': execution_arn,
            'steps': steps,
            'totalEvents': len(all_events),
            'totalSteps': len(steps)
        })

    except Exception as e:
        print(f"Error getting execution details: {str(e)}")
        import traceback
        traceback.print_exc()
        return cors_response(500, {'error': str(e), 'type': 'ExecutionDetailsError'})


def handle_executions(params):
    state_machines_response = stepfunctions.list_state_machines()
    state_machines = state_machines_response.get('stateMachines', [])

    if not state_machines:
        return cors_response(200, {
            'executions': [],
            'stats': {'running': 0, 'succeeded': 0, 'failed': 0, 'avgDuration': '-'}
        })

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

    return cors_response(200, {
        'executions': all_executions,
        'stats': {
            'running': stats['running'],
            'succeeded': stats['succeeded'],
            'failed': stats['failed'],
            'avgDuration': avg_duration
        }
    })


def get_lambda_functions_from_step_function():
    """
    ARCHITECTURAL FIX: Dynamically extract ALL Lambda functions from Step Function definition
    This ensures monitoring automatically picks up ANY new Lambda functions
    """
    try:
        # Get Step Function definition
        sm_response = stepfunctions.list_state_machines()
        state_machines = sm_response.get('stateMachines', [])

        if not state_machines:
            return []

        # Get first state machine (ContentGenerator)
        sm_arn = state_machines[0]['stateMachineArn']
        sm_details = stepfunctions.describe_state_machine(stateMachineArn=sm_arn)
        definition = json.loads(sm_details['definition'])

        # Recursively extract all Lambda function names from definition
        lambda_functions = set()

        def extract_lambdas(obj):
            if isinstance(obj, dict):
                # Check if this is a Lambda invoke task
                if obj.get('Resource') == 'arn:aws:states:::lambda:invoke':
                    params = obj.get('Parameters', {})
                    func_name = params.get('FunctionName', '')
                    if func_name:
                        # Extract function name from ARN or use as-is
                        if 'arn:aws:lambda' in func_name:
                            func_name = func_name.split(':')[-1]
                        lambda_functions.add(func_name)

                # Recurse into nested objects
                for value in obj.values():
                    extract_lambdas(value)
            elif isinstance(obj, list):
                for item in obj:
                    extract_lambdas(item)

        extract_lambdas(definition)
        return list(lambda_functions)

    except Exception as e:
        print(f"Error extracting Lambda functions from Step Function: {str(e)}")
        # Fallback to empty list - will show no logs instead of crashing
        return []


def handle_logs(params):
    limit = int(params.get('limit', 50))

    # ARCHITECTURAL FIX: Get Lambda functions dynamically from Step Function
    lambda_functions = get_lambda_functions_from_step_function()

    if not lambda_functions:
        print("WARNING: No Lambda functions found in Step Function definition")
        return cors_response(200, {'logs': []})

    print(f"Found {len(lambda_functions)} Lambda functions in Step Function: {lambda_functions[:5]}...")

    all_logs = []

    # Get logs from each Lambda function
    for func_name in lambda_functions[:5]:  # Limit to first 5 to avoid timeouts
        log_group_name = f'/aws/lambda/{func_name}'

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
                all_logs.append({
                    'timestamp': timestamp,
                    'message': event['message'].strip(),
                    'source': func_name  # Show which Lambda emitted this log
                })

        except Exception as e:
            print(f"Error getting logs from {log_group_name}: {str(e)}")
            continue

    all_logs.sort(key=lambda x: x['timestamp'], reverse=True)

    return cors_response(200, {'logs': all_logs[:limit]})
