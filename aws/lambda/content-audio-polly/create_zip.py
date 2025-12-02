#!/usr/bin/env python3
"""
Create deployment package for content-audio-polly Lambda
Uses Lambda Layer for shared code - minimal package size
"""

import os
import zipfile
import shutil

def create_deployment_package():
    """Create ZIP file for Lambda deployment"""

    lambda_dir = os.path.dirname(os.path.abspath(__file__))
    zip_path = os.path.join(lambda_dir, 'function.zip')

    # Remove old ZIP if exists
    if os.path.exists(zip_path):
        os.remove(zip_path)
        print(f"✅ Removed old {zip_path}")

    # Create ZIP file
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add Lambda function files
        files_to_include = [
            'lambda_function.py',
            'polly_provider.py'
        ]

        for filename in files_to_include:
            file_path = os.path.join(lambda_dir, filename)
            if os.path.exists(file_path):
                zipf.write(file_path, filename)
                print(f"   ✅ Added {filename}")
            else:
                print(f"   ⚠️  {filename} not found")

    file_size = os.path.getsize(zip_path)
    print(f"\n✅ Created {zip_path}")
    print(f"   Size: {file_size / 1024:.2f} KB")
    print(f"\n📝 Note: This Lambda requires 'tts-common' Lambda Layer")
    print(f"   Deploy the layer first: aws/lambda-layers/tts-common/")

    return zip_path

if __name__ == '__main__':
    create_deployment_package()
