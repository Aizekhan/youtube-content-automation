"""
Content Narrative Lambda v3.0 - MEGA-GENERATION Mode

Generates ALL 7 content components in ONE OpenAI request:
1. Narrative with SSML
2. Image Prompts for each scene
3. SFX + Music selection
4. CTA segments
5. Thumbnail design
6. Video Description
7. Metadata

Uses:
- mega_config_merger.py to merge all templates
- mega_prompt_builder.py to build comprehensive prompt
"""

import json
import boto3
import http.client
from datetime import datetime
from decimal import Decimal
from boto3.dynamodb.conditions import Key
from botocore.config import Config

# Import MEGA modules
import sys
sys.path.append('./shared')
from mega_config_merger import merge_mega_configuration
from mega_prompt_builder import build_mega_prompt
from openai_cache import get_cached_response, cache_response

# WEEK 2.5: Request size validation
try:
    from input_size_validator import validate_content_generation_request, RequestSizeTooLargeError
except ImportError:
    # Fallback if module not available
    def validate_content_generation_request(event, **kwargs):
        pass
    class RequestSizeTooLargeError(Exception):
        pass

# WEEK 2 FIX: Add timeout configuration for all AWS service calls
boto_config = Config(
    connect_timeout=5,      # Connection timeout: 5 seconds
    read_timeout=60,        # Read timeout: 60 seconds
    retries={
        'max_attempts': 3,  # Retry failed requests up to 3 times
        'mode': 'standard'  # Use standard retry mode with exponential backoff
    }
)

# AWS clients with timeout configuration
secrets_client = boto3.client('secretsmanager', region_name='eu-central-1', config=boto_config)
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1', config=boto_config)
cost_table = dynamodb.Table('CostTracking')

# OpenAI Pricing
OPENAI_PRICING = {
    'gpt-4o': {
        'input': 2.50 / 1_000_000,
        'output': 10.00 / 1_000_000,
    },
    'gpt-4o-mini': {
        'input': 0.150 / 1_000_000,
        'output': 0.600 / 1_000_000,
    }
}


def log_openai_cost(channel_id, content_id, model, input_tokens, output_tokens, user_id=None):
    """
    Log OpenAI API cost to CostTracking table

    WEEK 2 FIX: Added user_id parameter for multi-tenant cost isolation
    """
    try:
        # SECURITY: Warn if user_id not provided (multi-tenant isolation)
        if not user_id:
            print(" WARNING: Cost logged without user_id - multi-tenant isolation compromised!")

        model_key = model if model in OPENAI_PRICING else 'gpt-4o'
        pricing = OPENAI_PRICING[model_key]

        input_cost = input_tokens * pricing['input']
        output_cost = output_tokens * pricing['output']
        total_cost = Decimal(str(input_cost + output_cost))

        now = datetime.utcnow()

        item = {
            'date': now.strftime('%Y-%m-%d'),
            'timestamp': now.isoformat() + 'Z',
            'service': 'OpenAI',
            'operation': 'mega_generation',
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

        # Add user_id for multi-tenant cost tracking
        if user_id:
            item['user_id'] = user_id

        cost_table.put_item(Item=item)

        print(f" Logged cost: ${float(total_cost):.6f} ({input_tokens + output_tokens} tokens)")
        return float(total_cost)
    except Exception as e:
        print(f" Failed to log cost: {e}")
        return 0.0


def parse_json_fields_recursive(obj):
    """Recursively parse JSON string fields in a dict"""
    if not isinstance(obj, dict):
        return obj

    result = {}
    for key, value in obj.items():
        if isinstance(value, str):
            # Try to parse as JSON
            try:
                parsed = json.loads(value)
                result[key] = parse_json_fields_recursive(parsed) if isinstance(parsed, dict) else parsed
            except:
                result[key] = value
        elif isinstance(value, dict):
            result[key] = parse_json_fields_recursive(value)
        elif isinstance(value, list):
            result[key] = [parse_json_fields_recursive(item) if isinstance(item, dict) else item for item in value]
        else:
            result[key] = value
    return result


def convert_floats_to_decimal(obj):
    """Recursively convert all floats to Decimal for DynamoDB"""
    if isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_floats_to_decimal(value) for key, value in obj.items()}
    elif isinstance(obj, float):
        return Decimal(str(obj))
    else:
        return obj


