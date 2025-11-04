import json
import boto3
import http.client
from datetime import datetime
from decimal import Decimal
from boto3.dynamodb.conditions import Key

secrets_client = boto3.client('secretsmanager', region_name='eu-central-1')
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
cost_table = dynamodb.Table('CostTracking')

# OpenAI Pricing (USD) - November 2025
OPENAI_PRICING = {
    'gpt-4o': {
        'input': 2.50 / 1_000_000,  # $2.50 per 1M input tokens
        'output': 10.00 / 1_000_000,  # $10.00 per 1M output tokens
    },
    'gpt-4o-mini': {
        'input': 0.150 / 1_000_000,
        'output': 0.600 / 1_000_000,
    }
}

def log_openai_cost(channel_id, content_id, model, input_tokens, output_tokens):
    """Log OpenAI API cost to CostTracking table"""
    try:
        # Get pricing for model
        model_key = model if model in OPENAI_PRICING else 'gpt-4o'
        pricing = OPENAI_PRICING[model_key]

        # Calculate cost
        input_cost = input_tokens * pricing['input']
        output_cost = output_tokens * pricing['output']
        total_cost = Decimal(str(input_cost + output_cost))

        # Log to CostTracking
        now = datetime.utcnow()
        date_str = now.strftime('%Y-%m-%d')
        timestamp = now.isoformat() + 'Z'

        cost_table.put_item(
            Item={
                'date': date_str,
                'timestamp': timestamp,
                'service': 'OpenAI',
                'operation': 'narrative_generation',
                'channel_id': channel_id,
                'content_id': content_id,
                'cost_usd': total_cost,
                'units': input_tokens + output_tokens,
                'details': {
                    'model': model,
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'input_cost_usd': round(input_cost, 6),
                    'output_cost_usd': round(output_cost, 6)
                }
            }
        )

        print(f"✅ Logged OpenAI cost: ${float(total_cost):.6f} ({input_tokens + output_tokens} tokens)")
        return float(total_cost)
    except Exception as e:
        print(f"❌ Failed to log cost: {str(e)}")
        return 0.0

