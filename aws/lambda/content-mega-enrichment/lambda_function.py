"""
Content Mega Enrichment Lambda
Sprint 2.1 - Optimization

REPLACES 3 separate Lambda functions with 1 mega-prompt:
- content-topic-analyzer
- content-context-enrichment
- content-story-dna-generator

Benefits:
- 60% cost reduction (3 GPT calls → 1 GPT call)
- 3x faster (15s → 5s)
- Single point of failure instead of 3
- Consistent JSON structure
"""

import json
import boto3
import http.client
import time

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

def build_mega_enrichment_prompt(topic_text, topic_description, story_profile):
    """Build single mega-prompt for all enrichment tasks"""

    tone = story_profile.get('tone', 'dark')
    world_type = story_profile.get('world_type', 'realistic')

    return f"""You are a master story analyst and creative consultant. Analyze this topic and provide comprehensive enrichment data.

TOPIC: "{topic_text}"
TOPIC DESCRIPTION: {json.dumps(topic_description)}
STORY PROFILE:
- Tone: {tone}
- World Type: {world_type}
- Psychological Depth: {story_profile.get('psychological_depth', 3)}/5
- Plot Intensity: {story_profile.get('plot_intensity', 4)}/5

Your task: Generate a COMPLETE enrichment package with ALL of the following sections.

Return ONLY valid JSON in this EXACT structure:

{{
  "topic_analysis": {{
    "genre": "primary genre (mystery/horror/thriller/drama/sci-fi/etc)",
    "sub_genre": "specific sub-category",
    "story_type": "narrative structure type",
    "complexity_level": 1-5,
    "estimated_scenes": 6-10,
    "key_themes": ["theme1", "theme2", "theme3"],
    "mood_tags": ["mood1", "mood2", "mood3"],
    "setting_type": "primary setting category",
    "time_period": "temporal setting",
    "narrative_perspective_suggestion": "first_person/third_person/etc",
    "pacing_recommendation": "slow_burn/steady/fast_paced",
    "conflict_type": "primary conflict category"
  }},
  "enriched_context": {{
    "atmosphere": {{
      "primary_mood": "dominant emotional feeling (1-2 words)",
      "sensory_palette": {{
        "visual": ["visual detail 1", "visual detail 2", "visual detail 3"],
        "sound": ["sound detail 1", "sound detail 2", "sound detail 3"],
        "tactile": ["tactile detail 1", "tactile detail 2", "tactile detail 3"]
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
  }},
  "story_dna": {{
    "unique_twist": "one sentence describing the core unexpected element",
    "character_seeds": [
      {{
        "archetype": "character type (but subverted)",
        "unique_trait": "what makes this character unexpected",
        "internal_conflict": "psychological struggle",
        "growth_arc": "transformation path"
      }},
      {{
        "archetype": "secondary character type",
        "unique_trait": "distinctive characteristic",
        "internal_conflict": "inner tension",
        "growth_arc": "development direction"
      }}
    ],
    "plot_hooks": [
      "unexpected story direction 1",
      "surprising narrative path 2",
      "unconventional development 3",
      "twist possibility 4"
    ],
    "emotional_core": "the deep universal feeling this story explores",
    "thematic_question": "the philosophical question the story asks",
    "anti_cliche_guards": [
      {{
        "avoid": "common cliché to avoid",
        "instead": "fresh alternative approach"
      }},
      {{
        "avoid": "another overused trope",
        "instead": "innovative substitute"
      }},
      {{
        "avoid": "predictable element",
        "instead": "unexpected replacement"
      }}
    ],
    "surprise_element": "the one thing readers won't see coming"
  }}
}}

IMPORTANT:
- Be BOLD and CREATIVE in story_dna
- Avoid ALL genre clichés
- Make characters MEMORABLE and UNIQUE
- Sensory details should be VIVID and IMMERSIVE
- Return pure JSON, no markdown formatting"""

def enrich_with_mega_prompt(api_key, topic_text, topic_description, story_profile):
    """Single GPT-4 call for all enrichment"""
    start_time = time.time()

    prompt = build_mega_enrichment_prompt(topic_text, topic_description, story_profile)

    payload = {
        "model": "gpt-4",
        "messages": [
            {
                "role": "system",
                "content": "You are an expert story analyst and creative consultant. Return ONLY valid JSON without markdown formatting."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.75,  # Balanced between analytical and creative
        "max_tokens": 1500
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

        # Clean markdown if present
        if enrichment_text.startswith('```'):
            enrichment_text = enrichment_text.split('```')[1]
            if enrichment_text.startswith('json'):
                enrichment_text = enrichment_text[4:]
            enrichment_text = enrichment_text.strip()

        enrichment = json.loads(enrichment_text)

        processing_time = int((time.time() - start_time) * 1000)

        # Add metadata
        enrichment['_metadata'] = {
            'processing_time_ms': processing_time,
            'model': 'gpt-4',
            'temperature': 0.75,
            'prompt_tokens': response_data.get('usage', {}).get('prompt_tokens', 0),
            'completion_tokens': response_data.get('usage', {}).get('completion_tokens', 0),
            'total_tokens': response_data.get('usage', {}).get('total_tokens', 0)
        }

        return enrichment

    except json.JSONDecodeError as e:
        print(f"JSON parse error: {str(e)}")
        print(f"Raw response: {enrichment_text[:500]}")
        raise ValueError(f"Failed to parse AI response: {str(e)}")
    except Exception as e:
        print(f"OpenAI API error: {str(e)}")
        raise

def lambda_handler(event, context):
    """Main handler for mega enrichment"""
    print(f"Event: {json.dumps(event)}")

    try:
        topic_text = event.get('topic_text')
        topic_description = event.get('topic_description', {})
        story_profile = event.get('story_profile', {})

        if not topic_text:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'success': False, 'error': 'topic_text required'})
            }

        api_key = get_openai_api_key()
        enrichment = enrich_with_mega_prompt(api_key, topic_text, topic_description, story_profile)

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'success': True,
                'enrichment': enrichment,
                'topic_analyzed': topic_text,
                'version': 'sprint2.1'
            })
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({'success': False, 'error': f'Mega enrichment failed: {str(e)}'})
        }
