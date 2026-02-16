import json
import boto3
import time

ec2 = boto3.client('ec2', region_name='eu-central-1')

# EC2 Configuration - Z-Image-Turbo
INSTANCE_ID = 'i-0c311fcd95ed6efd3'
INSTANCE_NAME = 'z-image-turbo-server'

def lambda_handler(event, context):
    """Control EC2 instance for Z-Image-Turbo"""
    action = event.get('action', 'status')
    print(f"Z-Image EC2 Control - Action: {action}")

    try:
        if action == 'start':
            return start_instance()
        elif action == 'stop':
            return stop_instance()
        elif action == 'status':
            return get_status()
        else:
            return {'statusCode': 400, 'error': f'Unknown action: {action}'}
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'statusCode': 500, 'error': str(e)}

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