def parse_known_json_fields(template):
    """
    Parse all known JSON string fields in templates

    DynamoDB (especially from PHP) often stores complex fields as JSON strings.
    This ensures all nested structures are properly parsed.
    """
    known_fields = [
        'ai_config',
        'scene_variations',
        'sfx_library',
        'music_library',
        'cta_config',
        'thumbnail_config',
        'tts_config',
        'description_config',
        'image_settings'
    ]

    for field in known_fields:
        if field in template and isinstance(template[field], str):
            try:
                template[field] = json.loads(template[field])
                print(f"   Parsed {field} from JSON string")
            except json.JSONDecodeError as e:
                print(f"   WARNING: Failed to parse {field}: {e}")
                template[field] = {}

    # Deep parse ai_config.sections if it exists
    if 'ai_config' in template and isinstance(template['ai_config'], dict):
        if 'sections' in template['ai_config'] and isinstance(template['ai_config']['sections'], str):
            try:
                template['ai_config']['sections'] = json.loads(template['ai_config']['sections'])
                print(f"   Parsed ai_config.sections from JSON string")
            except:
                template['ai_config']['sections'] = {}

    return template


# REMOVED: load_all_templates() and load_story_blueprint()
# Templates system deleted - see CLEANUP_STATUS_CHECKPOINT.md


