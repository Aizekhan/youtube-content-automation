#!/usr/bin/env python3
"""
Quick Deploy Script for debug-test-runner Lambda
Runs locally with AWS credentials
"""

import boto3
import zipfile
import os
import json
from io import BytesIO

# Configuration
FUNCTION_NAME = 'debug-test-runner'
REGION = 'eu-central-1'
RUNTIME = 'python3.11'
HANDLER = 'lambda_function.lambda_handler'
TIMEOUT = 300
MEMORY_SIZE = 512

# Lambda execution role ARN (update if needed)
ROLE_ARN = 'arn:aws:iam::599297130956:role/lambda-execution-role'

def create_deployment_package():
    """Create a ZIP file with lambda_function.py"""
    print("📦 Creating deployment package...")

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write('lambda_function.py', 'lambda_function.py')

    zip_buffer.seek(0)
    print(f"✅ Package created: {len(zip_buffer.getvalue())} bytes")
    return zip_buffer.getvalue()

def deploy_lambda():
    """Deploy or update Lambda function"""
    print(f"🚀 Deploying {FUNCTION_NAME} to AWS Lambda...")

    # Create Lambda client
    lambda_client = boto3.client('lambda', region_name=REGION)

    # Create deployment package
    zip_content = create_deployment_package()

    try:
        # Try to update existing function
        print(f"📝 Attempting to update existing function...")
        response = lambda_client.update_function_code(
            FunctionName=FUNCTION_NAME,
            ZipFile=zip_content
        )
        print(f"✅ Function code updated!")

        # Update configuration
        print(f"⚙️  Updating function configuration...")
        lambda_client.update_function_configuration(
            FunctionName=FUNCTION_NAME,
            Timeout=TIMEOUT,
            MemorySize=MEMORY_SIZE
        )
        print(f"✅ Configuration updated!")

    except lambda_client.exceptions.ResourceNotFoundException:
        # Function doesn't exist, create it
        print(f"🆕 Function not found, creating new one...")

        response = lambda_client.create_function(
            FunctionName=FUNCTION_NAME,
            Runtime=RUNTIME,
            Role=ROLE_ARN,
            Handler=HANDLER,
            Code={'ZipFile': zip_content},
            Timeout=TIMEOUT,
            MemorySize=MEMORY_SIZE,
            Description='Debug test runner for content generation pipeline'
        )
        print(f"✅ Function created!")

    # Get or create Function URL
    print(f"🔗 Setting up Function URL...")
    try:
        url_response = lambda_client.get_function_url_config(
            FunctionName=FUNCTION_NAME
        )
        function_url = url_response['FunctionUrl']
        print(f"✅ Function URL already exists")
    except lambda_client.exceptions.ResourceNotFoundException:
        # Create Function URL
        url_response = lambda_client.create_function_url_config(
            FunctionName=FUNCTION_NAME,
            AuthType='NONE',
            Cors={
                'AllowOrigins': ['*'],
                'AllowMethods': ['POST', 'GET', 'OPTIONS'],
                'AllowHeaders': ['Content-Type'],
                'MaxAge': 86400
            }
        )
        function_url = url_response['FunctionUrl']

        # Add permission for public access
        try:
            lambda_client.add_permission(
                FunctionName=FUNCTION_NAME,
                StatementId='FunctionURLAllowPublicAccess',
                Action='lambda:InvokeFunctionUrl',
                Principal='*',
                FunctionUrlAuthType='NONE'
            )
        except:
            pass  # Permission might already exist

        print(f"✅ Function URL created")

    print(f"\n{'='*60}")
    print(f"✅ DEPLOYMENT COMPLETE!")
    print(f"{'='*60}")
    print(f"Function Name: {FUNCTION_NAME}")
    print(f"Region: {REGION}")
    print(f"Function URL: {function_url}")
    print(f"\n💡 Next step: Update debug-dashboard.html with this URL:")
    print(f"   const DEBUG_API_URL = '{function_url}';")
    print(f"{'='*60}\n")

    # Save URL to file
    with open('function_url.txt', 'w') as f:
        f.write(function_url)
    print(f"📄 URL saved to function_url.txt")

    return function_url

if __name__ == '__main__':
    try:
        # Check AWS credentials
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"👤 AWS Account: {identity['Account']}")
        print(f"👤 User/Role: {identity['Arn']}\n")

        # Deploy
        deploy_lambda()

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print(f"\n💡 Make sure AWS credentials are configured:")
        print(f"   Option 1: Set environment variables:")
        print(f"     set AWS_ACCESS_KEY_ID=your_key")
        print(f"     set AWS_SECRET_ACCESS_KEY=your_secret")
        print(f"     set AWS_DEFAULT_REGION=eu-central-1")
        print(f"\n   Option 2: Configure AWS CLI:")
        print(f"     aws configure")
        import traceback
        traceback.print_exc()
