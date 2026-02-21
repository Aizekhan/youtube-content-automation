"""
Retry EC2 Start from SQS Queue
Triggered by EventBridge every 3 minutes to retry failed EC2 starts
"""
import json
import boto3
import os

sqs = boto3.client('sqs', region_name='eu-central-1')
lambda_client = boto3.client('lambda', region_name='eu-central-1')
sfn_client = boto3.client('stepfunctions', region_name='eu-central-1')

QUEUE_URL = 'https://sqs.eu-central-1.amazonaws.com/599297130956/PendingImageGeneration'

def lambda_handler(event, context):
    """
    Reads messages from SQS queue and retries EC2 start
    """
    print(" Checking SQS queue for pending image generation tasks...")

    # Receive messages from queue (long polling)
    response = sqs.receive_message(
        QueueUrl=QUEUE_URL,
        MaxNumberOfMessages=1,  # Process one at a time
        WaitTimeSeconds=5,
        VisibilityTimeout=180  # 3 minutes
    )

    messages = response.get('Messages', [])

    if not messages:
        print(" No messages in queue")
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'No pending tasks'})
        }

    message = messages[0]
    receipt_handle = message['ReceiptHandle']

    try:
        # Parse message body
        body = json.loads(message['Body'])
        print(f" Processing message: {json.dumps(body, indent=2)}")

        execution_arn = body.get('execution_arn')
        collected_prompts = body.get('collected_prompts')
        phase1_results = body.get('phase1_results')

        # Attempt to start EC2 instance
        print(" Attempting to start EC2 SD3.5 instance...")

        ec2_response = lambda_client.invoke(
            FunctionName='ec2-sd35-control',
            InvocationType='RequestResponse',
            Payload=json.dumps({'action': 'start'})
        )

        ec2_result = json.loads(ec2_response['Payload'].read())
        print(f"EC2 response: {json.dumps(ec2_result)}")

        # Check if EC2 started successfully
        if ec2_result.get('statusCode') == 200:
            endpoint = ec2_result.get('endpoint')

            if endpoint:
                print(f" EC2 started successfully! Endpoint: {endpoint}")

                # Resume workflow - invoke image generation
                print(" Invoking image generation...")

                image_gen_response = lambda_client.invoke(
                    FunctionName='content-generate-images',
                    InvocationType='Event',  # Async
                    Payload=json.dumps({
                        'all_prompts': collected_prompts.get('all_image_prompts', []),
                        'provider': 'ec2-sd35',
                        'batch_mode': True,
                        'ec2_endpoint': endpoint,
                        'execution_arn': execution_arn,  # For tracking
                        'resume_workflow': True,
                        'phase1_results': phase1_results
                    })
                )

                print(f" Image generation invoked async")

                # Delete message from queue (success!)
                sqs.delete_message(
                    QueueUrl=QUEUE_URL,
                    ReceiptHandle=receipt_handle
                )

                print(" Message deleted from queue - workflow resumed!")

                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'message': 'EC2 started and workflow resumed',
                        'endpoint': endpoint,
                        'execution_arn': execution_arn
                    })
                }

        # EC2 start failed - message will return to queue
        print(" EC2 start failed - message will retry in 3 minutes")
        print(f"Message receive count: {message.get('Attributes', {}).get('ApproximateReceiveCount', 'unknown')}")

        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'EC2 start failed, will retry',
                'ec2_result': ec2_result
            })
        }

    except Exception as e:
        print(f" Error processing message: {e}")
        import traceback
        traceback.print_exc()

        # Don't delete message - let it retry
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
