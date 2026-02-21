#!/usr/bin/env python3
import zipfile
import os

print("Creating deployment package...")
with zipfile.ZipFile('function.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
    zipf.write('lambda_function.py', 'lambda_function.py')
    print("   Added lambda_function.py")
print(f"\nCreated function.zip ({os.path.getsize('function.zip')} bytes)")
