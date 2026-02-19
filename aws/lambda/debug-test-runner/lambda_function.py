import json
import boto3
import time
from datetime import datetime
from decimal import Decimal
from boto3.dynamodb.conditions import Key

# AWS Clients
lambda_client = boto3.client('lambda', region_name='eu-central-1')
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')

def lambda_handler(event, context):
    """
    Debug Test Runner - Sequentially invokes all content generation Lambda functions
    and collects detailed information about each step.

    Input:
    {
        "channel_id": "UCRmO5HB89GW...",
        "topic": "Optional topic" (if not provided, theme-agent will generate)
    }

    Output:
    {
        "success": true/false,
        "steps": [
            {
                "step_number": 1,
                "step_name": "get-channel-config",
                "status": "completed",
                "duration_ms": 234,
                "input": {...},
                "output": {...},
                "error": null
            },
            ...
        ],
        "summary": {
            "total_duration_ms": 12345,
            "total_cost_usd": 0.025,
            "scene_count": 18,
            "character_count": 8756
        }
    }
    """

    print(f" DEBUG TEST RUNNER - Starting")
    print(f"Event: {json.dumps(event, ensure_ascii=False, default=str)}")

    # Parse input - handle both direct invocation and Lambda URL (body as string)
    if 'body' in event:
        # Lambda Function URL - body is a JSON string
        try:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        except json.JSONDecodeError:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'success': False,
                    'error': 'Invalid JSON in request body'
                })
            }
    else:
        # Direct Lambda invocation
        body = event

    channel_id = body.get('channel_id')
    user_id = body.get('user_id')
    topic = body.get('topic', '')

    if not channel_id:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'success': False,
                'error': 'channel_id is required'
            })
        }

    if not user_id:
        return {
            'statusCode': 400,
            'body': json.dumps({
                'success': False,
                'error': 'user_id is required'
            })
        }

    # Initialize results
    test_start_time = time.time()
    steps = []
    total_cost = 0.0
    test_data = {}  # Store data between steps

    try:
        # Step 1: Get Channel Configuration
        step1_result = run_step(
            step_number=1,
            step_name='get-channel-config',
            lambda_function='content-get-channels',
            payload={'action': 'get_active', 'user_id': user_id},
            description='Fetching channel configuration from ChannelConfigs'
        )
        steps.append(step1_result)

        if step1_result['status'] != 'completed':
            raise Exception(f"Step 1 failed: {step1_result.get('error')}")

        # Extract channel config - handle both list and dict responses
        output = step1_result['output']
        if isinstance(output, list):
            channels = output
        elif isinstance(output, dict):
            channels = output.get('channels', [])
        else:
            raise Exception(f"Unexpected output format from content-get-channels: {type(output)}")

        channel_config = next((ch for ch in channels if ch['channel_id'] == channel_id), None)

        if not channel_config:
            raise Exception(f"Channel {channel_id} not found in active channels")

        test_data['channel_config'] = channel_config
        print(f" Step 1: Channel config loaded - {channel_config.get('channel_name', 'Unknown')}")


        # Step 2: Generate Theme
        step2_payload = {
            'channel_id': channel_id,
            'selected_topic': topic if topic else None
        }

        step2_result = run_step(
            step_number=2,
            step_name='generate-theme',
            lambda_function='content-theme-agent',
            payload=step2_payload,
            description='Generating content theme using AI'
        )
        steps.append(step2_result)

        if step2_result['status'] != 'completed':
            raise Exception(f"Step 2 failed: {step2_result.get('error')}")

        theme_output = step2_result['output']
        test_data['theme'] = theme_output
        total_cost += float(theme_output.get('cost_usd', 0))

        print(f" Step 2: Theme generated - {theme_output.get('selected_topic', 'Unknown')}")


        # Step 3: Generate Narrative
        step3_payload = {
            'channel_id': channel_id,
            'selected_topic': theme_output.get('selected_topic', topic),
            # Optional overrides for testing
            'target_character_count': event.get('target_character_count'),
            'scene_count_target': event.get('scene_count_target')
        }

        step3_result = run_step(
            step_number=3,
            step_name='generate-narrative',
            lambda_function='content-narrative',
            payload=step3_payload,
            description='Generating narrative script with scenes'
        )
        steps.append(step3_result)

        if step3_result['status'] != 'completed':
            raise Exception(f"Step 3 failed: {step3_result.get('error')}")

        narrative_output = step3_result['output']
        test_data['narrative'] = narrative_output
        total_cost += float(narrative_output.get('cost_usd', 0))

        print(f" Step 3: Narrative generated - {narrative_output.get('scene_count', 0)} scenes")


        # Step 4: Generate Audio (TTS)
        narrative_data = narrative_output.get('narrative_data', {})
        step4_payload = {
            'channel_id': channel_id,
            'narrative_id': narrative_output.get('content_id'),
            'scenes': narrative_data.get('scenes', []),
            'story_title': narrative_data.get('story_title', 'Untitled')
        }

        step4_result = run_step(
            step_number=4,
            step_name='generate-audio',
            lambda_function='content-audio-tts',
            payload=step4_payload,
            description='Generating audio files using AWS Polly'
        )
        steps.append(step4_result)

        if step4_result['status'] != 'completed':
            raise Exception(f"Step 4 failed: {step4_result.get('error')}")

        audio_output = step4_result['output']
        test_data['audio'] = audio_output
        total_cost += float(audio_output.get('cost_usd', 0))

        print(f" Step 4: Audio generated - {audio_output.get('scene_count', 0)} files, {audio_output.get('total_duration_sec', 0)}s")


        # Step 5: Generate Images
        step5_payload = {
            'channel_id': channel_id,
            'narrative_id': narrative_output.get('content_id'),
            'story_title': narrative_data.get('story_title', 'Untitled'),
            'scenes': narrative_data.get('scenes', [])
        }

        step5_result = run_step(
            step_number=5,
            step_name='generate-images',
            lambda_function='content-generate-images',
            payload=step5_payload,
            description='Generating images for all scenes'
        )
        steps.append(step5_result)

        if step5_result['status'] != 'completed':
            raise Exception(f"Step 5 failed: {step5_result.get('error')}")

        image_output = step5_result['output']
        test_data['images'] = image_output
        total_cost += float(image_output.get('total_cost_usd', 0))

        print(f" Step 5: Images generated - {image_output.get('images_generated', 0)} images, ${image_output.get('total_cost_usd', 0)}")


        # Step 6: Save Result
        step6_payload = {
            'channel_id': channel_id,
            'narrative_id': narrative_output.get('narrative_id'),
            'theme_data': theme_output,
            'narrative_data': narrative_output,
            'audio_data': audio_output,
            'image_data': image_output
        }

        step6_result = run_step(
            step_number=6,
            step_name='save-result',
            lambda_function='content-save-result',
            payload=step6_payload,
            description='Saving final result to GeneratedContent'
        )
        steps.append(step6_result)

        if step6_result['status'] != 'completed':
            print(f"  Step 6 warning: {step6_result.get('error')}")
            # Don't fail the whole test if save fails
        else:
            print(f" Step 6: Result saved")


        # Calculate total duration
        test_end_time = time.time()
        total_duration_ms = int((test_end_time - test_start_time) * 1000)

        # Build summary
        summary = {
            'total_duration_ms': total_duration_ms,
            'total_duration_sec': round(total_duration_ms / 1000, 2),
            'total_cost_usd': round(total_cost, 6),
            'scene_count': len(narrative_data.get('scenes', [])),
            'character_count': narrative_output.get('character_count', 0),
            'audio_duration_sec': audio_output.get('total_duration_sec', 0),
            'images_generated': image_output.get('images_generated', 0),
            'narrative_id': narrative_output.get('narrative_id'),
            'story_title': narrative_output.get('story_title', 'Untitled')
        }

        print(f" TEST COMPLETED SUCCESSFULLY")
        print(f"   Duration: {summary['total_duration_sec']}s")
        print(f"   Cost: ${summary['total_cost_usd']}")
        print(f"   Scenes: {summary['scene_count']}")
        print(f"   Images: {summary['images_generated']}")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'steps': steps,
                'summary': summary,
                'test_data': {
                    'channel_name': channel_config.get('channel_name', 'Unknown'),
                    'channel_id': channel_id,
                    'topic': theme_output.get('selected_topic', topic)
                }
            }, ensure_ascii=False, default=decimal_default)
        }

    except Exception as e:
        print(f" TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()

        test_end_time = time.time()
        total_duration_ms = int((test_end_time - test_start_time) * 1000)

        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': str(e),
                'steps': steps,
                'summary': {
                    'total_duration_ms': total_duration_ms,
                    'total_duration_sec': round(total_duration_ms / 1000, 2),
                    'total_cost_usd': round(total_cost, 6)
                }
            }, ensure_ascii=False, default=decimal_default)
        }


