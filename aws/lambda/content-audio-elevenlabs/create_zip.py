#!/usr/bin/env python3
"""
Create deployment package for content-audio-elevenlabs Lambda
Includes requests library for ElevenLabs API calls
"""

import os
import zipfile
import subprocess
import shutil

def create_deployment_package():
    """Create ZIP file for Lambda deployment"""

    lambda_dir = os.path.dirname(os.path.abspath(__file__))
    zip_path = os.path.join(lambda_dir, 'function.zip')
    package_dir = os.path.join(lambda_dir, 'package')

    # Remove old files if exist
    if os.path.exists(zip_path):
        os.remove(zip_path)
        print(f"✅ Removed old {zip_path}")

    if os.path.exists(package_dir):
        shutil.rmtree(package_dir)
        print(f"✅ Removed old package directory")

    # Install dependencies
    print(f"\n📦 Installing dependencies...")
    subprocess.run([
        'pip', 'install',
        '-r', 'requirements.txt',
        '-t', package_dir,
        '--platform', 'manylinux2014_x86_64',
        '--only-binary=:all:'
    ], check=True)

    # Create ZIP file
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add dependencies
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, package_dir)
                zipf.write(file_path, arcname)

        # Add Lambda function files
        files_to_include = [
            'lambda_function.py',
            'elevenlabs_provider.py'
        ]

        for filename in files_to_include:
            file_path = os.path.join(lambda_dir, filename)
            if os.path.exists(file_path):
                zipf.write(file_path, filename)
                print(f"   ✅ Added {filename}")

    # Cleanup
    shutil.rmtree(package_dir)

    file_size = os.path.getsize(zip_path)
    print(f"\n✅ Created {zip_path}")
    print(f"   Size: {file_size / 1024 / 1024:.2f} MB")
    print(f"\n📝 Note: This Lambda requires:")
    print(f"   1. 'tts-common' Lambda Layer")
    print(f"   2. 'elevenlabs-api-key' in AWS Secrets Manager")

    return zip_path

if __name__ == '__main__':
    create_deployment_package()
