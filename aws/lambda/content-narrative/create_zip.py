import zipfile
import os

# Path to parent shared directory
PARENT_SHARED = '../shared'

print("Creating deployment package...")

# Create zip file
with zipfile.ZipFile('function.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
    # Add lambda_function.py at root
    zipf.write('lambda_function.py', 'lambda_function.py')
    print("   Added lambda_function.py")

    # Add json_fixer.py at root
    zipf.write('json_fixer.py', 'json_fixer.py')
    print("   Added json_fixer.py")

    # Add all shared modules from PARENT shared directory (only existing files)
    shared_modules = [
        'config_merger.py',
        'mega_config_merger.py',
        'mega_prompt_builder.py',
        'response_extractor.py',
        'openai_cache.py'
    ]

    for module in shared_modules:
        source_path = f'{PARENT_SHARED}/{module}'
        if os.path.exists(source_path):
            zipf.write(source_path, f'shared/{module}')
            print(f"   Added shared/{module}")
        else:
            print(f"   WARNING: {module} not found at {source_path}")

print("\n✅ Created function.zip")

# Verify contents
with zipfile.ZipFile('function.zip', 'r') as zipf:
    print("\nZIP Contents:")
    for name in zipf.namelist():
        print(f"   {name}")
