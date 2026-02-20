#!/usr/bin/env python3
"""
Create deployment package for content-topic-analyzer Lambda
"""

import zipfile
import os
import subprocess
import sys

def create_deployment_package():
    """Create ZIP file for Lambda deployment"""

    print("Creating deployment package for content-topic-analyzer...")

    # Install dependencies
    print("\n1. Installing dependencies...")
    subprocess.run([
        sys.executable, '-m', 'pip', 'install',
        '-r', 'requirements.txt',
        '-t', '.',
        '--upgrade'
    ], check=True)

    print("\n2. Creating ZIP package...")
    with zipfile.ZipFile('function.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add all Python files
        for root, dirs, files in os.walk('.'):
            # Skip certain directories
            if any(skip in root for skip in ['.git', '__pycache__', 'function.zip', '.pytest_cache']):
                continue

            for file in files:
                if file.endswith(('.py', '.json')) or file == 'requirements.txt':
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, '.')
                    zipf.write(file_path, arcname)
                    print(f"   Added {arcname}")

                # Add dependencies
                elif file.endswith('.so') or file.endswith('.pyd'):
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, '.')
                    zipf.write(file_path, arcname)

        # Add OpenAI package files
        for root, dirs, files in os.walk('.'):
            if 'openai' in root or 'boto3' in root or 'botocore' in root:
                for file in files:
                    if not file.endswith('.pyc'):
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, '.')
                        try:
                            zipf.write(file_path, arcname)
                        except:
                            pass

    print(f"\n3. Created function.zip")
    print(f"   ZIP size: {os.path.getsize('function.zip') / 1024 / 1024:.2f} MB")

if __name__ == '__main__':
    create_deployment_package()
