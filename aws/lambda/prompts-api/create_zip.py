#!/usr/bin/env python3
import zipfile
import os

def create_lambda_zip():
    zip_filename = 'function.zip'

    # Remove old zip if exists
    if os.path.exists(zip_filename):
        os.remove(zip_filename)

    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add main files
        for file in ['index.js', 'package.json']:
            if os.path.exists(file):
                print(f'Adding {file}')
                zipf.write(file, file)

        # Add node_modules
        for root, dirs, files in os.walk('node_modules'):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = file_path
                print(f'Adding {arcname}')
                zipf.write(file_path, arcname)

    size = os.path.getsize(zip_filename)
    print(f'\n✅ Created {zip_filename} ({size / 1024 / 1024:.2f} MB)')

if __name__ == '__main__':
    create_lambda_zip()