def lambda_handler(event, context):
    print("=" * 80)
    print("MEGA-GENERATION v3.0 - Comprehensive Content Generator")
    print("=" * 80)
    print(f"Event: {json.dumps(event, ensure_ascii=False)[:500]}")

    # WEEK 2 FIX: Extract user_id for multi-tenant data isolation
    user_id = event.get('user_id')
    if not user_id:
        print("WARNING: No user_id provided")
        # For backward compatibility during migration
        raise ValueError('SECURITY ERROR: user_id is required for all requests')

    # WEEK 2.5: Validate request size to prevent memory exhaustion attacks
    try:
        validate_content_generation_request(event, max_size_mb=10, max_scenes=100)
    except RequestSizeTooLargeError as e:
        print(f" Request validation failed: {e}")
        return {
            'statusCode': 413,  # Payload Too Large
            'error': f'Request too large: {str(e)}',
            'user_id': user_id
        }

    channel_id = event.get('channel_id', 'Unknown')
    selected_topic = event.get('selected_topic', 'Default Topic')
    wikipedia_facts = event.get('wikipedia_facts', None)
    has_real_facts = event.get('has_real_facts', False)

    if has_real_facts and wikipedia_facts:
        print(f" Factual mode: Wikipedia facts available ({wikipedia_facts.get('char_count', 0)} chars)")
    else:
        print(" Fictional mode: no Wikipedia facts")

    try:
        # 1. Get OpenAI API key
        api_key_response = secrets_client.get_secret_value(SecretId='openai/api-key')
        secret_string = api_key_response['SecretString']
        try:
            api_key_data = json.loads(secret_string)
            api_key = api_key_data.get('api_key') or api_key_data.get('key')
        except:
            api_key = secret_string

        print(f" API key retrieved")

        # 2. Get ChannelConfig
        channel_table = dynamodb.Table('ChannelConfigs')
        channel_response = channel_table.query(
            IndexName='channel_id-index',
            KeyConditionExpression=Key('channel_id').eq(channel_id)
        )

        if not channel_response.get('Items'):
            raise Exception(f'Channel config not found for {channel_id}')

        channel_config = channel_response['Items'][0]

        # WEEK 2 FIX: IDOR prevention - verify channel belongs to user
        if channel_config.get('user_id') != user_id:
            print(f" SECURITY ERROR: Channel {channel_id} belongs to user {channel_config.get('user_id')}, not {user_id}")
            raise ValueError(f"SECURITY: Access denied - Channel does not belong to user {user_id}")

        print(f" Channel loaded: {channel_config.get('channel_name', 'Unknown')}")

        # MANUAL NARRATIVE BYPASS: If channel has manual_mode_enabled=true AND manual_narrative, skip OpenAI and use pre-written story
        manual_mode_enabled = channel_config.get('manual_mode_enabled') in ['true', True, '1', 1]
        manual_narrative = channel_config.get('manual_narrative')
        print(f" DEBUG: manual_mode_enabled={channel_config.get('manual_mode_enabled')} → {manual_mode_enabled}")
        print(f" DEBUG: manual_narrative exists={bool(manual_narrative)} length={len(str(manual_narrative)) if manual_narrative else 0}")
        if manual_mode_enabled and manual_narrative:
            print(" MANUAL NARRATIVE MODE: Using pre-written story from channel config")
            if isinstance(manual_narrative, str):
                import json as _json
                manual_narrative = _json.loads(manual_narrative)
            scenes = manual_narrative.get('scenes', [])
            story_title = manual_narrative.get('story_title', selected_topic)
            timestamp = datetime.utcnow().isoformat() + 'Z'
            narrative_id = timestamp.replace(':', '').replace('-', '').replace('.', '')[:20]
            narrative_text = '\n'.join([s.get('scene_narration', '') for s in scenes])
            return {
                'channel_id': channel_id,
                'content_id': narrative_id,
                'selected_topic': selected_topic,
                'story_title': story_title,
                'narrative_content': manual_narrative,
                'narrative_id': narrative_id,
                'scenes': scenes,
                'image_data': {'scenes': scenes},
                'thumbnail_data': manual_narrative.get('thumbnail_data', {
                    'thumbnail_prompt': story_title + ' dark fantasy cinematic',
                    'text_overlay': story_title,
                    'style_notes': 'dark fantasy'
                }),
                'cta_data': manual_narrative.get('cta_data', {'cta_segments': []}),
                'description_data': manual_narrative.get('description_data', {
                    'title': story_title,
                    'description': narrative_text[:500],
                    'tags': [],
                    'hashtags': []
                }),
                'sfx_data': manual_narrative.get('sfx_data', {
                    'sfx_cues': [],
                    'music_track': 'dark_ambient',
                    'timing_estimates': {}
                }),
                'image_provider': manual_narrative.get('image_provider', channel_config.get('image_provider', 'ec2-sd35')),
                'voice_config': {
                    'language': channel_config.get('language', 'uk'),
                    'speaker': channel_config.get('tts_voice_speaker') or 'serena',
                },
                'model': 'manual',
                'genre': channel_config.get('genre'),
                'character_count': len(narrative_text),
                'scene_count': len(scenes),
                'timestamp': timestamp
            }

        # 2.5. Build MEGA configuration (Templates system removed)
        print("\n Building mega configuration...")
        try:
            mega_config = merge_mega_configuration(channel_config)
        except Exception as merge_error:
            print(f"ERROR in merge_mega_configuration: {merge_error}")
            import traceback
            traceback.print_exc()
            raise

        print(f" Mega config created")
        print(f"   Model: {mega_config['model']}")
        print(f"   Temp: {mega_config['temperature']}")
        print(f"   Max tokens: {mega_config['max_tokens']}")

        # 5. Build MEGA prompt
        print("\n Building MEGA prompt...")
        try:
            system_message, user_message = build_mega_prompt(mega_config, selected_topic, wikipedia_facts)
        except Exception as prompt_error:
            print(f"ERROR in build_mega_prompt: {prompt_error}")
            import traceback
            traceback.print_exc()
            raise

        print(f" MEGA prompt built")
        print(f"   System message: {len(system_message)} chars")
        print(f"   User message: {len(user_message)} chars")

        # 6. Call OpenAI (with caching - WEEK 5)
        print("\n Checking OpenAI response cache...")

        # Build cache key from prompt
        cache_key_prompt = system_message + user_message

        # Check cache first
        cached_result = get_cached_response(cache_key_prompt, mega_config['model'], max_age_hours=24)

        if cached_result:
            print(" Cache HIT - using cached OpenAI response (saved API call!)")
            result = cached_result
        else:
            print(" Cache MISS - calling OpenAI API...")
            request_body = json.dumps({
                'model': mega_config['model'],
                'messages': [
                    {'role': 'system', 'content': system_message},
                    {'role': 'user', 'content': user_message}
                ],
                'temperature': mega_config['temperature'],
                'max_tokens': mega_config['max_tokens'],
                'response_format': {'type': 'json_object'}
            })

            # SECURITY FIX: Add SSL/TLS verification and timeout
            import ssl
            ssl_context = ssl.create_default_context()
            conn = http.client.HTTPSConnection('api.openai.com', context=ssl_context, timeout=240)
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }

            try:
                conn.request('POST', '/v1/chat/completions', body=request_body, headers=headers)
                response = conn.getresponse()
                response_data = response.read().decode('utf-8')
            finally:
                conn.close()  # Ensure connection is closed

            print(f" OpenAI response: {response.status}")

            result = json.loads(response_data)

            if 'error' in result:
                raise Exception(f"OpenAI API Error: {result['error'].get('message', 'Unknown')}")

            # Cache the successful response (TTL: 7 days)
            cache_response(cache_key_prompt, mega_config['model'], result, ttl_hours=168)
            print(" Response cached for future use")

        # 7. Parse MEGA response
        print("\n Parsing MEGA response...")
        generated_content = result['choices'][0]['message']['content']
        mega_response = json.loads(generated_content)

        # Extract components
        story_title = mega_response.get('story_title', selected_topic)
        scenes = mega_response.get('scenes', [])
        cta_segments = mega_response.get('cta_segments', [])
        thumbnail = mega_response.get('thumbnail', {})
        description_data = mega_response.get('description', {})
        sfx_data = mega_response.get('sfx_data', {})
        metadata = mega_response.get('metadata', {})

        # Ensure mega_response has all required fields for Step Functions JSONPath
        # This prevents JSONPath errors when fields are missing
        mega_response.setdefault('cta_segments', [])
        mega_response.setdefault('description', {})
        mega_response.setdefault('thumbnail', {})
        mega_response.setdefault('metadata', {})

        print(f" Parsed MEGA response:")
        print(f"   Title: {story_title}")
        print(f"   Scenes: {len(scenes)}")
        print(f"   Image prompts: {len([s for s in scenes if s.get('image_prompt')])}")
        print(f"   CTA segments: {len(cta_segments)}")
        print(f"   Has thumbnail: {bool(thumbnail.get('thumbnail_prompt'))}")
        print(f"   SFX cues: {len(sfx_data.get('sfx_cues', []))}")
        print(f"   Music track: {sfx_data.get('music_track', 'None')}")

        # Calculate character count
        narrative_text = '\n'.join([s.get('scene_narration', '') for s in scenes])
        character_count = len(narrative_text)

        # 8. Log cost
        usage = result.get('usage', {})
        input_tokens = usage.get('prompt_tokens', 0)
        output_tokens = usage.get('completion_tokens', 0)

        timestamp = datetime.utcnow().isoformat() + 'Z'
        narrative_id = timestamp.replace(':', '').replace('-', '').replace('.', '')[:20]

        cost_usd = log_openai_cost(
            channel_id=channel_id,
            content_id=narrative_id,
            model=mega_config['model'],
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            user_id=user_id  # WEEK 2 FIX: Multi-tenant cost tracking
        )

        # 9. Save to DynamoDB
        print("\n Saving to DynamoDB...")
        content_table = dynamodb.Table('GeneratedContent')

        # Convert all floats to Decimal for DynamoDB
        scenes_decimal = convert_floats_to_decimal(scenes)
        mega_response_decimal = convert_floats_to_decimal(mega_response)

        content_table.put_item(
            Item={
                'channel_id': channel_id,
                'created_at': timestamp,
                'type': 'mega_generation',
                'topic': selected_topic,
                'story_title': story_title,
                'narrative_text': narrative_text,
                'character_count': character_count,
                'scene_count': len(scenes),
                'scenes': scenes_decimal,
                'full_response': mega_response_decimal,
                'model': mega_config['model'],
                'api_version': 'mega_v3',
                'status': 'completed',
                'cost_usd': Decimal(str(cost_usd)),
                'tokens_used': input_tokens + output_tokens
            }
        )

        print(f" Saved to DynamoDB")

        # 10. Get image provider from channel config (Templates system removed)
        image_generation_config = channel_config.get('image_generation', {})
        image_provider = image_generation_config.get('provider', 'ec2-sd35')

        # 11. Return output for Step Functions
        print("\n Building output...")

        output = {
            'channel_id': channel_id,
            'content_id': narrative_id,
            'selected_topic': selected_topic,
            'story_title': story_title,
            'narrative_content': mega_response,
            'narrative_id': narrative_id,
            'scenes': scenes,

            # Image data for collect-image-prompts
            'image_data': {
                'scenes': scenes  # Scenes have image_prompt from MEGA response
            },

            # Thumbnail data for collect-image-prompts
            'thumbnail_data': {
                'thumbnail_prompt': thumbnail.get('thumbnail_prompt', ''),
                'text_overlay': thumbnail.get('text_overlay', ''),
                'style_notes': thumbnail.get('style_notes', '')
            },

            # CTA data for SaveFinalContent
            'cta_data': {
                'cta_segments': cta_segments
            },

            # Description data for SaveFinalContent
            'description_data': {
                'title': description_data.get('title', story_title),
                'description': description_data.get('description', ''),
                'tags': description_data.get('tags', []),
                'hashtags': description_data.get('hashtags', [])
            },

            # SFX data for SaveFinalContent
            'sfx_data': {
                'sfx_cues': sfx_data.get('sfx_cues', []),
                'music_track': sfx_data.get('music_track', ''),
                'timing_estimates': sfx_data.get('timing_estimates', {})
            },

            # Provider for Step Functions
            'image_provider': image_provider,

            # Voice config for collect-audio-scenes
            'voice_config': {
                'language': channel_config.get('language', 'en'),
                'speaker': channel_config.get('tts_voice_speaker') or 'Ryan',
            },

            # Metadata for SaveFinalContent (genre & model)
            'model': mega_config['model'],
            'genre': channel_config.get('genre'),

            'character_count': character_count,
            'scene_count': len(scenes),
            'timestamp': timestamp
        }

        print(f"\n" + "=" * 80)
        print(f" SUCCESS - MEGA-GENERATION COMPLETE")
        print(f"   Scenes: {len(scenes)}")
        print(f"   Image prompts: {len([s for s in scenes if s.get('image_prompt')])}")
        print(f"   Thumbnail: {'Yes' if thumbnail.get('thumbnail_prompt') else 'No'}")
        print(f"   Provider: {image_provider}")
        print(f"   Cost: ${cost_usd:.6f}")
        print("=" * 80)

        return output

    except Exception as e:
        print(f"\n ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

        # Fallback error response
        timestamp_err = datetime.utcnow().isoformat() + 'Z'
        narrative_id_err = timestamp_err.replace(':', '').replace('-', '').replace('.', '')[:20]

        return {
            'channel_id': channel_id,
            'content_id': narrative_id_err,
            'selected_topic': selected_topic,
            'story_title': selected_topic,
            'narrative_content': {},
            'narrative_id': narrative_id_err,
            'scenes': [],
            'image_data': {'scenes': []},
            'thumbnail_data': {'thumbnail_prompt': ''},
            'cta_data': {'cta_segments': []},
            'description_data': {},
            'sfx_data': {},
            'image_provider': 'ec2-sd35',
            'model': 'gpt-4o',
            'genre': event.get('genre', 'Unknown'),
            'character_count': 0,
            'scene_count': 0,
            'timestamp': timestamp_err,
            'error': str(e)
        }
