#!/usr/bin/env python3
"""
Deploy collect-audio-scenes Lambda
Changes:
- Simplified VOICE_DESCRIPTIONS (natural, conversational style)
- Removed emotional_beat from voice_description
"""

import boto3
import zipfile
import os
from datetime import datetime

lambda_client = boto3.client('lambda', region_name='eu-central-1')

def create_deployment_package():
    """Create ZIP with all necessary files"""
    zip_path = '/tmp/collect-audio-scenes.zip'

    base_dir = 'aws/lambda/collect-audio-scenes'

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Main lambda_function.py
        zipf.write(f'{base_dir}/lambda_function.py', 'lambda_function.py')

        # narrative_parser.py
        if os.path.exists(f'{base_dir}/narrative_parser.py'):
            zipf.write(f'{base_dir}/narrative_parser.py', 'narrative_parser.py')

    print(f"[OK] Created deployment package: {zip_path}")
    return zip_path

def deploy_lambda(zip_path):
    """Deploy to AWS Lambda"""

    with open(zip_path, 'rb') as f:
        zip_content = f.read()

    try:
        response = lambda_client.update_function_code(
            FunctionName='collect-audio-scenes',
            ZipFile=zip_content,
            Publish=True
        )

        print(f"[OK] Deployed collect-audio-scenes Lambda")
        print(f"  Version: {response['Version']}")
        print(f"  Last Modified: {response['LastModified']}")
        print(f"  Code Size: {response['CodeSize']} bytes")

        return True

    except Exception as e:
        print(f"[ERROR] Deployment failed: {e}")
        return False

if __name__ == '__main__':
    print("=" * 80)
    print("Deploy collect-audio-scenes Lambda (Simplified voice descriptions)")
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
        print("  1. Simplified VOICE_DESCRIPTIONS:")
        print("     - normal: Clear, natural voice. Speak at calm pace...")
        print("     - whisper: Quiet, intimate voice...")
        print("     - dramatic: Speak with quiet intensity...")
        print("     - action: Slightly faster pace with energy...")
        print("  2. Removed emotional_beat from voice_description")
        print()
    else:
        print()
        print("DEPLOYMENT FAILED")
        exit(1)
