import zipfile
import os

# Using relative path or current directory

with zipfile.ZipFile('function.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
    zipf.write('lambda_function.py', 'lambda_function.py')

print("Created function.zip with lambda_function.py")
