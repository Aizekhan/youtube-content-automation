import json
import boto3
import time

ec2 = boto3.client('ec2', region_name='eu-central-1')

# EC2 Configuration - Z-Image-Turbo
INSTANCE_ID = 'i-0c311fcd95ed6efd3'
INSTANCE_NAME = 'z-image-turbo-server'

def lambda_handler(event, context):
    """Control EC2 instance for Z-Image-Turbo"""
    # Detect invocation type
    is_function_url = 'requestContext' in event and 'http' in event.get('requestContext', {})

    action = event.get('action', 'status')
    print(f"Z-Image EC2 Control - Action: {action}, Invocation: {'Function URL' if is_function_url else 'Lambda Invoke'}")

    try:
        if action == 'start':
            result = start_instance()
        elif action == 'stop':
            result = stop_instance()
        elif action == 'status':
            result = get_status()
        else:
            result = {'statusCode': 400, 'error': f'Unknown action: {action}'}

        # Return format based on invocation type
        if is_function_url:
            status_code = result.get('statusCode', 200)
            return {
                'statusCode': status_code,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(result)
            }
        else:
            # Lambda Invoke - return plain object
            return result

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        error_result = {'statusCode': 500, 'error': str(e)}

        if is_function_url:
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(error_result)
            }
        else:
            return error_result

def start_instance():
    """Start EC2 instance"""
    response = ec2.describe_instances(InstanceIds=[INSTANCE_ID])
    instance = response['Reservations'][0]['Instances'][0]
    state = instance['State']['Name']

    if state == 'running':
        public_ip = instance.get('PublicIpAddress')
        endpoint = f"http://{public_ip}:5000"
        return {
            'statusCode': 200,
            'status': 'running', 'state': 'running',
            'endpoint': endpoint,
            'instance_id': INSTANCE_ID,
            'message': 'Already running'
        }
    elif state == 'stopped':
        print(f"Starting instance: {INSTANCE_ID}")
        ec2.start_instances(InstanceIds=[INSTANCE_ID])

        waiter = ec2.get_waiter('instance_running')
        waiter.wait(InstanceIds=[INSTANCE_ID])

        instance = ec2.describe_instances(InstanceIds=[INSTANCE_ID])['Reservations'][0]['Instances'][0]
        public_ip = instance.get('PublicIpAddress')
        endpoint = f"http://{public_ip}:5000"

        print(f"Instance started: {endpoint}")
        return {
            'statusCode': 200,
            'status': 'running', 'state': 'running',
            'endpoint': endpoint,
            'instance_id': INSTANCE_ID,
            'message': 'Started successfully'
        }
    else:
        return {
            'statusCode': 202,
            'status': state, 'state': state,
            'instance_id': INSTANCE_ID,
            'message': f'Instance is {state}'
        }

def stop_instance():
    """Stop EC2 instance"""
    response = ec2.describe_instances(InstanceIds=[INSTANCE_ID])
    instance = response['Reservations'][0]['Instances'][0]
    state = instance['State']['Name']

    if state == 'stopped':
        return {'statusCode': 200, 'status': 'stopped', 'state': 'stopped', 'instance_id': INSTANCE_ID}
    elif state == 'running':
        print(f"Stopping instance: {INSTANCE_ID}")
        ec2.stop_instances(InstanceIds=[INSTANCE_ID])
        return {'statusCode': 200, 'status': 'stopping', 'state': 'stopping', 'instance_id': INSTANCE_ID}
    else:
        return {'statusCode': 202, 'status': state, 'state': state, 'instance_id': INSTANCE_ID}

def get_status():
    """Get instance status"""
    instance = ec2.describe_instances(InstanceIds=[INSTANCE_ID])['Reservations'][0]['Instances'][0]
    state = instance['State']['Name']
    public_ip = instance.get('PublicIpAddress')

    result = {'statusCode': 200, 'status': state, 'state': state, 'instance_id': INSTANCE_ID}
    if public_ip:
        result['endpoint'] = f"http://{public_ip}:5000"
    return result
