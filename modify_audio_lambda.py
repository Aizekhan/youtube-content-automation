#!/usr/bin/env python3
"""
Add parallel batching to content-audio-qwen3tts Lambda:
1. Replace requests with urllib.request
2. Add concurrent.futures for parallel processing
3. Replace sequential loop with ThreadPoolExecutor
"""
import re

def modify_lambda():
    filepath = 'E:/youtube-content-automation/aws/lambda/content-audio-qwen3tts/lambda_function.py'

    # Read the file
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Replace imports
    content = content.replace(
        'import requests',
        'import urllib.request\nimport urllib.parse'
    )

    content = content.replace(
        'from boto3.dynamodb.conditions import Key',
        'from boto3.dynamodb.conditions import Key\nfrom concurrent.futures import ThreadPoolExecutor, as_completed'
    )

    # 2. Replace check_service_health function (requests → urllib)
    old_check_health = '''def check_service_health(endpoint):
    """Check if Qwen3-TTS service is healthy"""
    try:
        health_url = f"{endpoint}/health"
        response = requests.get(health_url, timeout=5)

        if response.status_code == 200:
            data = response.json()
            models_loaded = data.get('models_loaded', 0)
            return models_loaded >= 3

        return False

    except Exception as e:
        return False'''

    new_check_health = '''def check_service_health(endpoint):
    """Check if Qwen3-TTS service is healthy"""
    try:
        health_url = f"{endpoint}/health"
        req = urllib.request.Request(health_url, method='GET')

        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                models_loaded = data.get('models_loaded', 0)
                return models_loaded >= 3

        return False

    except Exception as e:
        return False'''

    content = content.replace(old_check_health, new_check_health)

    # 3. Replace generate_with_qwen3 HTTP call (requests → urllib)
    old_http = '''        print(f"Calling Qwen3-TTS API: {url}")

        response = requests.post(url, json=payload, timeout=120)

        if response.status_code != 200:
            raise Exception(f"Qwen3-TTS API error: {response.status_code} - {response.text}")

        result = response.json()'''

    new_http = '''        print(f"Calling Qwen3-TTS API: {url}")

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')

        with urllib.request.urlopen(req, timeout=120) as response:
            if response.status != 200:
                error_text = response.read().decode('utf-8')
                raise Exception(f"Qwen3-TTS API error: {response.status} - {error_text}")

            result = json.loads(response.read().decode('utf-8'))'''

    content = content.replace(old_http, new_http)

    # 4. Add process_single_scene worker function before lambda_handler
    worker_function = '''

def process_single_scene(scene, ec2_endpoint, channel_id, narrative_id, language, speaker, voice_description):
    """
    Worker function to process a single scene in parallel

    Returns: (scene_id, audio_file_dict) or (scene_id, None) on error
    """
    scene_id = scene.get('id') or scene.get('scene_number', 0)

    # Get text - prefer plain text over SSML for Qwen3-TTS
    text = scene.get('scene_narration') or scene.get('text', '')

    # Strip SSML tags if present (Qwen3 uses plain text)
    if not text and 'text_with_ssml' in scene:
        import re
        text = re.sub(r'<[^>]+>', '', scene['text_with_ssml'])

    if not text:
        print(f"⚠️ Scene {scene_id} has no text, skipping")
        return (scene_id, None)

    print(f"Generating audio for scene {scene_id}...")

    try:
        # Call Qwen3-TTS API on EC2
        audio_data, duration_ms = generate_with_qwen3(
            ec2_endpoint=ec2_endpoint,
            text=text,
            language=language,
            speaker=speaker,
            voice_description=voice_description
        )

        # Upload to S3
        s3_key = f"narratives/{channel_id}/{narrative_id}/scene_{scene_id}.wav"
        s3_url = upload_to_s3(audio_data, s3_key, content_type='audio/wav')

        audio_file = {
            'scene_id': scene_id,
            's3_url': s3_url,
            's3_key': s3_key,
            'duration_ms': duration_ms
        }

        print(f"✅ Scene {scene_id} audio generated: {duration_ms}ms")
        return (scene_id, audio_file)

    except Exception as scene_error:
        print(f"❌ Error generating scene {scene_id}: {scene_error}")
        return (scene_id, None)


'''

    # Insert worker function before lambda_handler
    content = content.replace('def lambda_handler(event, context):', worker_function + 'def lambda_handler(event, context):')

    # 5. Replace sequential loop with parallel processing
    old_loop = '''        # 2. Generate audio for each scene
        audio_files = []
        generation_start = datetime.utcnow()

        for scene in scenes:
            scene_id = scene.get('id') or scene.get('scene_number', 0)

            # Get text - prefer plain text over SSML for Qwen3-TTS
            text = scene.get('scene_narration') or scene.get('text', '')

            # Strip SSML tags if present (Qwen3 uses plain text)
            if not text and 'text_with_ssml' in scene:
                import re
                text = re.sub(r'<[^>]+>', '', scene['text_with_ssml'])

            if not text:
                print(f"⚠️ Scene {scene_id} has no text, skipping")
                continue

            print(f"Generating audio for scene {scene_id}...")

            try:
                # Call Qwen3-TTS API on EC2
                audio_data, duration_ms = generate_with_qwen3(
                    ec2_endpoint=ec2_endpoint,
                    text=text,
                    language=language,
                    speaker=speaker,
                    voice_description=voice_description
                )

                # Upload to S3
                s3_key = f"narratives/{channel_id}/{narrative_id}/scene_{scene_id}.wav"
                s3_url = upload_to_s3(audio_data, s3_key, content_type='audio/wav')

                audio_files.append({
                    'scene_id': scene_id,
                    's3_url': s3_url,
                    's3_key': s3_key,
                    'duration_ms': duration_ms
                })

                print(f"✅ Scene {scene_id} audio generated: {duration_ms}ms")

            except Exception as scene_error:
                print(f"❌ Error generating scene {scene_id}: {scene_error}")
                continue'''

    new_loop = '''        # 2. Generate audio for each scene (PARALLEL)
        audio_files = []
        generation_start = datetime.utcnow()

        # Use ThreadPoolExecutor for parallel generation
        max_workers = min(8, len(scenes))  # Max 8 concurrent requests
        print(f"🚀 Generating audio for {len(scenes)} scenes with {max_workers} parallel workers...")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all scenes for processing
            future_to_scene = {
                executor.submit(
                    process_single_scene,
                    scene,
                    ec2_endpoint,
                    channel_id,
                    narrative_id,
                    language,
                    speaker,
                    voice_description
                ): scene for scene in scenes
            }

            # Collect results as they complete
            for future in as_completed(future_to_scene):
                try:
                    scene_id, audio_file = future.result()
                    if audio_file:
                        audio_files.append(audio_file)
                except Exception as exc:
                    print(f"❌ Scene processing exception: {exc}")

        print(f"✅ Parallel generation complete: {len(audio_files)}/{len(scenes)} scenes successful")'''

    content = content.replace(old_loop, new_loop)

    # Write the modified file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print("✅ Successfully modified lambda_function.py:")
    print("  - Replaced requests with urllib.request")
    print("  - Added concurrent.futures for parallel processing")
    print("  - Replaced sequential loop with ThreadPoolExecutor")
    print(f"  - File: {filepath}")

if __name__ == '__main__':
    modify_lambda()
