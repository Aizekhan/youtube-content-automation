import zipfile
import os

# Create zip file
with zipfile.ZipFile('function.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
    # Add lambda_function.py at root
    zipf.write('lambda_function.py', 'lambda_function.py')

    # Add shared modules
    zipf.write('shared/config_merger.py', 'shared/config_merger.py')
    zipf.write('shared/pipeline_helpers.py', 'shared/pipeline_helpers.py')
    zipf.write('shared/input_size_validator.py', 'shared/input_size_validator.py')

print("Created function.zip with:")
print("   - lambda_function.py")
print("   - shared/config_merger.py")
print("   - shared/pipeline_helpers.py")
print("   - shared/input_size_validator.py")

# Verify contents
with zipfile.ZipFile('function.zip', 'r') as zipf:
    print("\nZip contents:")
    for name in zipf.namelist():
        print(f"   {name}")
