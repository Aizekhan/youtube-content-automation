"""
Episode Summary Generator
Generates structured episode summaries for series continuity
"""
import json
import os
import boto3

# Load OpenAI API key from Secrets Manager
def get_openai_api_key():
    """Load OpenAI API key from AWS Secrets Manager"""
    try:
        # First try environment variable (for local testing)
        api_key = os.environ.get('OPENAI_API_KEY')
        if api_key:
            return api_key

        # Otherwise load from Secrets Manager
        secrets_client = boto3.client('secretsmanager', region_name='eu-central-1')
        response = secrets_client.get_secret_value(SecretId='openai/api-key')
        # Secret is stored as plain text, not JSON
        return response['SecretString'].strip()
    except Exception as e:
        print(f"Error loading OpenAI API key: {e}")
        return None

def generate_episode_summary(narrative_data, topic_text, episode_number=None):
    """
    Generate structured episode summary for series continuity

    Args:
        narrative_data (dict): Full narrative content with scenes and mechanics
        topic_text (str): Episode topic/title
        episode_number (int): Episode number in series

    Returns:
        dict: Structured episode summary with:
            - episode_summary: 100-150 word narrative summary
            - characters_introduced: List of new characters
            - open_threads: List of unresolved plot threads
            - closed_threads: List of resolved plot threads
            - archetype_used: Story archetype
    """

    # Extract key data
    mechanics = narrative_data.get('mechanics', {})
    scenes = narrative_data.get('scenes', [])
    story_title = narrative_data.get('story_title', topic_text)

    # Build narrative text from scenes
    narrative_text = "\n\n".join([
        f"Scene {scene.get('scene_number', i+1)}: {scene.get('narration', '')}"
        for i, scene in enumerate(scenes[:5])  # First 5 scenes for context
    ])

    # Story mechanics context
    surface_truth = mechanics.get('surface_truth', '')
    hidden_truth = mechanics.get('hidden_truth', '')
    archetype = mechanics.get('dominant_archetype', 'unknown')
    recontextualization = mechanics.get('recontextualization_moment', '')

    prompt = f"""You are analyzing episode {episode_number or 'N/A'} of a series.

EPISODE TITLE: {story_title}
TOPIC: {topic_text}

STORY MECHANICS:
- Archetype: {archetype}
- Surface Truth: {surface_truth}
- Hidden Truth: {hidden_truth}
- Recontextualization: {recontextualization}

NARRATIVE (first 5 scenes):
{narrative_text}

Generate a structured episode summary in JSON format:

{{
  "episode_summary": "100-150 word summary focusing on KEY EVENTS and CHARACTER DEVELOPMENT. What happened that moves the story forward?",
  "characters_introduced": ["Character Name - brief description (age, role, key trait)"],
  "open_threads": [
    "Plot thread that MUST be addressed in future episodes (unresolved tension, unanswered questions, character arcs in progress)"
  ],
  "closed_threads": [
    "Plot thread that was RESOLVED in this episode (conflicts ended, questions answered, arcs completed)"
  ],
  "archetype_used": "{archetype}"
}}

CRITICAL RULES:
1. episode_summary: Focus on EVENTS and CHANGES, not descriptions
2. open_threads: Only include threads with UNRESOLVED tension (not background info)
3. closed_threads: Only include threads that were FULLY resolved in this episode
4. Keep it concise - this will be context for future episodes

Generate the JSON now:"""

    try:
        # Get API key
        api_key = get_openai_api_key()
        if not api_key:
            raise ValueError("OpenAI API key not available")

        # Create OpenAI client with explicit API key
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a narrative continuity expert. Generate structured episode summaries for series storytelling."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Low temperature for consistent structure
            max_tokens=500,
            response_format={"type": "json_object"}
        )

        summary_json = response.choices[0].message.content
        summary = json.loads(summary_json)

        # Validation
        required_fields = ['episode_summary', 'characters_introduced', 'open_threads', 'closed_threads', 'archetype_used']
        for field in required_fields:
            if field not in summary:
                summary[field] = [] if field in ['characters_introduced', 'open_threads', 'closed_threads'] else ''

        print(f"Generated episode summary: {len(summary['episode_summary'])} chars, {len(summary['open_threads'])} open threads")

        return summary

    except Exception as e:
        print(f"Error generating episode summary: {e}")
        # Fallback basic summary
        return {
            'episode_summary': f"Episode {episode_number or 'N/A'}: {story_title}. {surface_truth}",
            'characters_introduced': [],
            'open_threads': [],
            'closed_threads': [],
            'archetype_used': archetype
        }


def update_topic_with_summary(channel_id, topic_id, episode_summary, content_id):
    """
    Update ContentTopicsQueue with episode summary after generation

    Args:
        channel_id (str): Channel ID
        topic_id (str): Topic ID
        episode_summary (dict): Generated episode summary
        content_id (str): Link to GeneratedContent
    """
    import boto3
    from botocore.config import Config
    from datetime import datetime

    boto_config = Config(
        connect_timeout=5,
        read_timeout=60,
        retries={'max_attempts': 3, 'mode': 'standard'}
    )

    dynamodb = boto3.resource('dynamodb', region_name='eu-central-1', config=boto_config)
    topics_table = dynamodb.Table('ContentTopicsQueue')

    try:
        timestamp = datetime.utcnow().isoformat() + 'Z'

        # Update topic with episode summary
        topics_table.update_item(
            Key={
                'channel_id': channel_id,
                'topic_id': topic_id
            },
            UpdateExpression='SET episode_summary = :summary, archetype_used = :arch, content_id = :cid, updated_at = :ts, generation_completed_at = :ts',
            ExpressionAttributeValues={
                ':summary': episode_summary,
                ':arch': episode_summary.get('archetype_used', 'unknown'),
                ':cid': content_id,
                ':ts': timestamp
            }
        )

        print(f"Updated topic {topic_id} with episode summary (content_id: {content_id})")
        return True

    except Exception as e:
        print(f"Error updating topic with summary: {e}")
        import traceback
        traceback.print_exc()
        return False
