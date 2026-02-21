"""
Content Context Enrichment Lambda
Sprint 2 - Task 2.3

Enriches story context with atmosphere, sensory details, and mood.
Uses OpenAI to generate comprehensive environmental context.
"""

import json
import boto3
import http.client

def get_openai_api_key():
    """Get OpenAI API key from Secrets Manager"""
    secrets_client = boto3.client('secretsmanager', region_name='eu-central-1')
    try:
        response = secrets_client.get_secret_value(SecretId='openai/api-key')
        secret_string = response['SecretString']
        try:
            secret = json.loads(secret_string)
            api_key = secret.get('OPENAI_API_KEY') or secret.get('api_key')
        except json.JSONDecodeError:
            api_key = secret_string
        if not api_key:
            raise ValueError("API key not found")
        return api_key
    except Exception as e:
        print(f"Error getting API key: {str(e)}")
        raise

def build_enrichment_prompt(topic_text, tone, genre, world_type):
    """Build prompt for context enrichment"""
    return f"""Analyze this story topic and generate rich environmental context:

TOPIC: "{topic_text}"
TONE: {tone}
GENRE: {genre}
WORLD TYPE: {world_type}

Generate comprehensive atmospheric and sensory context. Return ONLY valid JSON:

{{
  "atmosphere": {{
    "primary_mood": "one or two words describing dominant feeling",
    "sensory_palette": {{
      "visual": ["detail1", "detail2", "detail3"],
      "sound": ["sound1", "sound2", "sound3"],
      "tactile": ["feeling1", "feeling2", "feeling3"]
    }},
    "emotional_arc": "brief description of emotional journey"
  }},
  "setting_details": {{
    "primary_location": "where story takes place",
    "time_of_day": "when events occur",
    "weather_conditions": "atmospheric conditions",
    "isolation_level": "none/low/medium/high/extreme"
  }},
  "symbolic_elements": ["symbol1", "symbol2"]
}}

Focus on creating immersive, sensory-rich atmosphere that enhances the story."""

def enrich_context_with_ai(api_key, topic_text, tone, genre, world_type):
    """Use OpenAI to enrich context"""
    prompt = build_enrichment_prompt(topic_text, tone, genre, world_type)
    
    payload = {
        "model": "gpt-4",
        "messages": [
            {"role": "system", "content": "You are an expert at creating rich, atmospheric story environments. Return pure JSON without markdown."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 600
    }
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        conn = http.client.HTTPSConnection('api.openai.com', timeout=30)
        conn.request('POST', '/v1/chat/completions', json.dumps(payload), headers)
        response = conn.getresponse()
        response_data = json.loads(response.read().decode())
        conn.close()
        
        if response.status != 200:
            raise ValueError(f"OpenAI API error: {response_data}")
        
        enrichment_text = response_data['choices'][0]['message']['content'].strip()
        
        if enrichment_text.startswith('```'):
            enrichment_text = enrichment_text.split('```')[1]
            if enrichment_text.startswith('json'):
                enrichment_text = enrichment_text[4:]
            enrichment_text = enrichment_text.strip()
        
        enrichment = json.loads(enrichment_text)
        return enrichment
        
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {str(e)}")
        raise ValueError(f"Failed to parse AI response: {str(e)}")
    except Exception as e:
        print(f"OpenAI API error: {str(e)}")
        raise

def lambda_handler(event, context):
    """Main handler for context enrichment"""
    print(f"Event: {json.dumps(event)}")
    
    try:
        topic_text = event.get('topic_text')
        tone = event.get('tone_suggestion', 'dark')
        genre = event.get('genre', 'mystery')
        world_type = event.get('world_type', 'realistic')
        
        if not topic_text:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'success': False, 'error': 'topic_text required'})
            }
        
        api_key = get_openai_api_key()
        enrichment = enrich_context_with_ai(api_key, topic_text, tone, genre, world_type)
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'success': True,
                'enriched_context': enrichment,
                'topic_analyzed': topic_text
            })
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'success': False, 'error': f'Failed: {str(e)}'})
        }
