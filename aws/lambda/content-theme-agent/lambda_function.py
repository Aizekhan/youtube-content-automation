import json
import boto3
import http.client
from datetime import datetime

secrets_client = boto3.client('secretsmanager', region_name='eu-central-1')
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')

def lambda_handler(event, context):
    print(f"Theme Agent - Responses API Version")
    print(f"Event: {json.dumps(event, ensure_ascii=False)}")

    channel_id = event.get('channel_id', 'Unknown')
    channel_name = event.get('channel_name', 'Unknown')
    genre = event.get('genre', 'General')
    input_titles = event.get('titles', [])

    try:
        # Отримуємо OpenAI API ключ
        api_key_response = secrets_client.get_secret_value(SecretId='openai/api-key')
        secret_string = api_key_response['SecretString']

        # Перевіряємо чи це JSON чи plain string
        try:
            api_key_data = json.loads(secret_string)
            api_key = api_key_data.get('api_key') or api_key_data.get('key')
        except:
            # Якщо не JSON - це plain string API key
            api_key = secret_string

        print(f"API key retrieved: {api_key[:10]}...")

        # Створюємо system prompt (інструкції для моделі)
        system_prompt = """Ти - професійний креатор контенту для YouTube каналів.
Твоя задача - генерувати унікальні, захоплюючі теми для відео.

Вимоги до тем:
- Формат: короткий заголовок (5-10 слів)
- Мова: українська
- Стиль: інтригуючий, що викликає цікавість
- Теми мають бути актуальними та цікавими для глядачів"""

        # Створюємо user message
        user_message = f"""Жанр каналу: {genre}
Назва каналу: {channel_name}

Базові ідеї з попередніх відео:
{chr(10).join(['- ' + title for title in input_titles])}

Згенеруй РІВНО 4 унікальні теми для нових відео в цьому жанрі.
Поверни тільки 4 заголовки, кожен з нового рядка, БЕЗ нумерації."""

        # Prepare request body
        request_body = json.dumps({
            'model': 'gpt-4o-mini',
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_message}
            ],
            'temperature': 0.9,
            'max_tokens': 500
        })

        # Виклик OpenAI API через http.client
        conn = http.client.HTTPSConnection('api.openai.com')
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        conn.request('POST', '/v1/chat/completions', body=request_body, headers=headers)
        response = conn.getresponse()
        response_data = response.read().decode('utf-8')

        print(f"OpenAI response status: {response.status}")
        print(f"Response data preview: {response_data[:200]}...")

        result = json.loads(response_data)

        # Перевірка на помилки
        if 'error' in result:
            raise Exception(f"OpenAI API Error: {result['error'].get('message', 'Unknown error')}")

        generated_text = result['choices'][0]['message']['content']
        print(f"Generated text: {generated_text[:100]}...")

        # Парсимо відповідь (очікуємо 4 теми, кожна з нового рядка)
        generated_titles = [t.strip().lstrip('0123456789.-) ') for t in generated_text.strip().split('\n') if t.strip()]
        generated_titles = [t for t in generated_titles if t and len(t) > 3][:4]

        # Якщо менше 4 тем, додаємо fallback
        while len(generated_titles) < 4:
            generated_titles.append(f"Тема для {genre} #{len(generated_titles)+1}")

        # Зберігаємо в DynamoDB
        table = dynamodb.Table('GeneratedContent')
        timestamp = datetime.utcnow().isoformat() + 'Z'

        table.put_item(
            Item={
                'channel_id': channel_id,
                'created_at': timestamp,
                'type': 'theme_generation',
                'channel_name': channel_name,
                'genre': genre,
                'input_titles': input_titles,
                'generated_titles': generated_titles,
                'model': 'gpt-4o-mini',
                'api_version': 'responses_api',
                'status': 'completed'
            }
        )

        print(f"✅ Saved to DynamoDB: {channel_id} at {timestamp}")

        output = {
            'channel_id': channel_id,
            'channel_name': channel_name,
            'genre': genre,
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
            'genre': genre,
            'generated_titles': [
                f"Fallback тема 1 для {genre}",
                f"Fallback тема 2 для {genre}",
                f"Fallback тема 3 для {genre}",
                f"Fallback тема 4 для {genre}"
            ],
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'error': str(e)
        }
