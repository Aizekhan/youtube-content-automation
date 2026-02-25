#!/usr/bin/env python3
"""
Deploy content-narrative Lambda with Series Context integration
"""
import boto3
import os
import zipfile
import time

FUNCTION_NAME = 'content-narrative'
REGION = 'eu-central-1'

lambda_client = boto3.client('lambda', region_name=REGION)

print("="*80)
print("DEPLOYING content-narrative Lambda - Series Context Integration")
print("="*80)

# Package Lambda
lambda_dir = 'aws/lambda/content-narrative'
zip_path = 'content-narrative-deployment.zip'

print(f"\n1. Packaging Lambda from {lambda_dir}...")

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    files_added = 0
    for root, dirs, files in os.walk(lambda_dir):
        # Skip __pycache__ and test files
        dirs[:] = [d for d in dirs if d != '__pycache__']

        for file in files:
            if file.endswith('.pyc') or file.startswith('test_'):
                continue

            file_path = os.path.join(root, file)
            arcname = os.path.relpath(file_path, lambda_dir)
            zipf.write(file_path, arcname)
            files_added += 1

print(f"   [OK] Packaged {files_added} files")

# Get zip size
zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
print(f"   [OK] Package size: {zip_size_mb:.2f} MB")

# Deploy
print(f"\n2. Deploying to AWS Lambda ({FUNCTION_NAME})...")

with open(zip_path, 'rb') as f:
    zip_content = f.read()

try:
    response = lambda_client.update_function_code(
        FunctionName=FUNCTION_NAME,
        ZipFile=zip_content,
        Publish=True
    )

    version = response['Version']
    print(f"   [OK] Deployed version: {version}")
    print(f"   [OK] Code SHA256: {response['CodeSha256'][:16]}...")
    print(f"   [OK] Last modified: {response['LastModified']}")

except Exception as e:
    print(f"   [ERROR] Deployment failed: {e}")
    exit(1)

# Wait for update to complete
print(f"\n3. Waiting for Lambda update to complete...")
max_wait = 30
waited = 0

while waited < max_wait:
    time.sleep(2)
    waited += 2

    try:
        config = lambda_client.get_function_configuration(FunctionName=FUNCTION_NAME)
        state = config.get('State', 'Unknown')

        if state == 'Active':
            print(f"   [OK] Lambda is Active (waited {waited}s)")
            break
        else:
            print(f"   ... State: {state} (waited {waited}s)")
    except Exception as e:
        print(f"   ... Checking state: {e}")

# Cleanup
os.remove(zip_path)
print(f"\n4. Cleanup complete")

print("\n" + "="*80)
print("DEPLOYMENT SUMMARY")
print("="*80)
print(f"Function: {FUNCTION_NAME}")
print(f"Version: {version}")
print(f"Region: {REGION}")
print("\nChanges Deployed:")
print("  - Phase 1a: Series context section with 4 mandatory rules")
print("  - Phase 1b: Voice instructions with character voice tags")
print("  - Three-phase engine: series_context parameter flow")
print("  - Lambda handler: series_context extraction from event")
print("\nNew Features:")
print("  - Archetype repetition prevention")
print("  - Tension-based narrative pacing (1-10 scale)")
print("  - Plot thread development/resolution")
print("  - Character voice tag formatting for multi-speaker TTS")
print("="*80)
print("\nNext Steps:")
print("  1. Test with series episode: python test-get-next-series-context.py")
print("  2. Verify Phase 1a respects archetype restrictions")
print("  3. Verify Phase 1b generates voice tags: [NARRATOR], [CHARACTER_ID]")
print("="*80)
