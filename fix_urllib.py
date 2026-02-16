#!/usr/bin/env python3
"""
Fix urllib usage in content-audio-qwen3tts Lambda function
"""
import re

# Read the file
with open('aws/lambda/content-audio-qwen3tts/lambda_function.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix check_service_health function
old_check_health = '''def check_service_health(endpoint):
    """Check if Qwen3-TTS service is healthy"""
    try:
        health_url = f"{endpoint}/health"
        req = urllib.request.Request(health_url, timeout=5)

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

# Fix generate_with_qwen3 POST request
old_generate = '''        print(f"Calling Qwen3-TTS API: {url}")

        req = urllib.request.Request(url, json=payload, timeout=120)

        if response.status_code != 200:
            raise Exception(f"Qwen3-TTS API error: {response.status_code} - {response.text}")

        result = response.json()'''

new_generate = '''        print(f"Calling Qwen3-TTS API: {url}")

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'}, method='POST')

        with urllib.request.urlopen(req, timeout=120) as response:
            if response.status != 200:
                error_text = response.read().decode('utf-8')
                raise Exception(f"Qwen3-TTS API error: {response.status} - {error_text}")

            result = json.loads(response.read().decode('utf-8'))'''

# Replace
content = content.replace(old_check_health, new_check_health)
content = content.replace(old_generate, new_generate)

# Write back
with open('aws/lambda/content-audio-qwen3tts/lambda_function.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Fixed urllib usage!")
print("✅ check_service_health - використовує urllib.request.urlopen з контекстним менеджером")
print("✅ generate_with_qwen3 - використовує urllib.request.urlopen для POST з JSON")