def lambda_handler(event, context):
    print(f"Narrative Architect - AI Prompt Configs Version")
    print(f"Event: {json.dumps(event, ensure_ascii=False)}")

    channel_id = event.get('channel_id', 'Unknown')
    selected_topic = event.get('selected_topic', 'Default Topic')
    target_character_count = event.get('target_character_count', 8000)
    scene_count_target = event.get('scene_count_target', 18)

    try:
        # 1. Отримуємо OpenAI API ключ
        api_key_response = secrets_client.get_secret_value(SecretId='openai/api-key')
        secret_string = api_key_response['SecretString']
        try:
            api_key_data = json.loads(secret_string)
            api_key = api_key_data.get('api_key') or api_key_data.get('key')
        except:
            api_key = secret_string

        print(f"API key retrieved: {api_key[:10]}...")

        # 2. Отримуємо prompt config з AIPromptConfigs
        prompt_table = dynamodb.Table('AIPromptConfigs')
        prompt_response = prompt_table.get_item(Key={'agent_id': 'narrative_architect'})

        if 'Item' not in prompt_response:
            raise Exception('Narrative Architect config not found in AIPromptConfigs')

        prompt_config = prompt_response['Item']
        system_instructions = prompt_config['system_instructions']
        model = prompt_config.get('model', 'gpt-4o')
        temperature = float(prompt_config.get('temperature', '0.8'))
        max_tokens = int(prompt_config.get('max_tokens', '4000'))

        print(f"Prompt config loaded: model={model}, temp={temperature}, max_tokens={max_tokens}")

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

        # 4. Формуємо JSON input згідно з інструкцією Narrative Architect
        user_input = {
            "channel_name": channel_config.get('channel_name', 'Unknown Channel'),
            "channel_config": {
                "genre": channel_config.get('genre', 'General'),
                "tone": channel_config.get('tone', 'Neutral'),
                "narration_style": channel_config.get('narration_style', 'Third-person'),
                "narrative_pace": channel_config.get('narrative_pace', 'medium'),
                "story_structure_pattern": channel_config.get('story_structure_pattern', 'Intro – build – twist – resolution'),
                "content_focus": channel_config.get('content_focus', ''),
                "narrative_keywords": channel_config.get('narrative_keywords', ''),
                "visual_keywords": channel_config.get('visual_keywords', ''),
                "image_style_variants": channel_config.get('image_style_variants', 'Cinematic realistic'),
                "color_palettes": channel_config.get('color_palettes', 'Natural colors'),
                "lighting_variants": channel_config.get('lighting_variants', 'Natural lighting'),
                "composition_variants": channel_config.get('composition_variants', 'Standard composition'),
                "tts_voice_profile": channel_config.get('tts_voice_profile', 'neutral_male'),
                "tts_mood_tags": channel_config.get('tts_mood_tags', 'clear, steady'),
                "recommended_music_variants": channel_config.get('recommended_music_variants', 'Ambient background')
            },
            "topic": selected_topic,
            "target_character_count": target_character_count,
            "scene_count_target": scene_count_target
        }

        user_message = json.dumps(user_input, ensure_ascii=False)

        print(f"Request size: {len(user_message)} chars, topic: {selected_topic}")

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

        if 'error' in result:
            raise Exception(f"OpenAI API Error: {result['error'].get('message', 'Unknown error')}")

        # 7. Parse JSON response
        generated_content = result['choices'][0]['message']['content']
        narrative_json = json.loads(generated_content)

        # Extract key fields
        story_title = narrative_json.get('story_title', selected_topic)
        narrative_text = narrative_json.get('narrative_text', '')
        character_count = narrative_json.get('character_count', len(narrative_text))
        scenes = narrative_json.get('scenes', [])

        print(f"Generated: {len(scenes)} scenes, {character_count} characters")
        print(f"Story title: {story_title}")

        # 7.5. Extract usage and log cost
        usage = result.get('usage', {})
        input_tokens = usage.get('prompt_tokens', 0)
        output_tokens = usage.get('completion_tokens', 0)
        total_tokens = usage.get('total_tokens', input_tokens + output_tokens)

        print(f"Token usage: {input_tokens} input + {output_tokens} output = {total_tokens} total")

        # 8. Зберігаємо в DynamoDB GeneratedContent
        content_table = dynamodb.Table('GeneratedContent')
        timestamp = datetime.utcnow().isoformat() + 'Z'
        narrative_id = timestamp.replace(':', '').replace('-', '').replace('.', '')[:20]

        # Log cost
        cost_usd = log_openai_cost(
            channel_id=channel_id,
            content_id=narrative_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens
        )

        content_table.put_item(
            Item={
                'channel_id': channel_id,
                'created_at': timestamp,
                'type': 'narrative_generation',
                'topic': selected_topic,
                'story_title': story_title,
                'narrative_text': narrative_text,
                'character_count': character_count,
                'scene_count': len(scenes),
                'scenes': scenes,
                'full_response': narrative_json,
                'model': model,
                'api_version': 'responses_api',
                'prompt_version': prompt_config.get('version', '1.0'),
                'status': 'completed',
                'cost_usd': Decimal(str(cost_usd)),
                'tokens_used': total_tokens
            }
        )

        print(f"✅ Saved to DynamoDB: {channel_id} at {timestamp}")

        # 9. Return output for Step Functions

        output = {
            'channel_id': channel_id,
            'selected_topic': selected_topic,
            'story_title': story_title,
            'narrative_content': narrative_json,  # Full JSON response
            'narrative_id': narrative_id,  # For TTS Lambda
            'scenes': scenes,  # For TTS Lambda
            'character_count': character_count,
            'scene_count': len(scenes),
            'timestamp': timestamp
        }

        print(f"✅ Success! Narrative generated with {len(scenes)} scenes")
        return output

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

        # Fallback
        timestamp_err = datetime.utcnow().isoformat() + 'Z'
        narrative_id_err = timestamp_err.replace(':', '').replace('-', '').replace('.', '')[:20]

        fallback_narrative = f"""INTRO:
Welcome! Today we explore: {selected_topic}

MAIN:
[Generation error: {str(e)}]

CONCLUSION:
Thank you for watching! Subscribe for more content!"""

        return {
            'channel_id': channel_id,
            'selected_topic': selected_topic,
            'story_title': selected_topic,
            'narrative_content': fallback_narrative,
            'narrative_id': narrative_id_err,  # Required for TTS
            'scenes': [],  # Required for TTS (empty array)
            'character_count': len(fallback_narrative),
            'scene_count': 0,
            'timestamp': timestamp_err,
            'error': str(e)
        }
