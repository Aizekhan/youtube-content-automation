#!/usr/bin/env python3
"""
Create deployment package for content-topics-list Lambda
"""

import zipfile
import os

def create_deployment_package():
    """Create ZIP file for Lambda deployment"""

    print("Creating deployment package...")

    with zipfile.ZipFile('function.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add lambda_function.py
        zipf.write('lambda_function.py', 'lambda_function.py')
        print("   Added lambda_function.py")

    print("\nCreated function.zip")

    # Show ZIP contents
    print("\nZIP Contents:")
    with zipfile.ZipFile('function.zip', 'r') as zipf:
        for file in zipf.namelist():
            print(f"   {file}")

    print(f"\nZIP size: {os.path.getsize('function.zip')} bytes")

if __name__ == '__main__':
    create_deployment_package()
