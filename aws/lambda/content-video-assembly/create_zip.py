import zipfile
import os

os.chdir('E:/youtube-content-automation/aws/lambda/content-video-assembly')

with zipfile.ZipFile('function.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
    zipf.write('lambda_function.py', 'lambda_function.py')
    zipf.write('cta_video_creator.py', 'cta_video_creator.py')

print("Created function.zip with lambda_function.py and cta_video_creator.py")
