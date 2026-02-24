"""
Series State CRUD Lambda
Manages SeriesState table - series configuration, characters, plot threads, tension curve

Operations:
- GET: Retrieve series state by series_id
- CREATE: Create new series with default template
- UPDATE: Update series configuration (arc_goal, tension_curve, characters, etc.)
- AUTO_UPDATE: Called by content-save-result after episode generation
"""
import json
import boto3
from datetime import datetime
from decimal import Decimal
from botocore.config import Config

boto_config = Config(
    connect_timeout=5,
    read_timeout=60,
    retries={'max_attempts': 3, 'mode': 'standard'}
)

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1', config=boto_config)
series_table = dynamodb.Table('SeriesState')

# Voice mapping for character auto-assignment
VOICE_MAPPING = {
    ('male', 'child'):        'aiden',
    ('male', 'young_adult'):  'dylan',
    ('male', 'adult'):        'ryan',
    ('male', 'elder'):        'uncle_fu',
    ('female', 'child'):      'sohee',
    ('female', 'young_adult'): 'vivian',
    ('female', 'adult'):      'serena',
    ('female', 'elder'):      'ono_anna',
}

def infer_voice(character_data):
    """
    Infer voice from character gender, age_group, and character_type

    Args:
        character_data (dict): Character with gender, age_group, character_type, description

    Returns:
        tuple: (speaker, voice_description)
    """
    gender = character_data.get('gender', 'neutral').lower()
    age_group = character_data.get('age_group', 'adult').lower()
    char_type = character_data.get('character_type', 'human').lower()
    description = character_data.get('description', '')

    # Direct mapping for humans
    voice_key = (gender, age_group)
    if voice_key in VOICE_MAPPING:
        speaker = VOICE_MAPPING[voice_key]
        voice_desc = f"{gender.capitalize()} {age_group.replace('_', ' ')} voice"
        return (speaker, voice_desc)

    # Fallback for non-human or neutral gender
    # Animal/creature/spirit - map based on personality hints in description
    if char_type in ['animal', 'creature', 'spirit']:
        # Default animal voices based on age_group
        if age_group == 'elder':
            return ('uncle_fu', 'Wise, aged voice')
        elif age_group == 'child':
            return ('sohee', 'Young, playful voice')
        else:
            return ('ryan', 'Neutral creature voice')

    # Ultimate fallback
    return ('ryan', 'Neutral voice')

