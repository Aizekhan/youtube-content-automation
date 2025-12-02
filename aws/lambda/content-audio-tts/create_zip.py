import zipfile
import os

# Create zip file
with zipfile.ZipFile('function.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
    # Add lambda_function.py at root
    zipf.write('lambda_function.py', 'lambda_function.py')

    # Add ssml_generator.py at root (NEW!)
    zipf.write('ssml_generator.py', 'ssml_generator.py')

    # Add shared modules
    zipf.write('shared/config_merger.py', 'shared/config_merger.py')
    zipf.write('shared/ssml_validator.py', 'shared/ssml_validator.py')

print("Created function.zip with:")
print("   - lambda_function.py")
print("   - ssml_generator.py (NEW!)")
print("   - shared/config_merger.py")
print("   - shared/ssml_validator.py")

# Verify contents
with zipfile.ZipFile('function.zip', 'r') as zipf:
    print("\nZip contents:")
    for name in zipf.namelist():
        print(f"   {name}")
