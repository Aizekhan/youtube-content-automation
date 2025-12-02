import json
import boto3
import time
from datetime import datetime
from botocore.exceptions import ClientError

ec2 = boto3.client('ec2', region_name='eu-central-1')
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')

# SD 3.5 Medium instance configuration
INSTANCE_ID = 'i-0a71aa2e72e9b9f75'
API_PORT = 5000

# WEEK 3.5: DynamoDB table for race condition prevention
# This table tracks EC2 instance state to prevent concurrent start operations
LOCK_TABLE_NAME = 'EC2InstanceLocks'


def acquire_start_lock(instance_id):
    """
    WEEK 3.5: Acquire lock to start instance using DynamoDB conditional update

    This prevents race conditions where multiple Lambda invocations
    try to start the same instance simultaneously.

    Returns:
        bool: True if lock acquired, False if another process has the lock
    """
    table = dynamodb.Table(LOCK_TABLE_NAME)

    try:
        # Try to update state from 'stopped' to 'starting'
        # This will fail if another Lambda already changed the state
        response = table.update_item(
            Key={'instance_id': instance_id},
            UpdateExpression='SET instance_state = :starting, updated_at = :now',
            ConditionExpression='instance_state = :stopped OR attribute_not_exists(instance_state)',
            ExpressionAttributeValues={
                ':starting': 'starting',
                ':stopped': 'stopped',
                ':now': datetime.utcnow().isoformat() + 'Z'
            },
            ReturnValues='ALL_NEW'
        )
        print(f"✅ Lock acquired for instance {instance_id}")
        return True

    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            # Another Lambda is already starting this instance
            print(f"⚠️ Lock already held for instance {instance_id} - another process is starting it")
            return False
        else:
            # Other error - re-raise
            raise


def release_start_lock(instance_id, final_state='running'):
    """
    WEEK 3.5: Release lock after instance is started

    Args:
        instance_id: EC2 instance ID
        final_state: Final state to set ('running' or 'failed')
    """
    table = dynamodb.Table(LOCK_TABLE_NAME)

    try:
        table.update_item(
            Key={'instance_id': instance_id},
            UpdateExpression='SET instance_state = :final_state, updated_at = :now',
            ExpressionAttributeValues={
                ':final_state': final_state,
                ':now': datetime.utcnow().isoformat() + 'Z'
            }
        )
        print(f"✅ Lock released for instance {instance_id}, state: {final_state}")

    except Exception as e:
        print(f"⚠️ Failed to release lock: {e}")
        # Don't fail the whole operation just because we couldn't release the lock


def update_instance_state(instance_id, state):
    """
    WEEK 3.5: Update instance state in DynamoDB without lock conditions

    Args:
        instance_id: EC2 instance ID
        state: New state ('stopped', 'running', etc.)
    """
    table = dynamodb.Table(LOCK_TABLE_NAME)

    try:
        table.put_item(
            Item={
                'instance_id': instance_id,
                'instance_state': state,
                'updated_at': datetime.utcnow().isoformat() + 'Z'
            }
        )
    except Exception as e:
        print(f"⚠️ Failed to update state in DynamoDB: {e}")
        # Don't fail the operation


def lambda_handler(event, context):
    """
    EC2 SD 3.5 Medium Control Lambda

    Actions:
    - start: Start instance and return endpoint
    - stop: Stop instance
    - status: Check instance status

    Note: CORS is handled by Function URL configuration
    Returns different format based on invocation type:
    - HTTP (Function URL): {statusCode, body}
    - Direct (Step Functions): plain JSON object
    """

    # Detect invocation type
    # Function URLs have 'requestContext' or 'headers'
    # Step Functions calls have neither - just the payload
    is_http = 'requestContext' in event or 'headers' in event

    # Parse body if present
    if 'body' in event:
        try:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            action = body.get('action', '').lower()
        except:
            action = event.get('action', '').lower()
    else:
        action = event.get('action', '').lower()

    try:
        if action == 'start':
            return start_instance(is_http)
        elif action == 'stop':
            return stop_instance(is_http)
        elif action == 'status':
            return get_status(is_http)
        else:
            error_data = {'error': f'Unknown action: {action}'}
            if is_http:
                return {'statusCode': 400, 'body': json.dumps(error_data)}
            else:
                return error_data
    except Exception as e:
        print(f"❌ Error: {e}")
        error_data = {'error': str(e)}
        if is_http:
            return {'statusCode': 500, 'body': json.dumps(error_data)}
        else:
            return error_data


