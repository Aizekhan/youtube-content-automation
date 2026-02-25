#!/usr/bin/env python3
"""
Deploy ONLY mega_config_merger.py changes to content-narrative Lambda
WITHOUT touching mega_prompt_builder.py
"""

import boto3
import zipfile
import io
import os

# Download current Lambda code
lambda_client = boto3.client('lambda', region_name='eu-central-1')

print("Downloading current Lambda code...")
response = lambda_client.get_function(FunctionName='content-narrative')
code_url = response['Code']['Location']

import urllib.request
current_zip_data = urllib.request.urlopen(code_url).read()

print(f"Downloaded {len(current_zip_data)} bytes")

# Extract current ZIP
current_zip = zipfile.ZipFile(io.BytesIO(current_zip_data))

# Create new ZIP with updated mega_config_merger.py
new_zip_buffer = io.BytesIO()
new_zip = zipfile.ZipFile(new_zip_buffer, 'w', zipfile.ZIP_DEFLATED)

# Copy all files from current ZIP EXCEPT mega_config_merger.py
for item in current_zip.namelist():
    if item == 'shared/mega_config_merger.py':
        print(f"Skipping {item} (will be replaced)")
        continue
    data = current_zip.read(item)
    new_zip.writestr(item, data)
    print(f"Copied {item}")

# Add NEW mega_config_merger.py from local
local_path = 'E:/youtube-content-automation/aws/lambda/content-narrative/shared/mega_config_merger.py'
with open(local_path, 'r', encoding='utf-8') as f:
    new_config_merger = f.read()

new_zip.writestr('shared/mega_config_merger.py', new_config_merger)
print(f"Added NEW shared/mega_config_merger.py ({len(new_config_merger)} bytes)")

new_zip.close()

# Deploy
zip_data = new_zip_buffer.getvalue()
print(f"\nDeploying {len(zip_data)} bytes...")

response = lambda_client.update_function_code(
    FunctionName='content-narrative',
    ZipFile=zip_data
)

print(f"✓ Deployed: {response['LastModified']} - {response['CodeSize']} bytes")
