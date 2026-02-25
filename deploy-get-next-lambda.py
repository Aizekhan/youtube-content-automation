import zipfile
import boto3
import os

# Create deployment package
zip_path = 'E:/youtube-content-automation/get-next-function.zip'

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    zf.write('E:/youtube-content-automation/aws/lambda/content-topics-get-next/lambda_function.py', 'lambda_function.py')

print(f"Created ZIP: {zip_path} ({os.path.getsize(zip_path)} bytes)")

# Deploy to Lambda
lambda_client = boto3.client('lambda', region_name='eu-central-1')

with open(zip_path, 'rb') as f:
    zip_content = f.read()

response = lambda_client.update_function_code(
    FunctionName='content-topics-get-next',
    ZipFile=zip_content
)

print(f"✓ Deployed to Lambda: {response['FunctionName']}")
print(f"  Version: {response['Version']}")
print(f"  Last Modified: {response['LastModified']}")
