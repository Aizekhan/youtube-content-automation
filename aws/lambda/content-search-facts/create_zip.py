import zipfile
import os

print("Creating deployment package for content-search-facts...")

with zipfile.ZipFile('function.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
    zipf.write('lambda_function.py', 'lambda_function.py')
    print("   Added lambda_function.py")

# Verify
with zipfile.ZipFile('function.zip', 'r') as zipf:
    print("\nZIP Contents:")
    for name in zipf.namelist():
        print(f"   {name}")

print("\nDone: function.zip")
