"""
Content Story DNA Generator Lambda
Sprint 2 - Task 2.4

Generates unique narrative DNA to avoid clichés.
Creates unique twists, character seeds, plot hooks, and anti-cliché guards.
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

def build_story_dna_prompt(topic_text, genre, story_type, tone, complexity_level):
    """Build prompt for generating unique story DNA"""
    return f"""Generate unique Story DNA for this narrative to avoid clichés:

TOPIC: "{topic_text}"
GENRE: {genre}
STORY TYPE: {story_type}
TONE: {tone}
COMPLEXITY: {complexity_level}/5

Your goal: Create UNIQUE, UNEXPECTED narrative elements that break genre conventions.

Return ONLY valid JSON:

{{
  "story_dna": {{
    "unique_twist": "one sentence describing the core unexpected element that makes this story different",
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

Be BOLD. Be CREATIVE. AVOID all genre clichés. Make it MEMORABLE."""

def generate_story_dna_with_ai(api_key, topic_text, genre, story_type, tone, complexity_level):
    """Use OpenAI to generate unique story DNA"""
    prompt = build_story_dna_prompt(topic_text, genre, story_type, tone, complexity_level)

    payload = {
        "model": "gpt-4",
        "messages": [
            {
                "role": "system",
                "content": "You are a master storyteller who creates unique, memorable narratives by subverting genre conventions and avoiding clichés. Return pure JSON without markdown."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.9,  # High creativity for unique DNA
        "max_tokens": 800
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

        dna_text = response_data['choices'][0]['message']['content'].strip()

        # Clean markdown if present
        if dna_text.startswith('```'):
            dna_text = dna_text.split('```')[1]
            if dna_text.startswith('json'):
                dna_text = dna_text[4:]
            dna_text = dna_text.strip()

        story_dna = json.loads(dna_text)
        return story_dna

    except json.JSONDecodeError as e:
        print(f"JSON parse error: {str(e)}")
        print(f"Raw response: {dna_text[:500]}")
        raise ValueError(f"Failed to parse AI response: {str(e)}")
    except Exception as e:
        print(f"OpenAI API error: {str(e)}")
        raise

def lambda_handler(event, context):
    """Main handler for story DNA generation"""
    print(f"Event: {json.dumps(event)}")

    try:
        topic_text = event.get('topic_text')
        genre = event.get('genre', 'mystery')
        story_type = event.get('story_type', 'discovery_quest')
        tone = event.get('tone_suggestion', 'dark')
        complexity_level = event.get('complexity_level', 3)

        if not topic_text:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
                'body': json.dumps({'success': False, 'error': 'topic_text required'})
            }

        api_key = get_openai_api_key()
        story_dna = generate_story_dna_with_ai(
            api_key,
            topic_text,
            genre,
            story_type,
            tone,
            complexity_level
        )

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'},
            'body': json.dumps({
                'success': True,
                'story_dna': story_dna.get('story_dna', story_dna),
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
            'body': json.dumps({'success': False, 'error': f'Failed to generate story DNA: {str(e)}'})
        }
