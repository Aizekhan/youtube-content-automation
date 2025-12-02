import json
import boto3
import http.client
from datetime import datetime
from boto3.dynamodb.conditions import Key
from botocore.config import Config

# WEEK 2 FIX: Add timeout configuration
boto_config = Config(
    connect_timeout=5,
    read_timeout=60,
    retries={'max_attempts': 3, 'mode': 'standard'}
)

secrets_client = boto3.client('secretsmanager', region_name='eu-central-1', config=boto_config)
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1', config=boto_config)

def lambda_handler(event, context):
    print(f"Theme Agent - AI Prompt Configs Version")
    print(f"Event: {json.dumps(event, ensure_ascii=False)}")

    channel_id = event.get('channel_id', 'Unknown')
    channel_name = event.get('channel_name', 'Unknown')
    input_titles = event.get('titles', [])
    topics_to_generate = event.get('topics_to_generate', 4)
    avoid_list = event.get('avoid_list', [])

    try:
        # 1. Отримуємо OpenAI API ключ
        api_key_response = secrets_client.get_secret_value(SecretId='openai/api-key')
        secret_string = api_key_response['SecretString']
        try:
            api_key_data = json.loads(secret_string)
            api_key = api_key_data.get('api_key') or api_key_data.get('key')
        except:
            api_key = secret_string

        print("✅ API key retrieved successfully")

        # 2. Отримуємо prompt config з AIPromptConfigs
        prompt_table = dynamodb.Table('AIPromptConfigs')
        prompt_response = prompt_table.get_item(Key={'agent_id': 'theme_agent'})

        if 'Item' not in prompt_response:
            raise Exception('Theme Agent config not found in AIPromptConfigs')

        prompt_config = prompt_response['Item']
        system_instructions = prompt_config['system_instructions']
        model = prompt_config.get('model', 'gpt-4o-mini')
        temperature = float(prompt_config.get('temperature', '0.9'))
        max_tokens = int(prompt_config.get('max_tokens', '500'))

        print(f"Prompt config loaded: model={model}, temp={temperature}")

        # 3. Отримуємо channel config з ChannelConfigs (query через GSI)
        channel_table = dynamodb.Table('ChannelConfigs')
        channel_response = channel_table.query(
            IndexName='channel_id-index',
            KeyConditionExpression=Key('channel_id').eq(channel_id)
        )

        if not channel_response.get('Items'):
            raise Exception(f'Channel config not found for {channel_id}')

        channel_config = channel_response['Items'][0]
        print(f"Channel config loaded for: {channel_config.get('channel_name', 'Unknown')}")

        # 4. Формуємо JSON input згідно з інструкцією Theme Agent
        user_input = {
            "channel_name": channel_config.get('channel_name', channel_name),
            "channel_config": {
                "genre": channel_config.get('genre', 'General'),
                "tone": channel_config.get('tone', 'Neutral'),
                "content_focus": channel_config.get('content_focus', ''),
                "narrative_keywords": channel_config.get('narrative_keywords', ''),
                "example_keywords_for_youtube": channel_config.get('example_keywords_for_youtube', '')
            },
            "topics_to_generate": topics_to_generate,
            "avoid_list": avoid_list + input_titles  # Додаємо input_titles до avoid_list
        }

        user_message = json.dumps(user_input, ensure_ascii=False)

        # 5. Prepare OpenAI request
        request_body = json.dumps({
            'model': model,
            'messages': [
                {'role': 'system', 'content': system_instructions},
                {'role': 'user', 'content': user_message}
            ],
            'temperature': temperature,
            'max_tokens': max_tokens,
            'response_format': {'type': 'json_object'}  # Force JSON output
        })

        # 6. Виклик OpenAI API
        # SECURITY FIX: Add SSL/TLS verification and timeout
        import ssl
        ssl_context = ssl.create_default_context()
        conn = http.client.HTTPSConnection('api.openai.com', context=ssl_context, timeout=60)
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        try:
            conn.request('POST', '/v1/chat/completions', body=request_body, headers=headers)
            response = conn.getresponse()
            response_data = response.read().decode('utf-8')
        finally:
            conn.close()  # Ensure connection is closed

        print(f"OpenAI response status: {response.status}")

        result = json.loads(response_data)

        if 'error' in result:
            raise Exception(f"OpenAI API Error: {result['error'].get('message', 'Unknown error')}")

        # 7. Parse JSON response
        generated_content = result['choices'][0]['message']['content']
        generated_json = json.loads(generated_content)

        generated_titles = generated_json.get('new_topics', [])

        print(f"Generated {len(generated_titles)} titles")

        # Fallback якщо менше ніж потрібно
        while len(generated_titles) < topics_to_generate:
            generated_titles.append(f"Theme #{len(generated_titles)+1}")

        # 8. Зберігаємо в DynamoDB GeneratedContent
        content_table = dynamodb.Table('GeneratedContent')
        timestamp = datetime.utcnow().isoformat() + 'Z'

        content_table.put_item(
            Item={
                'channel_id': channel_id,
                'created_at': timestamp,
                'type': 'theme_generation',
                'channel_name': channel_config.get('channel_name', channel_name),
                'genre': channel_config.get('genre', 'General'),
                'input_titles': input_titles,
                'generated_titles': generated_titles,
                'full_response': generated_json,
                'model': model,
                'api_version': 'responses_api',
                'prompt_version': prompt_config.get('version', '1.0'),
                'status': 'completed'
            }
        )

        print(f"✅ Saved to DynamoDB: {channel_id} at {timestamp}")

        # 9. Return output for Step Functions
        output = {
            'channel_id': channel_id,
            'channel_name': channel_config.get('channel_name', channel_name),
            'genre': channel_config.get('genre', 'General'),
            'generated_titles': generated_titles,
            'timestamp': timestamp
        }

        print(f"✅ Success! Generated: {json.dumps(output, ensure_ascii=False)}")
        return output

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

        # Fallback
        return {
            'channel_id': channel_id,
            'channel_name': channel_name,
            'genre': 'Unknown',
            'generated_titles': [f"Fallback theme {i+1}" for i in range(topics_to_generate)],
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'error': str(e)
        }
