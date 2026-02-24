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


    # Add all shared modules from LOCAL shared directory (Three Phase Engine)
    shared_modules = [
        'archetype_mechanics.py',
        'three_phase_engine.py',
        'openai_cache.py',
        'response_extractor.py'
    ]

    for module in shared_modules:
        source_path = f'shared/{module}'
        if os.path.exists(source_path):
            zipf.write(source_path, f'shared/{module}')
            print(f"   Added shared/{module}")
        else:
            print(f"   WARNING: {module} not found at {source_path}")

    # Add story_prompts directory
    story_prompts = [
        'phase1a-story-mechanics.txt',
        'phase1b-narrative-generation.txt',
        'phase1c-prompts-generation.txt'
    ]

    for prompt_file in story_prompts:
        source_path = f'story_prompts/{prompt_file}'
        if os.path.exists(source_path):
            zipf.write(source_path, f'story_prompts/{prompt_file}')
            print(f"   Added story_prompts/{prompt_file}")
        else:
            print(f"   WARNING: {prompt_file} not found at {source_path}")

print("\n Created function.zip")

# Verify contents
with zipfile.ZipFile('function.zip', 'r') as zipf:
    print("\nZIP Contents:")
    for name in zipf.namelist():
        print(f"   {name}")