def start_instance(is_http=True):
    """
    Start EC2 instance and wait for it to be ready

    WEEK 3.5: Now uses DynamoDB optimistic locking to prevent race conditions
    """
    print(f"🚀 Starting instance {INSTANCE_ID}...")

    # Check current state
    response = ec2.describe_instances(InstanceIds=[INSTANCE_ID])
    state = response['Reservations'][0]['Instances'][0]['State']['Name']

    if state == 'running':
        print("✅ Instance already running")
        ip = response['Reservations'][0]['Instances'][0]['PublicIpAddress']
        endpoint = f"http://{ip}:{API_PORT}"

        # Update DynamoDB state
        update_instance_state(INSTANCE_ID, 'running')

        # Check if API is ready
        if wait_for_api(endpoint):
            result = {'state': 'running', 'endpoint': endpoint, 'ip': ip}
            return {'statusCode': 200, 'body': json.dumps(result)} if is_http else result
        else:
            # API not ready after timeout
            error = {'error': 'API not ready after timeout', 'state': 'running', 'ip': ip}
            return {'statusCode': 500, 'body': json.dumps(error)} if is_http else error

    if state in ['stopped', 'stopping']:
        # WEEK 3.5: Acquire lock before starting instance
        # This prevents multiple Lambdas from starting the same instance
        if not acquire_start_lock(INSTANCE_ID):
            # Another Lambda is already starting this instance
            print("⏳ Another Lambda is already starting this instance - waiting for it...")

            # Wait a bit and check current state
            time.sleep(5)
            response = ec2.describe_instances(InstanceIds=[INSTANCE_ID])
            current_state = response['Reservations'][0]['Instances'][0]['State']['Name']

            if current_state == 'running':
                ip = response['Reservations'][0]['Instances'][0]['PublicIpAddress']
                endpoint = f"http://{ip}:{API_PORT}"
                result = {'state': 'running', 'endpoint': endpoint, 'ip': ip, 'note': 'Started by another Lambda'}
                return {'statusCode': 200, 'body': json.dumps(result)} if is_http else result
            else:
                result = {'state': current_state, 'note': 'Another Lambda is starting the instance'}
                return {'statusCode': 202, 'body': json.dumps(result)} if is_http else result

        try:
            # Start the instance
            ec2.start_instances(InstanceIds=[INSTANCE_ID])
            print("⏳ Waiting for instance to start...")

            # Wait for running state
            waiter = ec2.get_waiter('instance_running')
            waiter.wait(InstanceIds=[INSTANCE_ID])

            # Get IP address
            response = ec2.describe_instances(InstanceIds=[INSTANCE_ID])
            ip = response['Reservations'][0]['Instances'][0]['PublicIpAddress']
            endpoint = f"http://{ip}:{API_PORT}"

            print(f"✅ Instance running at {ip}")

            # Wait for API to be ready
            if wait_for_api(endpoint):
                # Release lock with success state
                release_start_lock(INSTANCE_ID, 'running')

                result = {'state': 'running', 'endpoint': endpoint, 'ip': ip}
                return {'statusCode': 200, 'body': json.dumps(result)} if is_http else result
            else:
                # API not ready - release lock with failed state
                release_start_lock(INSTANCE_ID, 'failed')
                raise Exception('API not ready after timeout')

        except Exception as e:
            # Release lock on failure
            release_start_lock(INSTANCE_ID, 'failed')
            raise

    error = {'error': f'Cannot start from state: {state}'}
    return {'statusCode': 400, 'body': json.dumps(error)} if is_http else error


def stop_instance(is_http=True):
    """
    Stop EC2 instance

    WEEK 3.5: Now updates DynamoDB state
    WEEK 5.4 FIX: Wait for EC2 to fully stop before updating state to 'stopped'
    """
    print(f"🛑 Stopping instance {INSTANCE_ID}...")

    response = ec2.describe_instances(InstanceIds=[INSTANCE_ID])
    state = response['Reservations'][0]['Instances'][0]['State']['Name']

    if state == 'stopped':
        print("✅ Instance already stopped")
        # Update DynamoDB state
        update_instance_state(INSTANCE_ID, 'stopped')
        result = {'state': 'stopped'}
        return {'statusCode': 200, 'body': json.dumps(result)} if is_http else result

    if state == 'running':
        # Update DynamoDB state to stopping
        update_instance_state(INSTANCE_ID, 'stopping')

        # Initiate EC2 stop
        ec2.stop_instances(InstanceIds=[INSTANCE_ID])
        print("✅ Stop initiated, waiting for instance to fully stop...")

        # WEEK 5.4 FIX: Wait for EC2 to actually stop (max 4 minutes)
        try:
            waiter = ec2.get_waiter('instance_stopped')
            waiter.wait(
                InstanceIds=[INSTANCE_ID],
                WaiterConfig={'Delay': 15, 'MaxAttempts': 16}  # 15s * 16 = 4 minutes
            )
            print("✅ Instance fully stopped")

            # Update DynamoDB state to stopped
            update_instance_state(INSTANCE_ID, 'stopped')
            result = {'state': 'stopped'}
            return {'statusCode': 200, 'body': json.dumps(result)} if is_http else result

        except Exception as e:
            print(f"⚠️ Error waiting for instance to stop: {e}")
            # Return stopping state if wait fails
            result = {'state': 'stopping', 'error': str(e)}
            return {'statusCode': 200, 'body': json.dumps(result)} if is_http else result

    result = {'state': state}
    return {'statusCode': 200, 'body': json.dumps(result)} if is_http else result


def get_status(is_http=True):
    """Get instance status"""
    response = ec2.describe_instances(InstanceIds=[INSTANCE_ID])
    instance = response['Reservations'][0]['Instances'][0]
    state = instance['State']['Name']

    result = {'state': state}

    if state == 'running':
        ip = instance.get('PublicIpAddress')
        if ip:
            result['endpoint'] = f"http://{ip}:{API_PORT}"
            result['ip'] = ip

    return {'statusCode': 200, 'body': json.dumps(result)} if is_http else result


def wait_for_api(endpoint, timeout=300):
    """Wait for SD 3.5 API to be ready"""
    import http.client
    from urllib.parse import urlparse

    print(f"⏳ Waiting for API at {endpoint}/health...")

    parsed = urlparse(endpoint)
    host = parsed.hostname
    port = parsed.port or 5000

    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            conn = http.client.HTTPConnection(host, port, timeout=5)
            conn.request("GET", "/health")
            response = conn.getresponse()

            if response.status == 200:
                data = json.loads(response.read().decode())
                if data.get('model_loaded'):
                    print(f"✅ API ready! Model: {data.get('model')}, GPU: {data.get('gpu')}")
                    return True
                else:
                    print(f"⏳ Model loading... ({int(time.time() - start_time)}s)")

            conn.close()
        except Exception as e:
            print(f"⏳ API not ready yet... ({int(time.time() - start_time)}s)")

        time.sleep(10)

    print(f"❌ API not ready after {timeout}s")
    return False
