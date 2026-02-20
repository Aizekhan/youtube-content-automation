"""
Content Topic Analyzer Lambda
Sprint 2 - Task 2.1

Analyzes topic_text and determines story characteristics:
- Genre & sub-genre
- Story type & complexity
- Mood tags & themes
- Setting type & time period
- Estimated scene count
"""

import json
import os
import boto3
import http.client

# Get OpenAI API key
def get_openai_api_key():
    """Get OpenAI API key from Secrets Manager"""
    secrets_client = boto3.client('secretsmanager', region_name='eu-central-1')

    try:
        response = secrets_client.get_secret_value(SecretId='openai/api-key')
        secret_string = response['SecretString']

        # Try parsing as JSON first
        try:
            secret = json.loads(secret_string)
            api_key = secret.get('OPENAI_API_KEY') or secret.get('api_key')
        except json.JSONDecodeError:
            # If not JSON, treat as plain string
            api_key = secret_string

        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in secret")

        return api_key
    except Exception as e:
        print(f"Error getting OpenAI API key: {str(e)}")
        raise


def build_analysis_prompt(topic_text, topic_description, story_profile):
    """Build prompt for topic analysis"""

    context = topic_description.get('context', '') if topic_description else ''
    tone = topic_description.get('tone_suggestion', '') if topic_description else ''
    key_elements = topic_description.get('key_elements', []) if topic_description else []

    story_mode = story_profile.get('story_mode', 'fiction') if story_profile else 'fiction'
    world_type = story_profile.get('world_type', 'realistic') if story_profile else 'realistic'

    prompt = f"""Analyze this story topic and provide detailed categorization:

TOPIC: "{topic_text}"

CONTEXT: {context if context else 'Not provided'}
TONE SUGGESTION: {tone if tone else 'Not specified'}
KEY ELEMENTS: {', '.join(key_elements) if key_elements else 'Not specified'}
STORY MODE: {story_mode}
WORLD TYPE: {world_type}

Analyze and return ONLY a JSON object with this exact structure:

{{
  "genre": "primary genre (mystery, horror, thriller, drama, adventure, sci-fi, fantasy, historical, etc.)",
  "sub_genre": "more specific sub-category",
  "story_type": "narrative structure type (discovery_quest, psychological_journey, survival_story, heist, revenge_tale, coming_of_age, etc.)",
  "complexity_level": 1-5 (1=simple, 5=very complex),
  "estimated_scenes": 6-10 (recommended number of scenes),
  "key_themes": ["theme1", "theme2", "theme3"],
  "mood_tags": ["mood1", "mood2", "mood3"],
  "setting_type": "primary setting (urban, wilderness, historical_location, enclosed_space, virtual_world, etc.)",
  "time_period": "when story takes place (modern_day, historical_era, future, timeless, etc.)",
  "narrative_perspective_suggestion": "suggested POV (first_person, third_person_limited, omniscient)",
  "pacing_recommendation": "slow_burn, steady, fast_paced, or variable",
  "conflict_type": "primary conflict (internal, external, vs_nature, vs_society, vs_supernatural, etc.)"
}}

Requirements:
1. Be specific and insightful
2. Consider the tone and key elements provided
3. Match complexity to the topic's depth
4. Suggest appropriate scene count (simpler = fewer scenes)
5. Return ONLY valid JSON, no markdown, no explanation"""

    return prompt


def analyze_topic_with_ai(api_key, topic_text, topic_description, story_profile):
    """Use OpenAI to analyze the topic via direct HTTP request"""

    prompt = build_analysis_prompt(topic_text, topic_description, story_profile)

    # Build OpenAI API request
    payload = {
        "model": "gpt-4",
        "messages": [
            {
                "role": "system",
                "content": "You are a professional story analyst and genre expert. Analyze topics and categorize them accurately. Always return pure JSON without markdown formatting."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.3,
        "max_tokens": 500
    }

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    try:
        # Use http.client for direct API call
        conn = http.client.HTTPSConnection('api.openai.com', timeout=30)
        conn.request('POST', '/v1/chat/completions', json.dumps(payload), headers)
        response = conn.getresponse()
        response_data = json.loads(response.read().decode())
        conn.close()

        if response.status != 200:
            raise ValueError(f"OpenAI API error: {response_data}")

        analysis_text = response_data['choices'][0]['message']['content'].strip()

        # Remove markdown code blocks if present
        if analysis_text.startswith('```'):
            analysis_text = analysis_text.split('```')[1]
            if analysis_text.startswith('json'):
                analysis_text = analysis_text[4:]
            analysis_text = analysis_text.strip()

        # Parse JSON
        analysis = json.loads(analysis_text)

        # Validate required fields
        required_fields = [
            'genre', 'sub_genre', 'story_type', 'complexity_level',
            'estimated_scenes', 'key_themes', 'mood_tags', 'setting_type',
            'time_period'
        ]

        for field in required_fields:
            if field not in analysis:
                raise ValueError(f"Missing required field: {field}")

        return analysis

    except json.JSONDecodeError as e:
        print(f"JSON parse error: {str(e)}")
        print(f"Raw response: {analysis_text}")
        raise ValueError(f"Failed to parse AI response as JSON: {str(e)}")
    except Exception as e:
        print(f"OpenAI API error: {str(e)}")
        raise


def lambda_handler(event, context):
    """
    Main Lambda handler for topic analysis

    Input:
    {
      "topic_text": "The Mystery of the Lost City",
      "topic_description": {
        "context": "Ancient civilization",
        "tone_suggestion": "dark",
        "key_elements": ["temples", "mystery", "discovery"]
      },
      "story_profile": {
        "story_mode": "fiction",
        "world_type": "realistic"
      }
    }

    Output:
    {
      "success": true,
      "analysis": {
        "genre": "mystery",
        "sub_genre": "archaeological_thriller",
        ...
      }
    }
    """

    print(f"Received event: {json.dumps(event)}")

    try:
        # Extract inputs
        topic_text = event.get('topic_text')
        topic_description = event.get('topic_description', {})
        story_profile = event.get('story_profile', {})

        # Validate required fields
        if not topic_text:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'success': False,
                    'error': 'topic_text is required'
                })
            }

        # Get OpenAI API key
        api_key = get_openai_api_key()

        # Analyze topic
        analysis = analyze_topic_with_ai(
            api_key,
            topic_text,
            topic_description,
            story_profile
        )

        # Add metadata
        analysis['topic_text_analyzed'] = topic_text
        analysis['analysis_timestamp'] = context.aws_request_id if context else 'test'

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'analysis': analysis
            })
        }

    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'error': f'Failed to analyze topic: {str(e)}'
            })
        }