def run_step(step_number, step_name, lambda_function, payload, description):
    """
    Run a single step by invoking a Lambda function and collecting results

    Returns:
    {
        'step_number': 1,
        'step_name': 'get-channel-config',
        'lambda_function': 'content-get-channels',
        'description': '...',
        'status': 'completed' | 'failed',
        'duration_ms': 234,
        'input': {...},
        'output': {...},
        'error': null | 'error message',
        'timestamp': '2025-11-05T...'
    }
    """
    print(f"\n{'='*60}")
    print(f"STEP {step_number}: {step_name}")
    print(f"Lambda: {lambda_function}")
    print(f"Description: {description}")
    print(f"{'='*60}")

    step_start_time = time.time()
    timestamp = datetime.utcnow().isoformat() + 'Z'

    try:
        # Invoke Lambda function
        print(f" Invoking {lambda_function}...")
        print(f"Payload: {json.dumps(payload, ensure_ascii=False, default=str)}")

        response = lambda_client.invoke(
            FunctionName=lambda_function,
            InvocationType='RequestResponse',
            Payload=json.dumps(payload, default=str)
        )

        # Parse response
        response_payload = json.loads(response['Payload'].read().decode('utf-8'))

        # Calculate duration
        step_end_time = time.time()
        duration_ms = int((step_end_time - step_start_time) * 1000)

        # Check if Lambda returned an error
        if response.get('FunctionError'):
            error_message = response_payload.get('errorMessage', 'Unknown error')
            print(f" Lambda error: {error_message}")

            return {
                'step_number': step_number,
                'step_name': step_name,
                'lambda_function': lambda_function,
                'description': description,
                'status': 'failed',
                'duration_ms': duration_ms,
                'input': payload,
                'output': None,
                'error': error_message,
                'timestamp': timestamp
            }

        # Success
        print(f" Step completed in {duration_ms}ms")

        return {
            'step_number': step_number,
            'step_name': step_name,
            'lambda_function': lambda_function,
            'description': description,
            'status': 'completed',
            'duration_ms': duration_ms,
            'input': payload,
            'output': response_payload,
            'error': None,
            'timestamp': timestamp
        }

    except Exception as e:
        step_end_time = time.time()
        duration_ms = int((step_end_time - step_start_time) * 1000)

        error_message = str(e)
        print(f" Exception: {error_message}")

        return {
            'step_number': step_number,
            'step_name': step_name,
            'lambda_function': lambda_function,
            'description': description,
            'status': 'failed',
            'duration_ms': duration_ms,
            'input': payload,
            'output': None,
            'error': error_message,
            'timestamp': timestamp
        }


def decimal_default(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
