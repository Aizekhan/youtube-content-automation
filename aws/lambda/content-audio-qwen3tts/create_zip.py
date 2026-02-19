#!/usr/bin/env python3
"""
Create deployment package for content-audio-qwen3tts Lambda
"""
import zipfile
import os

def create_zip():
    zip_file = 'function.zip'

    # Remove old zip
    if os.path.exists(zip_file):
        os.remove(zip_file)

    # Create new zip
    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add lambda function
        zf.write('lambda_function.py')

        print(f"[OK] Created {zip_file}")
        print(f"   - lambda_function.py")

    # Print file size
    size_mb = os.path.getsize(zip_file) / 1024 / 1024
    print(f"\n Package size: {size_mb:.2f} MB")

    print("\n Deploy with:")
    print(f"   aws lambda update-function-code --function-name content-audio-qwen3tts --zip-file fileb://{zip_file}")

if __name__ == '__main__':
    create_zip()
