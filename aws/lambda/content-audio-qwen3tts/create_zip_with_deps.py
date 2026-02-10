import zipfile
import os

zip_file = 'function.zip'
if os.path.exists(zip_file):
    os.remove(zip_file)

with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
    # Add lambda function
    zf.write('lambda_function.py')
    
    # Add requests and dependencies
    for lib in ['requests', 'urllib3', 'certifi', 'charset_normalizer', 'idna']:
        if os.path.exists(lib):
            for root, dirs, files in os.walk(lib):
                for file in files:
                    file_path = os.path.join(root, file)
                    zf.write(file_path)

print(f"Created {zip_file} with requests library")
size_mb = os.path.getsize(zip_file) / 1024 / 1024
print(f"Size: {size_mb:.2f} MB")
