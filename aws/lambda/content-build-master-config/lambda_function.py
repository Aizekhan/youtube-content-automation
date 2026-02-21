"""
Content Build Master Config Lambda
Sprint 1 - Task 1.9
Sprint 2 Enhancement - Integrates enrichment Lambdas

Functionality:
- Load channel config from DynamoDB
- Optionally load topic from ContentTopicsQueue
- Run Sprint 2 enrichment pipeline (topic analysis, context enrichment, story DNA, facts)
- Merge channel + topic + story profile + enrichments into MasterConfig
- Return comprehensive config for content generation
"""

import json
import boto3
from decimal import Decimal
from botocore.config import Config

# AWS clients with timeout configuration
boto_config = Config(
    connect_timeout=5,
    read_timeout=60,
    retries={'max_attempts': 3, 'mode': 'standard'}
)

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1', config=boto_config)
lambda_client = boto3.client('lambda', region_name='eu-central-1', config=boto_config)
channels_table = dynamodb.Table('ChannelConfigs')
topics_table = dynamodb.Table('ContentTopicsQueue')


def decimal_default(obj):
    """Helper to convert Decimal to int/float for JSON serialization"""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    raise TypeError


def invoke_lambda_sync(function_name, payload):
    """
    Invoke Lambda synchronously and parse response

    Args:
        function_name: Name of Lambda function to invoke
        payload: Dictionary payload to send

    Returns:
        Parsed response dictionary or None on error
    """
    try:
        print(f"  Invoking {function_name}...")

        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )

        # Read response payload
        response_payload = json.loads(response['Payload'].read())

        # Handle API Gateway format (has 'body' field)
        if 'body' in response_payload:
            if isinstance(response_payload['body'], str):
                response_data = json.loads(response_payload['body'])
            else:
                response_data = response_payload['body']
        else:
            # Direct Lambda response
            response_data = response_payload

        print(f"  {function_name} completed successfully")
        return response_data

    except Exception as e:
        print(f"  Error invoking {function_name}: {e}")
        import traceback
        traceback.print_exc()
        return None


