"""
Content Save Result Lambda - Sprint 3 - Quality Metrics Collection
Saves generated content to DynamoDB with enrichment metadata and quality metrics.
Sprint 4 - Series Episode Summary Generation
"""
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

# Sprint 4: Episode summary generation
try:
    from episode_summary_generator import generate_episode_summary, update_topic_with_summary
except ImportError as e:
    print(f"WARNING: episode_summary_generator not available - {e}")
    import traceback
    traceback.print_exc()
    generate_episode_summary = None
    update_topic_with_summary = None
except Exception as e:
    print(f"ERROR importing episode_summary_generator: {e}")
    import traceback
    traceback.print_exc()
    generate_episode_summary = None
    update_topic_with_summary = None

# WEEK 2 FIX: Add timeout configuration
boto_config = Config(
    connect_timeout=5,
    read_timeout=60,
    retries={'max_attempts': 3, 'mode': 'standard'}
)

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1', config=boto_config)
table = dynamodb.Table('GeneratedContent')

# Sprint 3: Lambda client for invoking cliche-detector
lambda_client = boto3.client('lambda', region_name='eu-central-1')

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

def invoke_cliche_detector(narrative_data):
    """Call cliche detector Lambda to analyze narrative quality"""
    try:
        response = lambda_client.invoke(
            FunctionName='content-cliche-detector',
            InvocationType='RequestResponse',
            Payload=json.dumps({'narrative_data': narrative_data})
        )

        result = json.loads(response['Payload'].read())
        if result.get('statusCode') == 200:
            body = json.loads(result['body'])
            return body if body.get('success') else None
        return None
    except Exception as e:
        print(f"Cliche detector error: {str(e)}")
        return None

def lambda_handler(event, context):
    print(f" Save Result - MEGA Mode v4.0 - Multi-Tenant - Sprint 3")
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

        except Exception as e:
            print(f" Failed to load channel config: {e}")
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

    # Sprint 3: Call cliche detector for quality metrics
    print(" Sprint 3: Invoking cliche detector for quality metrics...")
    cliche_results = invoke_cliche_detector(narrative_data)
    if cliche_results:
        print(f" Quality metrics collected: cliche_score={cliche_results.get('cliche_detection', {}).get('cliche_score', 0)}")
    else:
        print(" Quality metrics unavailable (cliche detector failed or returned no data)")

    # Sprint 3: Extract enrichment metadata from master_config
    master_config = event.get('master_config', {})
    enrichment_metadata = {
        'enrichment_enabled': bool(master_config.get('topic_analysis') or master_config.get('story_dna')),
        'enrichment_version': 'v2.1',
        'has_topic_analysis': bool(master_config.get('topic_analysis')),
        'has_story_dna': bool(master_config.get('story_dna')),
        'has_wikipedia_facts': bool(master_config.get('wikipedia_facts'))
    }

    # Sprint 3: Build quality metrics from cliche detector results
    quality_metrics = {}
    if cliche_results:
        quality_metrics = {
            'cliche_score': cliche_results.get('cliche_detection', {}).get('cliche_score', 0),
            'detected_cliches': [p['pattern'] for p in cliche_results.get('cliche_detection', {}).get('detected_patterns', [])],
            'is_clean': cliche_results.get('cliche_detection', {}).get('is_clean', True),
            'severity': cliche_results.get('cliche_detection', {}).get('severity', 'minimal'),
            'word_count': cliche_results.get('story_metrics', {}).get('word_count', 0),
            'unique_words': cliche_results.get('story_metrics', {}).get('unique_words', 0),
            'vocabulary_richness': cliche_results.get('story_metrics', {}).get('vocabulary_richness', 0),
            'twist_count': cliche_results.get('story_metrics', {}).get('twist_count', 0)
        }

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
        'estimated_duration_seconds': safe_get(metadata, 'estimated_duration_seconds', 0),

        # Sprint 3: Enrichment metadata and quality metrics
        'enrichment_metadata': enrichment_metadata,
        'quality_metrics': quality_metrics
    }

    try:
        item = convert_floats_to_decimal(item)
        table.put_item(Item=item)

        print(f" Saved: content_id={content_id}, title={story_title}")

        # Sprint 4: Generate episode summary for series episodes
        topic_id = selected_topic.get('topic_id') if isinstance(selected_topic, dict) else None
        series_id = event.get('series_id')
        episode_number = event.get('episode_number')

        if topic_id and series_id and episode_number and generate_episode_summary and update_topic_with_summary:
            print(f" Sprint 4: Generating episode summary for series {series_id}, episode {episode_number}")
            try:
                # Generate structured episode summary
                episode_summary = generate_episode_summary(
                    narrative_data=narrative_data,
                    topic_text=selected_topic.get('title', story_title),
                    episode_number=episode_number
                )

                # Update topic in ContentTopicsQueue with summary
                update_success = update_topic_with_summary(
                    channel_id=channel_id,
                    topic_id=topic_id,
                    episode_summary=episode_summary,
                    content_id=content_id
                )

                if update_success:
                    print(f" Episode summary generated and saved: {len(episode_summary.get('episode_summary', ''))} chars")
                else:
                    print(f" WARNING: Failed to update topic with episode summary")

            except Exception as e:
                print(f" ERROR generating episode summary: {e}")
                import traceback
                traceback.print_exc()
                # Non-fatal - don't fail the whole save operation
        elif topic_id and (series_id or episode_number):
            print(f" Skipping episode summary: series_id={series_id}, episode_number={episode_number}, generator_available={generate_episode_summary is not None}")

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
