import json
import boto3
import time
from datetime import datetime

ec2 = boto3.client('ec2', region_name='eu-central-1')

# EC2 Configuration
INSTANCE_NAME = 'qwen3-tts-server'
INSTANCE_TYPE = 'g4dn.xlarge'
AMI_ID = 'ami-015b956468289e022'  # Qwen3-TTS Production with auto-start service (2026-02-12)
KEY_NAME = 'n8n-key'
SECURITY_GROUP_ID = 'sg-08aee4fb3504062dc'
SUBNET_ID = 'subnet-0ac0c300488c280ff'
IAM_INSTANCE_PROFILE = 'arn:aws:iam::599297130956:instance-profile/qwen3-ec2-instance-profile'

# Health check configuration
HEALTH_CHECK_URL = 'http://{ip}:5000/health'
MAX_STARTUP_WAIT = 300  # 5 minutes max wait for startup

def lambda_handler(event, context):
    """
    Control EC2 instance for Qwen3-TTS

    Actions:
    - start: Launch or start EC2 instance
    - stop: Stop EC2 instance
    - status: Get instance status and endpoint

    Input:
    {
        "action": "start" | "stop" | "status"
    }

    Output:
    {
        "status": "running" | "stopped" | "starting",
        "endpoint": "http://ip:5000",
        "instance_id": "i-xxxxx",
        "message": "..."
    }
    """

    action = event.get('action', 'status')

    print(f" EC2 Qwen3-TTS Control - Action: {action}")

    try:
        if action == 'start':
            return start_instance()
        elif action == 'stop':
            return stop_instance()
        elif action == 'status':
            return get_status()
        else:
            return {
                'statusCode': 400,
                'error': f'Unknown action: {action}'
            }

    except Exception as e:
        print(f" Error: {str(e)}")
        import traceback
        traceback.print_exc()

        return {
            'statusCode': 500,
            'error': str(e),
            'message': 'EC2 control failed'
        }


def find_instance():
    """Find existing Qwen3-TTS EC2 instance by name tag"""
    try:
        response = ec2.describe_instances(
            Filters=[
                {'Name': 'tag:Name', 'Values': [INSTANCE_NAME]},
                {'Name': 'instance-state-name', 'Values': ['running', 'stopped', 'stopping', 'pending']}
            ]
        )

        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                return instance

        return None

    except Exception as e:
        print(f"Error finding instance: {e}")
        return None


def start_instance():
    """Start or create EC2 instance"""

    # Check if instance exists
    instance = find_instance()

    if instance:
        instance_id = instance['InstanceId']
        state = instance['State']['Name']

        print(f" Found existing instance: {instance_id} (state: {state})")

        if state == 'running':
            # Already running, return endpoint immediately (Step Functions will check health)
            public_ip = instance.get('PublicIpAddress')
            if not public_ip:
                print("  Instance running but no public IP yet, waiting...")
                time.sleep(5)
                instance = get_instance_by_id(instance_id)
                public_ip = instance.get('PublicIpAddress')

            endpoint = f"http://{public_ip}:5000"

            return {
                'statusCode': 202,
                'status': 'starting',
                'endpoint': endpoint,
                'instance_id': instance_id,
                'message': 'Instance running, service starting (wait 2-3 min)'
            }

        elif state == 'stopped':
            # Start existing instance
            print(f" Starting stopped instance: {instance_id}")
            ec2.start_instances(InstanceIds=[instance_id])

            # Wait for running state
            waiter = ec2.get_waiter('instance_running')
            waiter.wait(InstanceIds=[instance_id])

            # Get public IP
            instance = get_instance_by_id(instance_id)
            public_ip = instance.get('PublicIpAddress')
            endpoint = f"http://{public_ip}:5000"

            print(f" Instance started: {endpoint}")

            return {
                'statusCode': 202,
                'status': 'starting',
                'endpoint': endpoint,
                'instance_id': instance_id,
                'message': 'Instance started, service starting (wait 2-3 min)'
            }

        elif state == 'stopping':
            # Wait for instance to fully stop, then start it
            print(f"Instance is stopping, waiting for stopped state...")
            waiter = ec2.get_waiter('instance_stopped')
            waiter.wait(InstanceIds=[instance_id], WaiterConfig={'Delay': 5, 'MaxAttempts': 60})

            print(f"Instance stopped, now starting...")
            ec2.start_instances(InstanceIds=[instance_id])

            # Wait for running state
            waiter = ec2.get_waiter('instance_running')
            waiter.wait(InstanceIds=[instance_id])

            # Get public IP
            instance = get_instance_by_id(instance_id)
            public_ip = instance.get('PublicIpAddress')
            endpoint = f"http://{public_ip}:5000"

            print(f"Instance started: {endpoint}")

            return {
                'statusCode': 202,
                'status': 'starting',
                'endpoint': endpoint,
                'instance_id': instance_id,
                'message': 'Instance was stopping, waited and started'
            }

        elif state == 'pending':
            return {
                'statusCode': 202,
                'status': 'pending',
                'instance_id': instance_id,
                'message': 'Instance is pending, wait and retry'
            }

    else:
        # Create new instance
        print(f" Creating new instance: {INSTANCE_NAME}")

        # Launch instance (UserData not needed - service auto-starts from AMI)
        response = ec2.run_instances(
            ImageId=AMI_ID,
            InstanceType=INSTANCE_TYPE,
            KeyName=KEY_NAME,
            SecurityGroupIds=[SECURITY_GROUP_ID],
            SubnetId=SUBNET_ID,
            IamInstanceProfile={'Arn': IAM_INSTANCE_PROFILE},
            MinCount=1,
            MaxCount=1,
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': 'Name', 'Value': INSTANCE_NAME},
                        {'Key': 'Service', 'Value': 'Qwen3-TTS'},
                        {'Key': 'ManagedBy', 'Value': 'Lambda'}
                    ]
                }
            ],
            BlockDeviceMappings=[
                {
                    'DeviceName': '/dev/sda1',
                    'Ebs': {
                        'VolumeSize': 80,
                        'VolumeType': 'gp3',
                        'DeleteOnTermination': True
                    }
                }
            ]
        )

        instance_id = response['Instances'][0]['InstanceId']
        print(f" Instance created: {instance_id}")

        # Wait for running state
        print(" Waiting for instance to start...")
        waiter = ec2.get_waiter('instance_running')
        waiter.wait(InstanceIds=[instance_id])

        # Get public IP
        instance = get_instance_by_id(instance_id)
        public_ip = instance.get('PublicIpAddress')
        endpoint = f"http://{public_ip}:5000"

        print(f" Instance running: {endpoint}")
        print(" Waiting for Qwen3-TTS service to start (may take 2-3 minutes)...")

        return {
            'statusCode': 202,
            'status': 'starting',
            'endpoint': endpoint,
            'instance_id': instance_id,
            'message': 'Instance created, service starting (wait 2-3 min)'
        }


