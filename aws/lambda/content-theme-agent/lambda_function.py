import json
import boto3
import urllib3
from datetime import datetime

secrets_client = boto3.client('secretsmanager', region_name='eu-central-1')
http = urllib3.PoolManager()

def lambda_handler(event, context):
    print(f"Theme Agent - OpenAI Version")
    print(f"Event: {json.dumps(event, ensure_ascii=False)}")
    
    channel_id = event.get('channel_id', 'Unknown')
    channel_name = event.get('channel_name', 'Unknown')
    genre = event.get('genre', 'General')
    input_titles = event.get('titles', [])
    
    try:
        # Отримуємо OpenAI API ключ
        try:
            secret_response = secrets_client.get_secret_value(SecretId='openai/api-key')
            secret_data = json.loads(secret_response['SecretString'])
            api_key = secret_data.get('api_key') or secret_data.get('key')
        except:
            # Пробуємо другий секрет
            secret_response = secrets_client.get_secret_value(SecretId='OPENAI_API_KEY')
            api_key = secret_response['SecretString']
        
        print(f"API key retrieved: {api_key[:10]}...")
        
        # Створюємо промпт
        prompt = f"""Ти - креативний генератор тем для YouTube каналу жанру "{genre}".

Згенеруй 4 унікальні, захоплюючі теми для відео.

Вимоги:
- Жанр: {genre}
- Формат: короткий заголовок (5-10 слів)
- Мова: українська
- Стиль: інтригуючий, що викликає цікавість

Базові ідеї: {', '.join(input_titles)}

Поверни тільки 4 заголовки, кожен з нового рядка, без нумерації."""

        # Виклик OpenAI API
        response = http.request(
            'POST',
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            body=json.dumps({
                'model': 'gpt-4o-mini',
                'messages': [
                    {'role': 'system', 'content': 'Ти - професійний креатор контенту для YouTube.'},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.9,
                'max_tokens': 500
            }).encode('utf-8')
        )
        
        result = json.loads(response.data.decode('utf-8'))
        print(f"OpenAI response: {result}")
        
        generated_text = result['choices'][0]['message']['content']
        generated_titles = [t.strip() for t in generated_text.strip().split('\n') if t.strip()]
        
        while len(generated_titles) < 4:
            generated_titles.append(f"Тема для {genre} #{len(generated_titles)+1}")
        
        output = {
            'channel_id': channel_id,
            'channel_name': channel_name,
            'genre': genre,
            'generated_titles': generated_titles[:4],
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        print(f"Success! Generated: {json.dumps(output, ensure_ascii=False)}")
        return output
        
    except Exception as e:
        print(f"Error: {str(e)}")
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
