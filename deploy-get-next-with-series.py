"""
Deploy content-topics-get-next Lambda with SeriesState integration
"""
import boto3
import zipfile
import io

lambda_client = boto3.client('lambda', region_name='eu-central-1')

def create_deployment_package():
    """Create deployment package"""
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(
            'aws/lambda/content-topics-get-next/lambda_function.py',
            'lambda_function.py'
        )

    return zip_buffer.getvalue()

def deploy_lambda():
    """Deploy Lambda"""
    print("Creating deployment package...")
    zip_content = create_deployment_package()
    print(f"   Size: {len(zip_content) / 1024:.2f} KB")

    print("Updating Lambda function...")
    response = lambda_client.update_function_code(
        FunctionName='content-topics-get-next',
        ZipFile=zip_content
    )

    print("Deployed successfully!")
    print(f"  Function: {response['FunctionName']}")
    print(f"  Version: {response['Version']}")
    print(f"  Last Modified: {response['LastModified']}")

    return response

if __name__ == '__main__':
    try:
        deploy_lambda()
        print("\nDeployment complete!")
    except Exception as e:
        print(f"\nDeployment failed: {e}")
        import traceback
        traceback.print_exc()