def lambda_handler(event, context):
    """
    Build MasterConfig from channel + topic data

    Input:
    {
      "user_id": "xxx",
      "channel_id": "UCxxx",
      "topic_id": "topic_xxx"  // optional
    }

    Output:
    {
      "success": true,
      "master_config": {
        "channel_id": "...",
        "channel_name": "...",
        "language": "uk",
        "story_profile": {
          "world_type": "realistic",
          "tone": "dark",
          "psychological_depth": 3,
          "plot_intensity": 4,
          "character_mode": "auto_generate",
          "character_archetype": "anti_hero"
        },
        "topic": {
          "topic_id": "...",
          "topic_text": "...",
          "topic_description": {
            "context": "...",
            "tone_suggestion": "dark",
            "key_elements": ["...", "..."]
          }
        },
        "all_channel_fields": {...}  // full channel config for backward compatibility
      }
    }
    """

    print("=" * 80)
    print("Build Master Config Lambda")
    print("=" * 80)
    print(f"Event: {json.dumps(event, default=str)[:500]}")

    # Extract parameters
    user_id = event.get('user_id')
    channel_id = event.get('channel_id')
    topic_id = event.get('topic_id')  # Optional

    # Validation
    if not user_id:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'success': False,
                'error': 'user_id is required'
            })
        }

    if not channel_id:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'success': False,
                'error': 'channel_id is required'
            })
        }

    print(f"\nBuilding MasterConfig:")
    print(f"  user_id: {user_id}")
    print(f"  channel_id: {channel_id}")
    print(f"  topic_id: {topic_id or 'None (will auto-generate)'}")

    try:
        # 1. Load Channel Config
        print(f"\n  Loading channel config...")

        channel_response = channels_table.get_item(
            Key={
                'user_id': user_id,
                'channel_id': channel_id
            }
        )

        if 'Item' not in channel_response:
            print(f"  CHANNEL_NOT_FOUND")
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'success': False,
                    'error': 'CHANNEL_NOT_FOUND',
                    'message': f'Channel {channel_id} not found for user {user_id}'
                })
            }

        channel_config = channel_response['Item']
        print(f"  Channel loaded: {channel_config.get('channel_name', 'N/A')}")

        # 2. Extract Story Profile from channel
        story_profile = {
            'world_type': channel_config.get('world_type', 'realistic'),
            'tone': channel_config.get('tone', 'dark'),
            'psychological_depth': int(channel_config.get('psychological_depth', 3)),
            'plot_intensity': int(channel_config.get('plot_intensity', 4)),
            'character_mode': channel_config.get('character_mode', 'auto_generate'),
            'character_archetype': channel_config.get('character_archetype', 'anti_hero'),
            'enable_internal_conflict': channel_config.get('enable_internal_conflict', True),
            'enable_secret': channel_config.get('enable_secret', False),
            'moral_dilemma_level': int(channel_config.get('moral_dilemma_level', 3))
        }

        print(f"\n  Story Profile:")
        print(f"    world_type: {story_profile['world_type']}")
        print(f"    tone: {story_profile['tone']}")
        print(f"    psychological_depth: {story_profile['psychological_depth']}")
        print(f"    plot_intensity: {story_profile['plot_intensity']}")

        # 3. Load Topic (if provided)
        topic_data = None

        if topic_id:
            print(f"\n  Loading topic: {topic_id}")

            topic_response = topics_table.get_item(
                Key={
                    'channel_id': channel_id,
                    'topic_id': topic_id
                }
            )

            if 'Item' in topic_response:
                topic_item = topic_response['Item']

                # Security: verify user_id
                if topic_item.get('user_id') != user_id:
                    print(f"  ACCESS_DENIED - wrong user_id")
                    return {
                        'statusCode': 403,
                        'body': json.dumps({
                            'success': False,
                            'error': 'ACCESS_DENIED',
                            'message': 'Topic belongs to different user'
                        })
                    }

                topic_data = {
                    'topic_id': topic_item.get('topic_id'),
                    'topic_text': topic_item.get('topic_text'),
                    'topic_description': topic_item.get('topic_description', {}),
                    'status': topic_item.get('status'),
                    'priority': int(topic_item.get('priority', 100)),
                    'source': topic_item.get('source', 'manual')
                }

                print(f"  Topic loaded: {topic_data['topic_text']}")
                print(f"  Topic tone suggestion: {topic_data['topic_description'].get('tone_suggestion', 'N/A')}")
            else:
                print(f"  Topic not found, will proceed without topic")
        else:
            print(f"\n  No topic_id provided, MasterConfig will not include topic")

        # 4. Sprint 2 Enrichment Pipeline
        topic_analysis = None
        enriched_context = None
        story_dna = None
        wikipedia_facts = None

        if topic_data:
            print(f"\n  Running Sprint 2 enrichment pipeline...")

            topic_text = topic_data.get('topic_text', '')
            topic_description = topic_data.get('topic_description', {})
            tone_suggestion = topic_description.get('tone_suggestion', story_profile['tone'])

            # 4.1 Topic Analyzer
            topic_analysis = invoke_lambda_sync(
                'content-topic-analyzer',
                {
                    'topic_text': topic_text,
                    'topic_description': topic_description,
                    'story_profile': story_profile
                }
            )

            # 4.2 Search Facts (only if factual_mode enabled)
            if channel_config.get('factual_mode', False):
                print(f"  Factual mode enabled, searching Wikipedia facts...")
                wikipedia_facts = invoke_lambda_sync(
                    'content-search-facts',
                    {
                        'topic_text': topic_text,
                        'max_results': 10
                    }
                )

            # 4.3 Context Enrichment
            genre = None
            if topic_analysis and 'genre' in topic_analysis:
                genre = topic_analysis['genre']

            enriched_context = invoke_lambda_sync(
                'content-context-enrichment',
                {
                    'topic_text': topic_text,
                    'tone_suggestion': tone_suggestion,
                    'genre': genre,
                    'world_type': story_profile['world_type']
                }
            )

            # 4.4 Story DNA Generator
            story_dna = invoke_lambda_sync(
                'content-story-dna-generator',
                {
                    'topic_text': topic_text,
                    'genre': genre,
                    'story_type': 'narrative',
                    'tone_suggestion': tone_suggestion,
                    'complexity_level': story_profile.get('psychological_depth', 3)
                }
            )

            print(f"  Sprint 2 enrichment pipeline completed")

        # 5. Build MasterConfig
        master_config = {
            'channel_id': channel_id,
            'user_id': user_id,
            'channel_name': channel_config.get('channel_name', ''),
            'language': channel_config.get('language', 'uk'),
            'story_profile': story_profile,
            'all_channel_fields': channel_config  # Full config for backward compatibility
        }

        # Add topic if available
        if topic_data:
            master_config['topic'] = topic_data

        # Add Sprint 2 enrichment data
        if topic_analysis:
            master_config['topic_analysis'] = topic_analysis
        if enriched_context:
            master_config['enriched_context'] = enriched_context
        if story_dna:
            master_config['story_dna'] = story_dna
        if wikipedia_facts:
            master_config['wikipedia_facts'] = wikipedia_facts

        print(f"\n  MasterConfig built successfully")
        print(f"  Size: {len(json.dumps(master_config, default=decimal_default))} bytes")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'master_config': master_config
            }, default=decimal_default)
        }

    except Exception as e:
        print(f"  Error building MasterConfig: {e}")
        import traceback
        traceback.print_exc()

        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': f'Failed to build MasterConfig: {str(e)}'
            })
        }
