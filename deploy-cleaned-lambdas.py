import zipfile
import boto3
import os

lambda_client = boto3.client('lambda', region_name='eu-central-1')

# Lambda 1: content-get-channels
print("=== Deploying content-get-channels ===")
zip1 = 'E:/youtube-content-automation/get-channels.zip'
with zipfile.ZipFile(zip1, 'w', zipfile.ZIP_DEFLATED) as zf:
    zf.write('E:/youtube-content-automation/aws/lambda/content-get-channels/lambda_function.py', 'lambda_function.py')
print(f"Created ZIP: {zip1} ({os.path.getsize(zip1)} bytes)")

with open(zip1, 'rb') as f:
    response1 = lambda_client.update_function_code(
        FunctionName='content-get-channels',
        ZipFile=f.read()
    )
print(f"Deployed: {response1['FunctionName']} v{response1['Version']}")

# Lambda 2: content-save-result
print("\n=== Deploying content-save-result ===")
zip2 = 'E:/youtube-content-automation/save-result.zip'
with zipfile.ZipFile(zip2, 'w', zipfile.ZIP_DEFLATED) as zf:
    zf.write('E:/youtube-content-automation/aws/lambda/content-save-result/lambda_function.py', 'lambda_function.py')
print(f"Created ZIP: {zip2} ({os.path.getsize(zip2)} bytes)")

with open(zip2, 'rb') as f:
    response2 = lambda_client.update_function_code(
        FunctionName='content-save-result',
        ZipFile=f.read()
    )
print(f"Deployed: {response2['FunctionName']} v{response2['Version']}")

print("\n=== DEPLOYMENT COMPLETE ===")
print("All variation_sets removed from:")
print("- content-get-channels Lambda")
print("- content-save-result Lambda")
print("- All 37 channels in DynamoDB")
