"""
Deploy content-series-state Lambda - Series Memory CRUD
"""
import boto3
import zipfile
import io

lambda_client = boto3.client('lambda', region_name='eu-central-1')

def create_deployment_package():
    """Create deployment package with Lambda function"""

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add main Lambda function
        zipf.write(
            'aws/lambda/content-series-state/lambda_function.py',
            'lambda_function.py'
        )

    return zip_buffer.getvalue()

def deploy_lambda():
    """Deploy Lambda with new code"""

    print("Creating deployment package...")
    zip_content = create_deployment_package()

    print(f"   Size: {len(zip_content) / 1024:.2f} KB")

    # Check if Lambda exists
    try:
        lambda_client.get_function(FunctionName='content-series-state')
        print("Updating existing Lambda function...")

        response = lambda_client.update_function_code(
            FunctionName='content-series-state',
            ZipFile=zip_content
        )

    except lambda_client.exceptions.ResourceNotFoundException:
        print("Creating new Lambda function...")

        # Get IAM role ARN
        iam = boto3.client('iam')
        role = iam.get_role(RoleName='ContentGeneratorLambdaRole')
        role_arn = role['Role']['Arn']

        response = lambda_client.create_function(
            FunctionName='content-series-state',
            Runtime='python3.11',
            Role=role_arn,
            Handler='lambda_function.lambda_handler',
            Code={'ZipFile': zip_content},
            Description='Series State CRUD - Sprint 4',
            Timeout=30,
            MemorySize=512,
            Environment={
                'Variables': {}
            }
        )

    print("Deployed successfully!")
    print(f"   Function: {response['FunctionName']}")
    print(f"   Version: {response['Version']}")
    print(f"   Last Modified: {response['LastModified']}")
    print(f"   Code Size: {response['CodeSize']} bytes")

    return response

if __name__ == '__main__':
    try:
        result = deploy_lambda()
        print("\nDeployment complete!")
    except Exception as e:
        print(f"\nDeployment failed: {e}")
        import traceback
        traceback.print_exc()
