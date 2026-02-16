import zipfile
import os

def create_zip():
    zip_file = 'function.zip'
    if os.path.exists(zip_file):
        os.remove(zip_file)

    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add lambda function
        zf.write('lambda_function.py')
        
        # Add all dependencies
        for root, dirs, files in os.walk('.'):
            # Skip hidden dirs, __pycache__, and dist-info
            if root.startswith('./.') or '__pycache__' in root or 'dist-info' in root:
                continue
            if root == '.':
                continue
                
            for file in files:
                if file.endswith('.py') or file.endswith('.so') or file.endswith('.pyd'):
                    file_path = os.path.join(root, file)
                    arcname = file_path[2:]  # Remove './'
                    zf.write(file_path, arcname)
        
        print(f"Created {zip_file}")

if __name__ == '__main__':
    create_zip()