def stop_instance():
    """Stop EC2 instance"""

    instance = find_instance()

    if not instance:
        return {
            'statusCode': 404,
            'status': 'not_found',
            'message': 'No instance found'
        }

    instance_id = instance['InstanceId']
    state = instance['State']['Name']

    if state == 'stopped':
        return {
            'statusCode': 200,
            'status': 'stopped',
            'instance_id': instance_id,
            'message': 'Instance already stopped'
        }

    elif state == 'running':
        print(f"  Stopping instance: {instance_id}")
        ec2.stop_instances(InstanceIds=[instance_id])

        return {
            'statusCode': 200,
            'status': 'stopping',
            'instance_id': instance_id,
            'message': 'Instance stop initiated'
        }

    else:
        return {
            'statusCode': 202,
            'status': state,
            'instance_id': instance_id,
            'message': f'Instance is {state}'
        }


def get_status():
    """Get instance status"""

    instance = find_instance()

    if not instance:
        return {
            'statusCode': 404,
            'status': 'not_found',
            'message': 'No instance exists'
        }

    instance_id = instance['InstanceId']
    state = instance['State']['Name']
    public_ip = instance.get('PublicIpAddress')

    result = {
        'statusCode': 200,
        'status': state,
        'instance_id': instance_id,
        'instance_type': instance['InstanceType']
    }

    if public_ip:
        endpoint = f"http://{public_ip}:5000"
        result['endpoint'] = endpoint

        # Check health if running
        if state == 'running':
            healthy = check_health(endpoint)
            result['healthy'] = healthy
            result['message'] = 'Service healthy' if healthy else 'Service not responding'

    return result


def get_instance_by_id(instance_id):
    """Get instance details by ID"""
    response = ec2.describe_instances(InstanceIds=[instance_id])
    return response['Reservations'][0]['Instances'][0]


def check_health(endpoint):
    """Check if Qwen3-TTS service is healthy"""
    try:
        import urllib.request
        import json as json_module

        health_url = f"{endpoint}/health"
        req = urllib.request.Request(health_url, method='GET')

        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json_module.loads(response.read().decode('utf-8'))
                return data.get('status') == 'healthy' and data.get('models_loaded', 0) >= 3

        return False

    except Exception as e:
        print(f"Health check failed: {e}")
        return False


def get_userdata_script():
    """Get UserData script for EC2 initialization"""

    # Reference to the setup script in S3 or inline
    # For now, return inline script

    script = """#!/bin/bash
# Download and execute Qwen3-TTS setup script
curl -fsSL https://raw.githubusercontent.com/YOUR_REPO/main/aws/ec2-qwen3-tts-setup.sh -o /tmp/setup.sh
chmod +x /tmp/setup.sh
bash /tmp/setup.sh
"""

    return script


if __name__ == "__main__":
    # Test locally
    print(lambda_handler({'action': 'status'}, None))
