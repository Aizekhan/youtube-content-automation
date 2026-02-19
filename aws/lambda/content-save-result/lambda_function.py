import json
import boto3
from datetime import datetime
from decimal import Decimal
from botocore.config import Config
import sys
sys.path.append('./shared')

# WEEK 2.5: Request size validation
try:
    from input_size_validator import validate_data_save_request, RequestSizeTooLargeError
except ImportError:
    # Fallback if module not available
    def validate_data_save_request(event, **kwargs):
        pass
    class RequestSizeTooLargeError(Exception):
        pass

# WEEK 2 FIX: Add timeout configuration
boto_config = Config(
    connect_timeout=5,
    read_timeout=60,
    retries={'max_attempts': 3, 'mode': 'standard'}
)

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1', config=boto_config)
table = dynamodb.Table('GeneratedContent')

def convert_floats_to_decimal(obj):
    """Recursively convert float values to Decimal for DynamoDB compatibility"""
    if isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_floats_to_decimal(value) for key, value in obj.items()}
    elif isinstance(obj, float):
        return Decimal(str(obj))
    return obj

def safe_get(obj, key, default='Unknown'):
    """Safely get value from dict or return default"""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default

def lambda_handler(event, context):
    print(f" Save Result - MEGA Mode v4.0 - Multi-Tenant")
    print(f"Event keys: {list(event.keys())}")

    # Extract user_id for multi-tenant data isolation
    user_id = event.get('user_id')
    if not user_id:
        print("WARNING: No user_id provided")
        # For backward compatibility during migration
        raise ValueError('SECURITY ERROR: user_id is required for all requests')

    # WEEK 2.5: Validate request size to prevent memory exhaustion attacks
    try:
        validate_data_save_request(event, max_size_mb=20)
    except RequestSizeTooLargeError as e:
        print(f" Request validation failed: {e}")
        return {
            'channel_id': event.get('channel_id'),
            'content_id': event.get('content_id'),
            'status': 'error',
            'error': f'Request too large: {str(e)}'
        }

    # Basic fields
    channel_id = event.get('channel_id')
    config_id = event.get('config_id')  # Primary key for ChannelConfigs
    content_id = event.get('content_id')
    created_at = datetime.utcnow().isoformat() + 'Z'
    # VARIATION SET TRACKING: Read current variation set info
    variation_set_index = None
    variation_set_name = None
    generation_count_at_creation = None

    if config_id:
        try:
            channels_table = dynamodb.Table('ChannelConfigs')

            # SECURITY FIX: Load channel config with user_id verification BEFORE accessing data
            # This prevents IDOR (Insecure Direct Object Reference) vulnerability
            response = channels_table.get_item(Key={'config_id': config_id})

            if 'Item' not in response:
                print(f" Channel config not found: {config_id}")
                raise ValueError(f"Channel config not found: {config_id}")

            channel_config = response['Item']

            # SECURITY: Verify channel belongs to user IMMEDIATELY after loading
            # This check now happens BEFORE any data processing
            if channel_config.get('user_id') != user_id:
                print(f" SECURITY ERROR: Access denied - Channel config {config_id} belongs to user {channel_config.get('user_id')}, not {user_id}")
                raise ValueError(f"SECURITY: Access denied - Channel config does not belong to user {user_id}")

            # Parse variation_sets if it's a JSON string (PHP backend compatibility)
            variation_sets = channel_config.get('variation_sets', [])
            if isinstance(variation_sets, str):
                try:
                    variation_sets = json.loads(variation_sets)
                    print(f" Parsed variation_sets from JSON string: {len(variation_sets)} sets")
                except json.JSONDecodeError as e:
                    print(f" Failed to parse variation_sets JSON: {e}")
                    variation_sets = []

            # Convert generation_count to int (handles both string and number)
            generation_count_raw = channel_config.get('generation_count', 0)
            generation_count = int(generation_count_raw) if generation_count_raw else 0
            rotation_mode = channel_config.get('rotation_mode', 'sequential')

            if variation_sets and len(variation_sets) > 0:
                # Calculate active set (same logic as theme-agent and narrative)
                if rotation_mode == 'sequential':
                    active_set_index = generation_count % len(variation_sets)
                elif rotation_mode == 'random':
                    import random
                    random.seed(generation_count)
                    active_set_index = random.randint(0, len(variation_sets) - 1)
                else:  # manual
                    active_set_index = channel_config.get('manual_set_index', 0)

                if active_set_index < len(variation_sets):
                    active_set = variation_sets[active_set_index]
                    variation_set_index = active_set_index
                    variation_set_name = active_set.get('set_name', f'Set_{active_set_index}')
                    generation_count_at_creation = generation_count

                    print(f" Variation Set Tracking: Set {active_set_index}/{len(variation_sets)-1}: '{variation_set_name}' (gen #{generation_count})")
        except Exception as e:
            print(f" Failed to read variation set info: {e}")
            # Non-critical - continue saving content

    # MEGA mode data (as dicts)
    narrative_data = event.get('narrative_data', {})
    image_data = event.get('image_data', {})
    sfx_data = event.get('sfx_data', {})
    cta_data = event.get('cta_data', {})
    thumbnail_data = event.get('thumbnail_data', {})
    description_data = event.get('description_data', {})
    selected_topic = event.get('selected_topic', {})
    metadata = event.get('metadata', {})

    # Handle case where selected_topic is a string instead of dict
    if isinstance(selected_topic, str):
        selected_topic = {'title': selected_topic}
        print(f" Converted selected_topic from string to dict: {selected_topic}")

    # CRITICAL VALIDATION: Theme and Narrative MUST exist together
    # This prevents data integrity violations (narratives without themes)
    if not selected_topic or not selected_topic.get('title'):
        error_msg = f" VALIDATION FAILED: Missing theme (selected_topic) for channel {channel_id}"
        print(error_msg)
        raise ValueError("Cannot save content: missing theme (selected_topic). Theme MUST be created before narrative!")



    if not narrative_data or not narrative_data.get('story_title'):
        error_msg = f" VALIDATION FAILED: Missing narrative (narrative_data) for channel {channel_id}"
        print(error_msg)
        raise ValueError("Cannot save content: missing narrative (narrative_data). Both theme and narrative are required!")

    print(f" VALIDATION PASSED: Both theme '{selected_topic.get('title')}' and narrative '{narrative_data.get('story_title')}' exist")

    # Audio/Image results
    audio_files = event.get('audio_files', [])
    cta_audio_files = event.get('cta_audio_files', [])
    # Support both 'generated_images' (from Step Functions) and 'scene_images' (direct calls)
    scene_images = event.get('generated_images', event.get('scene_images', []))

    # Extract title safely
    story_title = safe_get(narrative_data, 'story_title', safe_get(selected_topic, 'title', 'Unknown'))

    # Build pipeline_status for frontend compatibility
    pipeline_status = {
        'progress_percentage': 100,
        'overall_status': 'completed',
        'stages': {
            'story': {'status': 'completed', 'timestamp': created_at},
            'voice': {'status': 'completed' if len(audio_files) > 0 else 'pending', 'timestamp': created_at},
            'visuals': {'status': 'completed' if len(scene_images) > 0 else 'pending', 'timestamp': created_at}
        }
    }

    # Get channel info for metadata
    channel_name = 'Unknown'
    genre = None
    if config_id:
        try:
            channels_table = dynamodb.Table('ChannelConfigs')
            response = channels_table.get_item(Key={'config_id': config_id})
            if 'Item' in response:
                channel_config = response['Item']

                # Security: Verify channel belongs to user (defense in depth)
                if channel_config.get('user_id') != user_id:
                    print(f" SECURITY ERROR: Channel config {config_id} does not belong to user {user_id}")
                    raise ValueError(f"Access denied: Channel config does not belong to user {user_id}")

                channel_name = channel_config.get('channel_name', 'Unknown')
                genre = channel_config.get('genre')
        except Exception as e:
            print(f" Failed to get channel name/genre: {e}")

    # Build image_data from narrative_data if not provided
    if not image_data or not image_data.get('scenes'):
        scenes = narrative_data.get('scenes', [])
        if scenes:
            image_scenes = []
            for scene in scenes:
                scene_data = {
                    'scene_number': scene.get('scene_number', 0),
                    'image_prompt': scene.get('image_prompt', ''),
                    'negative_prompt': scene.get('negative_prompt', '')
                }
                image_scenes.append(scene_data)
            image_data = {
                'scenes': image_scenes,
                'total_images': len(image_scenes)
            }
        else:
            image_data = {}

    # Build description_data if not provided
    if not description_data:
        description_data = {
            'title': story_title,
            'description': f"Generated story: {story_title}" if story_title else '',
            'tags': []
        }

    # Ensure cta_data has proper structure
    if not cta_data:
        cta_data = {'cta_segments': []}

    # Build DynamoDB item
    item = {
        'channel_id': channel_id,
        'created_at': created_at,
        'user_id': user_id,  # Multi-tenant data isolation
        'content_id': content_id,
        'type': 'mega_generation',
        'story_title': story_title,
        'status': 'completed',
        'api_version': 'mega_mode_v4',

        # Frontend compatibility
        'pipeline_status': pipeline_status,

        # MEGA data
        'narrative_data': narrative_data,
        'image_data': image_data,
        'sfx_data': sfx_data,
        'cta_data': cta_data,
        'thumbnail_data': thumbnail_data,
        'description_data': description_data,
        'selected_topic': selected_topic,

        # Channel metadata (for frontend display)
        'channel_name': channel_name,
        'genre': genre,
        'model': event.get('model', safe_get(narrative_data, 'model', safe_get(metadata, 'model', 'gpt-4o-mini'))),  # AI model from event or narrative

        # Frontend compatibility: genre in metadata object
        'metadata': {
            'genre': genre,
            'total_word_count': safe_get(metadata, 'total_word_count', 0),
            'total_scenes': safe_get(metadata, 'total_scenes', 0),
        },

        # VARIATION SET TRACKING (for history and analytics)
        'variation_set_index': variation_set_index,  # e.g., 0, 1, 2, 3, 4
        'variation_set_name': variation_set_name,    # e.g., 'Ancient Egypt', 'Ancient Greece'
        'generation_count_at_creation': generation_count_at_creation,  # e.g., 0, 1, 2...

        # Audio
        'audio_files': audio_files,
        'cta_audio_files': cta_audio_files,
        'has_audio': len(audio_files) > 0,
        'audio_scene_count': len(audio_files),
        'audio_duration_sec': event.get('audio_duration_sec', 0),
        'tts_provider': event.get('tts_provider'),

        # Images
        'scene_images': scene_images,
        'has_images': len(scene_images) > 0,
        'image_count': len(scene_images),

        # Metadata
        'total_cost_usd': Decimal(str(event.get('total_cost_usd', 0))),
        'validation_errors': event.get('validation_errors', []),

        # Frontend-expected field names
        'character_count': safe_get(metadata, 'total_word_count', safe_get(narrative_data, 'total_word_count', 0)),
        'scene_count': safe_get(metadata, 'total_scenes', safe_get(narrative_data, 'total_scenes', 0)),
        'voice': event.get('tts_provider', event.get('tts_service', 'Auto')),

        # Original field names (for backward compatibility)
        'total_word_count': safe_get(metadata, 'total_word_count', 0),
        'total_scenes': safe_get(metadata, 'total_scenes', 0),
        'estimated_duration_seconds': safe_get(metadata, 'estimated_duration_seconds', 0)
    }

    try:
        item = convert_floats_to_decimal(item)
        table.put_item(Item=item)

        print(f" Saved: content_id={content_id}, title={story_title}")

        # AUTO-INCREMENT generation_count for Variation Sets rotation
        try:
            channels_table = dynamodb.Table('ChannelConfigs')
            channels_table.update_item(
                Key={'config_id': config_id},
                UpdateExpression='SET generation_count = if_not_exists(generation_count, :zero) + :inc',
                ExpressionAttributeValues={
                    ':zero': 0,
                    ':inc': 1
                }
            )
            print(f" Incremented generation_count for channel {channel_id}")
        except Exception as inc_error:
            # Non-critical error - content is already saved
            print(f" Failed to increment generation_count: {inc_error}")

        return {
            'channel_id': channel_id,
            'content_id': content_id,
            'status': 'saved',
            'timestamp': created_at,
            'story_title': story_title
        }

    except Exception as e:
        print(f" Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'channel_id': channel_id,
            'content_id': content_id,
            'status': 'error',
            'error': str(e)
        }
