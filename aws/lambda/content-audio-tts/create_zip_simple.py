import zipfile
import os

zip_file = 'function.zip'
if os.path.exists(zip_file):
    os.remove(zip_file)

with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
    zf.write('lambda_function.py')

print(f"Created {zip_file} (simplified, no shared)")
