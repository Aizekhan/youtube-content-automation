import zipfile
import os

# Path to parent shared directory
PARENT_SHARED = '../shared'

# Create zip file
with zipfile.ZipFile('function.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
    # Add lambda_function.py at root
    zipf.write('lambda_function.py', 'lambda_function.py')

    # Add json_fixer.py at root
    zipf.write('json_fixer.py', 'json_fixer.py')

    # Add all shared modules from PARENT shared directory
    zipf.write(f'{PARENT_SHARED}/config_merger.py', 'shared/config_merger.py')
    zipf.write(f'{PARENT_SHARED}/mega_config_merger.py', 'shared/mega_config_merger.py')
    zipf.write(f'{PARENT_SHARED}/mega_prompt_builder.py', 'shared/mega_prompt_builder.py')
    zipf.write(f'{PARENT_SHARED}/response_extractor.py', 'shared/response_extractor.py')
    zipf.write(f'{PARENT_SHARED}/input_size_validator.py', 'shared/input_size_validator.py')
    zipf.write(f'{PARENT_SHARED}/openai_cache.py', 'shared/openai_cache.py')

print("Created function.zip with:")
print("   - lambda_function.py")
print("   - json_fixer.py")
print("   - shared/config_merger.py")
print("   - shared/mega_config_merger.py")
print("   - shared/mega_prompt_builder.py")
print("   - shared/response_extractor.py")
print("   - shared/input_size_validator.py")
print("   - shared/openai_cache.py")

# Verify contents
with zipfile.ZipFile('function.zip', 'r') as zipf:
    print("\nZip contents:")
    for name in zipf.namelist():
        print(f"   {name}")
