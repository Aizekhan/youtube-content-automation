#!/usr/bin/env python3
import zipfile
import os
import sys

def create_lambda_zip(source_dir, output_zip):
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # Skip __pycache__
            if '__pycache__' in root:
                continue

            for file in files:
                if file.endswith('.pyc'):
                    continue

                file_path = os.path.join(root, file)
                # Calculate relative path from source_dir
                arcname = os.path.relpath(file_path, source_dir)
                zipf.write(file_path, arcname)
                print(f'Added: {arcname}')

    print(f'\nZIP created: {output_zip}')
    print(f'Size: {os.path.getsize(output_zip)} bytes')

if __name__ == '__main__':
    source = sys.argv[1] if len(sys.argv) > 1 else 'aws/lambda/content-generate-images'
    output = sys.argv[2] if len(sys.argv) > 2 else 'C:/Temp/lambda.zip'
    create_lambda_zip(source, output)
