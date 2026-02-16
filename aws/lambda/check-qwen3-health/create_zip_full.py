import zipfile
import os

# Create a ZIP file with lambda function and all dependencies
with zipfile.ZipFile('function.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
    # Add the Lambda function
    zipf.write('lambda_function.py')

    # Add all dependency directories
    for root, dirs, files in os.walk('.'):
        # Skip the current directory, .git, and __pycache__
        if root == '.' or '.git' in root or '__pycache__' in root or 'function.zip' in root:
            continue
        for file in files:
            file_path = os.path.join(root, file)
            arcname = file_path[2:]  # Remove './' prefix
            zipf.write(file_path, arcname)

print("Created function.zip with all dependencies")
print(f"Size: {os.path.getsize('function.zip')} bytes")
