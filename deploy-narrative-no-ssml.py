#!/usr/bin/env python3
"""
Deploy content-narrative Lambda
Changes:
- Removed SSML generation from Phase 1b prompt
- Added variation_used constraints (normal by default, dramatic max 1x, whisper for secrets)
"""

import boto3
import zipfile
import os
from datetime import datetime

lambda_client = boto3.client('lambda', region_name='eu-central-1')

def create_deployment_package():
    """Create ZIP with all necessary files"""
    zip_path = '/tmp/content-narrative-no-ssml.zip'

    base_dir = 'aws/lambda/content-narrative'

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Main lambda_function.py
        zipf.write(f'{base_dir}/lambda_function.py', 'lambda_function.py')

        # Shared modules
        for filename in os.listdir(f'{base_dir}/shared'):
            if filename.endswith('.py'):
                zipf.write(
                    f'{base_dir}/shared/{filename}',
                    f'shared/{filename}'
                )

        # Story prompts (including updated phase1b)
        for filename in os.listdir(f'{base_dir}/story_prompts'):
            if filename.endswith('.txt'):
                zipf.write(
                    f'{base_dir}/story_prompts/{filename}',
                    f'story_prompts/{filename}'
                )

    print(f"[OK] Created deployment package: {zip_path}")
    return zip_path

def deploy_lambda(zip_path):
    """Deploy to AWS Lambda"""

    with open(zip_path, 'rb') as f:
        zip_content = f.read()

    try:
        response = lambda_client.update_function_code(
            FunctionName='content-narrative',
            ZipFile=zip_content,
            Publish=True
        )

        print(f"[OK] Deployed content-narrative Lambda")
        print(f"  Version: {response['Version']}")
        print(f"  Last Modified: {response['LastModified']}")
        print(f"  Code Size: {response['CodeSize']} bytes")

        return True

    except Exception as e:
        print(f"[ERROR] Deployment failed: {e}")
        return False

if __name__ == '__main__':
    print("=" * 80)
    print("Deploy content-narrative Lambda (No SSML + variation_used constraints)")
    print("=" * 80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    zip_path = create_deployment_package()
    success = deploy_lambda(zip_path)

    if success:
        print()
        print("=" * 80)
        print("DEPLOYMENT SUCCESSFUL")
        print("=" * 80)
        print()
        print("Changes deployed:")
        print("  1. Phase 1b prompt: Removed SSML instructions, use punctuation instead")
        print("  2. Phase 1b prompt: Added variation_used field with strict constraints:")
        print("     - normal by default")
        print("     - whisper only for secrets/confessions")
        print("     - dramatic maximum 1 time per episode (climax only)")
        print("     - action only for chase/fight scenes")
        print("  3. response_extractor.py: Removed SSML validation")
        print()
    else:
        print()
        print("DEPLOYMENT FAILED")
        exit(1)
