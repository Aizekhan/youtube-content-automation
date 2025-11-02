import json
import boto3
import http.client
from datetime import datetime

secrets_client = boto3.client('secretsmanager', region_name='eu-central-1')
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')

def lambda_handler(event, context):
    print(f"Narrative Architect - Responses API Version")
    print(f"Event: {json.dumps(event, ensure_ascii=False)}")

    channel_id = event.get('channel_id', 'Unknown')
    selected_topic = event.get('selected_topic', 'Default Topic')

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
        system_prompt = """Ти - професійний сценарист для YouTube відео.
Твоя задача - створювати детальні, захоплюючі сценарії для відео.

Вимоги до сценарію:
- Структура: Вступ (hook) → Основна частина → Висновок
- Мова: жива, захоплююча українська
- Стиль: розмовний, дружній
- Довжина: детальний сценарій на 5-8 хвилин відео
- Включати: факти, цікаві деталі, заклик до дії"""

        # Створюємо user message
        user_message = f"""Тема для відео: {selected_topic}

Створи детальний сценарій для YouTube відео на цю тему.

Сценарій має включати:
1. ВСТУП (30 сек):
   - Захоплюючий hook
   - Короткий анонс теми

2. ОСНОВНА ЧАСТИНА (4-6 хв):
   - Ключові моменти теми
   - Цікаві факти та деталі
   - Практичні поради або інсайти

3. ВИСНОВОК (30-60 сек):
   - Підсумок основних ідей
   - Заклик до дії (підписатись, лайк, коментар)

Використовуй живу, захоплюючу мову українською."""

        # Prepare request body
        request_body = json.dumps({
            'model': 'gpt-4o-mini',
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_message}
            ],
            'temperature': 0.8,
            'max_tokens': 2000
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

        result = json.loads(response_data)

        # Перевірка на помилки
        if 'error' in result:
            raise Exception(f"OpenAI API Error: {result['error'].get('message', 'Unknown error')}")

        narrative_content = result['choices'][0]['message']['content']
        print(f"Generated narrative length: {len(narrative_content)} characters")

        # Зберігаємо в DynamoDB
        table = dynamodb.Table('GeneratedContent')
        timestamp = datetime.utcnow().isoformat() + 'Z'

        table.put_item(
            Item={
                'channel_id': channel_id,
                'created_at': timestamp,
                'type': 'narrative_generation',
                'topic': selected_topic,
                'narrative_content': narrative_content,
                'model': 'gpt-4o-mini',
                'api_version': 'responses_api',
                'status': 'completed'
            }
        )

        print(f"✅ Saved to DynamoDB: {channel_id} at {timestamp}")

        result = {
            'channel_id': channel_id,
            'selected_topic': selected_topic,
            'narrative_content': narrative_content,
            'timestamp': timestamp
        }

        print(f"✅ Success! Narrative generated ({len(narrative_content)} chars)")
        return result

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

        # Fallback
        fallback_narrative = f"""ВСТУП:
Привіт! Сьогодні говоримо про {selected_topic}. Це дуже цікава тема!

ОСНОВНА ЧАСТИНА:
[Помилка генерації: {str(e)}]

ВИСНОВОК:
Дякую за перегляд! Підписуйтесь на канал!"""

        return {
            'channel_id': channel_id,
            'selected_topic': selected_topic,
            'narrative_content': fallback_narrative,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'error': str(e)
        }
