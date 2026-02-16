import zipfile
import os

# Create a ZIP file with lambda function only (no dependencies)
with zipfile.ZipFile('function.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
    zipf.write('lambda_function.py')

print("Created function.zip")
print(f"Size: {os.path.getsize('function.zip')} bytes")