def convert_decimals(obj):
    """Convert Decimal to int/float for JSON serialization"""
    if isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_decimals(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj

def lambda_handler(event, context):
    print(f"SeriesState Lambda - Event: {json.dumps(event, default=str)}")

    # CORS is handled by Function URL configuration - no need for OPTIONS handler

    # Parse body if Function URL request
    if isinstance(event.get('body'), str):
        try:
            body = json.loads(event['body'])
        except:
            body = event
    else:
        body = event.get('body', event)

    operation = body.get('operation') or event.get('operation')
    user_id = body.get('user_id') or event.get('user_id')

    if not user_id:
        return error_response('user_id required for security', 400)

    if operation == 'GET':
        return get_series_state(body, user_id)
    elif operation == 'CREATE':
        return create_series_state(body, user_id)
    elif operation == 'UPDATE':
        return update_series_state(body, user_id)
    elif operation == 'AUTO_UPDATE':
        return auto_update_series_state(body, user_id)
    elif operation == 'LIST':
        return list_series_by_channel(body, user_id)
    else:
        return error_response(f'Unknown operation: {operation}', 400)

def get_series_state(body, user_id):
    """GET: Retrieve series state"""
    series_id = body.get('series_id')

    if not series_id:
        return error_response('series_id required', 400)

    try:
        response = series_table.get_item(Key={'series_id': series_id})

        if 'Item' not in response:
            return error_response(f'Series not found: {series_id}', 404)

        series = response['Item']

        # Security: verify series belongs to user
        if series.get('user_id') != user_id:
            return error_response('Access denied', 403)

        return success_response(convert_decimals(series))

    except Exception as e:
        print(f"GET error: {e}")
        import traceback
        traceback.print_exc()
        return error_response(str(e), 500)

def create_series_state(body, user_id):
    """CREATE: Create new series with template"""
    series_id = body.get('series_id')
    channel_id = body.get('channel_id')
    series_title = body.get('series_title', 'Untitled Series')
    total_episodes = body.get('total_episodes', 10)

    if not series_id or not channel_id:
        return error_response('series_id and channel_id required', 400)

    try:
        # Check if series already exists
        existing = series_table.get_item(Key={'series_id': series_id})
        if 'Item' in existing:
            return error_response(f'Series already exists: {series_id}', 409)

        # Default tension curve template (10 episodes)
        default_tension = generate_default_tension_curve(total_episodes)

        timestamp = datetime.utcnow().isoformat() + 'Z'

        series_state = {
            'series_id': series_id,
            'channel_id': channel_id,
            'user_id': user_id,
            'series_title': series_title,
            'series_notes': body.get('series_notes', ''),

            # Season arc
            'season_arc': {
                'arc_goal': body.get('arc_goal', ''),
                'climax_episode': int(total_episodes * 0.8),  # 80% point
                'finale_episode': total_episodes,
                'total_episodes': total_episodes,
                'theme': body.get('theme', '')
            },

            # Tension curve
            'tension_curve': default_tension,

            # Narrator voice
            'narrator_voice': {
                'speaker': body.get('narrator_speaker', 'ryan'),
                'voice_description': body.get('narrator_voice_description', 'Neutral narration')
            },

            # Characters (empty - added as episodes generate)
            'characters': {},

            # Plot threads
            'plot_threads': [],

            # Archetypes used
            'archetypes_used': [],

            # Episodes generated
            'episodes_generated': 0,

            # Series overrides (defaults from channel config)
            'series_overrides': {
                'complexity_level': body.get('complexity_level', 7),
                'narrative_tone': body.get('narrative_tone', 'balanced'),
                'archetype_pool': body.get('archetype_pool', [])
            },

            # Metadata
            'created_at': timestamp,
            'updated_at': timestamp
        }

        series_table.put_item(Item=series_state)

        print(f"Created series: {series_id}")
        return success_response(convert_decimals(series_state))

    except Exception as e:
        print(f"CREATE error: {e}")
        import traceback
        traceback.print_exc()
        return error_response(str(e), 500)

def update_series_state(body, user_id):
    """UPDATE: Manual update from Series Dashboard"""
    series_id = body.get('series_id')
    updates = body.get('updates', {})

    if not series_id or not updates:
        return error_response('series_id and updates required', 400)

    try:
        # Load and verify ownership
        response = series_table.get_item(Key={'series_id': series_id})
        if 'Item' not in response:
            return error_response(f'Series not found: {series_id}', 404)

        series = response['Item']
        if series.get('user_id') != user_id:
            return error_response('Access denied', 403)

        # Build update expression
        update_expr = "SET updated_at = :ts"
        expr_values = {':ts': datetime.utcnow().isoformat() + 'Z'}

        # Update arc_goal
        if 'arc_goal' in updates:
            update_expr += ", season_arc.arc_goal = :arc_goal"
            expr_values[':arc_goal'] = updates['arc_goal']

        # Update tension_curve
        if 'tension_curve' in updates:
            update_expr += ", tension_curve = :tension"
            expr_values[':tension'] = updates['tension_curve']

        # Update narrator_voice
        if 'narrator_voice' in updates:
            update_expr += ", narrator_voice = :narrator"
            expr_values[':narrator'] = updates['narrator_voice']

        # Update characters
        if 'characters' in updates:
            update_expr += ", characters = :chars"
            expr_values[':chars'] = updates['characters']

        # Update plot_threads
        if 'plot_threads' in updates:
            update_expr += ", plot_threads = :threads"
            expr_values[':threads'] = updates['plot_threads']

        # Update series_overrides
        if 'series_overrides' in updates:
            update_expr += ", series_overrides = :overrides"
            expr_values[':overrides'] = updates['series_overrides']

        series_table.update_item(
            Key={'series_id': series_id},
            UpdateExpression=update_expr,
            ExpressionAttributeValues=expr_values
        )

        print(f"Updated series: {series_id}")

        # Return updated series
        updated = series_table.get_item(Key={'series_id': series_id})
        return success_response(convert_decimals(updated['Item']))

    except Exception as e:
        print(f"UPDATE error: {e}")
        import traceback
        traceback.print_exc()
        return error_response(str(e), 500)

def auto_update_series_state(body, user_id):
    """AUTO_UPDATE: Called by content-save-result after episode generation"""
    series_id = body.get('series_id')
    episode_number = body.get('episode_number')
    episode_summary = body.get('episode_summary', {})

    if not series_id or not episode_number:
        return error_response('series_id and episode_number required', 400)

    try:
        # Load series
        response = series_table.get_item(Key={'series_id': series_id})
        if 'Item' not in response:
            return error_response(f'Series not found: {series_id}', 404)

        series = response['Item']
        if series.get('user_id') != user_id:
            return error_response('Access denied', 403)

        # Extract data from episode_summary
        characters_introduced = episode_summary.get('characters_introduced', [])
        open_threads = episode_summary.get('open_threads', [])
        closed_threads = episode_summary.get('closed_threads', [])
        archetype_used = episode_summary.get('archetype_used', '')

        # Update characters
        updated_characters = series.get('characters', {}).copy()
        for char_data in characters_introduced:
            # Support both new dict format and old string format
            if isinstance(char_data, dict):
                # New format with gender, age_group, character_type
                char_name = char_data.get('name', 'Unknown')
                char_id = char_name.lower().replace(' ', '_')

                if char_id not in updated_characters:
                    # Infer voice from character data
                    speaker, voice_desc = infer_voice(char_data)

                    updated_characters[char_id] = {
                        'name': char_name,
                        'role': 'supporting',
                        'introduced_ep': episode_number,
                        'visual_frozen': char_data.get('description', ''),
                        'gender': char_data.get('gender', 'neutral'),
                        'age_group': char_data.get('age_group', 'adult'),
                        'character_type': char_data.get('character_type', 'human'),
                        'voice_config': {
                            'speaker': speaker,
                            'voice_description': voice_desc
                        },
                        'current_state': '',
                        'emotional_arc': []
                    }
            elif isinstance(char_data, str):
                # Old format: "Name - description"
                parts = char_data.split(' - ', 1)
                if len(parts) == 2:
                    char_name = parts[0].strip()
                    char_id = char_name.lower().replace(' ', '_')

                    if char_id not in updated_characters:
                        # Use fallback voice for old format
                        updated_characters[char_id] = {
                            'name': char_name,
                            'role': 'supporting',
                            'introduced_ep': episode_number,
                            'visual_frozen': parts[1].strip(),
                            'voice_config': {
                                'speaker': 'ryan',  # fallback for old format
                                'voice_description': 'Neutral voice'
                            },
                            'current_state': '',
                            'emotional_arc': []
                        }

        # Update plot_threads
        updated_threads = series.get('plot_threads', []).copy()

        # Add new open threads
        for thread_desc in open_threads:
            thread_id = f"thread-{len(updated_threads) + 1:03d}"
            updated_threads.append({
                'thread_id': thread_id,
                'description': thread_desc,
                'introduced_ep': episode_number,
                'priority': 'MEDIUM',
                'status': 'open'
            })

        # Close resolved threads
        for closed_desc in closed_threads:
            for thread in updated_threads:
                if closed_desc.lower() in thread.get('description', '').lower():
                    thread['status'] = 'closed'
                    thread['resolved_ep'] = episode_number

        # Update archetypes_used
        updated_archetypes = series.get('archetypes_used', []).copy()
        if archetype_used:
            updated_archetypes.append({
                'ep': episode_number,
                'archetype': archetype_used
            })

        # Increment episodes_generated
        episodes_generated = series.get('episodes_generated', 0) + 1

        # Update DynamoDB
        series_table.update_item(
            Key={'series_id': series_id},
            UpdateExpression="""
                SET characters = :chars,
                    plot_threads = :threads,
                    archetypes_used = :archetypes,
                    episodes_generated = :count,
                    updated_at = :ts
            """,
            ExpressionAttributeValues={
                ':chars': updated_characters,
                ':threads': updated_threads,
                ':archetypes': updated_archetypes,
                ':count': episodes_generated,
                ':ts': datetime.utcnow().isoformat() + 'Z'
            }
        )

        print(f"Auto-updated series {series_id} after EP{episode_number}")
        return success_response({'updated': True, 'episodes_generated': episodes_generated})

    except Exception as e:
        print(f"AUTO_UPDATE error: {e}")
        import traceback
        traceback.print_exc()
        return error_response(str(e), 500)

def list_series_by_channel(body, user_id):
    """LIST: Get all series for a channel"""
    channel_id = body.get('channel_id')

    if not channel_id:
        return error_response('channel_id required', 400)

    try:
        response = series_table.query(
            IndexName='ChannelIndex',
            KeyConditionExpression='channel_id = :cid',
            ExpressionAttributeValues={':cid': channel_id}
        )

        series_list = response.get('Items', [])

        # Filter by user_id for security
        filtered = [s for s in series_list if s.get('user_id') == user_id]

        return success_response({'series': convert_decimals(filtered)})

    except Exception as e:
        print(f"LIST error: {e}")
        import traceback
        traceback.print_exc()
        return error_response(str(e), 500)

def generate_default_tension_curve(total_episodes):
    """Generate default tension curve with climax at 80% point"""
    curve = {}
    for ep in range(1, total_episodes + 1):
        # Start low, build to climax, resolve
        if ep <= total_episodes * 0.3:
            tension = 3 + (ep * 0.5)  # Build slowly
        elif ep <= total_episodes * 0.7:
            tension = 5 + ((ep - total_episodes * 0.3) * 0.3)  # Build faster
        elif ep <= total_episodes * 0.8:
            tension = 8 + ((ep - total_episodes * 0.7) * 2)  # Peak
        elif ep < total_episodes:
            tension = 8 - ((ep - total_episodes * 0.8) * 0.5)  # Falling action
        else:
            tension = 10  # Finale

        curve[str(ep)] = int(min(10, max(1, tension)))

    return curve

def success_response(data):
    """Standard success response - CORS handled by Function URL"""
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'success': True,
            'data': data
        }, default=str)
    }

def error_response(message, status_code=500):
    """Standard error response - CORS handled by Function URL"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'success': False,
            'error': message
        })
    }
