"""
Deploy content-save-result Lambda with episode summary generator and openai library
"""
import boto3
import zipfile
import os
import io
import subprocess
import tempfile
import shutil

lambda_client = boto3.client('lambda', region_name='eu-central-1')

def create_deployment_package():
    """Create deployment package with episode_summary_generator and openai"""

    print("Installing openai library...")
    temp_dir = tempfile.mkdtemp()

    try:
        # Install openai to temp directory for Lambda (Amazon Linux 2 / Python 3.11)
        subprocess.check_call([
            'pip', 'install',
            'openai',
            '-t', temp_dir,
            '--platform', 'manylinux2014_x86_64',
            '--only-binary=:all:',
            '--python-version', '3.11',
            '--no-cache-dir',
            '--quiet'
        ])

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

            # Add openai library and dependencies from temp directory
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)

        return zip_buffer.getvalue()

    finally:
        # Cleanup temp directory
        shutil.rmtree(temp_dir, ignore_errors=True)

def deploy_lambda():
    """Deploy Lambda with new code"""

    print("Creating deployment package with openai...")
    zip_content = create_deployment_package()

    print(f"Package size: {len(zip_content) / 1024:.2f} KB")

    print("Updating Lambda function...")

    response = lambda_client.update_function_code(
        FunctionName='content-save-result',
        ZipFile=zip_content
    )

    print("Deployed successfully!")
    print(f"  Function: {response['FunctionName']}")
    print(f"  Version: {response['Version']}")
    print(f"  Last Modified: {response['LastModified']}")
    print(f"  Code Size: {response['CodeSize']} bytes")

    return response

if __name__ == '__main__':
    try:
        result = deploy_lambda()
        print("\nDeployment complete!")
    except Exception as e:
        print(f"\nDeployment failed: {e}")
        import traceback
        traceback.print_exc()
