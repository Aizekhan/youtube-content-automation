"""
Deploy content-save-result Lambda with episode summary generator
"""
import boto3
import zipfile
import os
import io

lambda_client = boto3.client('lambda', region_name='eu-central-1')

def create_deployment_package():
    """Create deployment package with episode_summary_generator"""

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add main Lambda function
        zipf.write(
            'aws/lambda/content-save-result/lambda_function.py',
            'lambda_function.py'
        )

        # Add episode summary generator
        zipf.write(
            'aws/lambda/content-save-result/episode_summary_generator.py',
            'episode_summary_generator.py'
        )

        # Add shared modules if they exist
        shared_dir = 'aws/lambda/content-save-result/shared'
        if os.path.exists(shared_dir):
            for root, dirs, files in os.walk(shared_dir):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, 'aws/lambda/content-save-result')
                        zipf.write(file_path, arcname)

    return zip_buffer.getvalue()

def deploy_lambda():
    """Deploy Lambda with new code"""

    print("Creating deployment package...")
    zip_content = create_deployment_package()

    print(f"Package size: {len(zip_content) / 1024:.2f} KB")

    print("Updating Lambda function...")

    response = lambda_client.update_function_code(
        FunctionName='content-save-result',
        ZipFile=zip_content
    )

    print(f"✓ Deployed successfully!")
    print(f"  Function: {response['FunctionName']}")
    print(f"  Version: {response['Version']}")
    print(f"  Last Modified: {response['LastModified']}")
    print(f"  Code Size: {response['CodeSize']} bytes")

    return response

if __name__ == '__main__':
    try:
        result = deploy_lambda()
        print("\n✓ Deployment complete!")
    except Exception as e:
        print(f"\n✗ Deployment failed: {e}")
        import traceback
        traceback.print_exc()
