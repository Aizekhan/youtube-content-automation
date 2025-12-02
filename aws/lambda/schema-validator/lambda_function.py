import json
import boto3
from typing import Dict, List, Any
from decimal import Decimal
from datetime import datetime

# ===== AWS CLIENTS =====
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
lambda_client = boto3.client('lambda', region_name='eu-central-1')
stepfunctions_client = boto3.client('stepfunctions', region_name='eu-central-1')

# ===== FRONTEND EXPECTATIONS =====
FRONTEND_EXPECTATIONS = {
    "populateStory": {
        "required_paths": [
            "narrative_data.scenes[].text_with_ssml",
            "narrative_data.scenes[].scene_number",
            "narrative_data.scenes[].scene_title",
            "narrative_data.selected_voice",
            "narrative_data.hook"
        ]
    },
    "populateAudio": {
        "required_paths": [
            "sfx_data.scenes[].music_track",
            "sfx_data.scenes[].sfx_cues[]",
            "sfx_data.scenes[].timing_estimates[]"
        ]
    },
    "populateCTA": {
        "required_paths": [
            "cta_data.cta_segments[].type",
            "cta_data.cta_segments[].cta_audio_segment.ssml_text",
            "cta_data.cta_segments[].placement.scene_number"
        ]
    },
    "populateDescription": {
        "required_paths": [
            "description_data.description",
            "description_data.hashtags[]",
            "description_data.timestamps[]"
        ]
    },
    "populateThumbnail": {
        "required_paths": [
            "thumbnail_data.thumbnail_prompt",
            "thumbnail_data.text_overlay"
        ]
    },
    "populateVisuals": {
        "required_paths": [
            "image_data.scenes[].image_prompt",
            "image_data.scenes[].scene_number"
        ]
    },
    "populateVoice": {
        "required_paths": [
            "audio_files[].scene_id",
            "audio_files[].s3_url",
            "audio_files[].duration_ms"
        ]
    }
}

# ===== REQUIRED SYSTEM COMPONENTS =====
REQUIRED_LAMBDA_FUNCTIONS = [
    'content-get-channels',
    'content-query-titles',
    'content-theme-agent',
    'content-narrative',
    'content-audio-tts',
    'content-save-result',
    'content-generate-images',
    'collect-image-prompts',
    'distribute-images',
    'ec2-sd35-control',
    'content-video-assembly',
    'dashboard-content',
    'dashboard-monitoring',
    'dashboard-costs'
]

REQUIRED_DYNAMODB_TABLES = [
    'GeneratedContent',
    'ChannelConfigs',
    'ThemeTemplates',
    'NarrativeTemplates',
    'TTSTemplates',
    'ImageGenerationTemplates',
    'SFXTemplates',
    'CTATemplates',
    'DescriptionTemplates',
    'ThumbnailTemplates',
    'VideoEditingTemplates',
    'CostTracking'
]

STEP_FUNCTION_NAME = 'ContentGenerator'


def decimal_default(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def extract_path(obj: Any, path: str) -> bool:
    """Check if path exists in object"""
    parts = path.replace('[]', '').split('.')
    current = obj

    i = 0
    while i < len(parts):
        part = parts[i]

        # Handle list - take first element but don't advance to next part
        if isinstance(current, list):
            if len(current) > 0:
                current = current[0]
                # Don't increment i - reprocess same part with list element
                continue
            else:
                return False

        # Handle dict - get the key
        elif isinstance(current, dict):
            if part in current:
                current = current[part]
                i += 1  # Move to next part
            else:
                return False

        # Neither dict nor list - invalid
        else:
            return False

    return True


def get_latest_generated_content() -> Dict[str, Any]:
    """Fetch the latest generated content from DynamoDB"""
    try:
        table = dynamodb.Table('GeneratedContent')
        response = table.scan(
            Limit=50,
            FilterExpression='attribute_exists(narrative_data)'
        )

        if not response.get('Items'):
            return {
                'success': False,
                'error': 'No generated content found in DynamoDB',
                'data': None
            }

        # Sort by created_at to get latest
        items = sorted(
            response['Items'],
            key=lambda x: x.get('created_at', ''),
            reverse=True
        )

        latest = items[0]

        return {
            'success': True,
            'data': latest,
            'content_id': latest.get('content_id', 'unknown'),
            'channel_id': latest.get('channel_id', 'unknown'),
            'created_at': latest.get('created_at', 'unknown')
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Failed to fetch content: {str(e)}',
            'data': None
        }


def validate_frontend_expectations(data: Dict) -> Dict[str, Any]:
    """Validate that DynamoDB data matches frontend expectations"""
    results = {
        "all_valid": True,
        "functions": {}
    }

    for function_name, expectations in FRONTEND_EXPECTATIONS.items():
        missing_paths = []

        for path in expectations['required_paths']:
            if not extract_path(data, path):
                missing_paths.append(path)

        results["functions"][function_name] = {
            "valid": len(missing_paths) == 0,
            "missing_paths": missing_paths,
            "required_count": len(expectations['required_paths']),
            "satisfied_count": len(expectations['required_paths']) - len(missing_paths)
        }

        if missing_paths:
            results["all_valid"] = False

    return results


def check_lambda_functions() -> Dict[str, Any]:
    """Check if all required Lambda functions exist"""
    results = {
        'all_exist': True,
        'total_required': len(REQUIRED_LAMBDA_FUNCTIONS),
        'found': 0,
        'missing': [],
        'details': {}
    }

    for func_name in REQUIRED_LAMBDA_FUNCTIONS:
        try:
            response = lambda_client.get_function(FunctionName=func_name)
            results['details'][func_name] = {
                'exists': True,
                'runtime': response['Configuration'].get('Runtime', 'unknown'),
                'last_modified': response['Configuration'].get('LastModified', 'unknown')
            }
            results['found'] += 1
        except lambda_client.exceptions.ResourceNotFoundException:
            results['all_exist'] = False
            results['missing'].append(func_name)
            results['details'][func_name] = {
                'exists': False,
                'error': 'Function not found'
            }
        except Exception as e:
            results['details'][func_name] = {
                'exists': False,
                'error': str(e)
            }

    return results


def check_dynamodb_tables() -> Dict[str, Any]:
    """Check if all required DynamoDB tables exist"""
    results = {
        'all_exist': True,
        'total_required': len(REQUIRED_DYNAMODB_TABLES),
        'found': 0,
        'missing': [],
        'details': {}
    }

    dynamodb_client = boto3.client('dynamodb', region_name='eu-central-1')

    for table_name in REQUIRED_DYNAMODB_TABLES:
        try:
            response = dynamodb_client.describe_table(TableName=table_name)
            results['details'][table_name] = {
                'exists': True,
                'status': response['Table']['TableStatus'],
                'item_count': response['Table'].get('ItemCount', 0)
            }
            results['found'] += 1
        except dynamodb_client.exceptions.ResourceNotFoundException:
            results['all_exist'] = False
            results['missing'].append(table_name)
            results['details'][table_name] = {
                'exists': False,
                'error': 'Table not found'
            }
        except Exception as e:
            results['details'][table_name] = {
                'exists': False,
                'error': str(e)
            }

    return results


def check_variation_sets() -> Dict[str, Any]:
    """Check if variation sets are being tracked properly"""
    results = {
        'variation_sets_working': False,
        'latest_content_has_metadata': False,
        'details': {}
    }

    try:
        # Get latest content
        content_result = get_latest_generated_content()

        if not content_result['success']:
            results['error'] = content_result['error']
            return results

        content = content_result['data']

        # Check if variation set metadata exists
        has_set_name = 'variation_set_name' in content
        has_set_index = 'variation_set_index' in content
        has_gen_count = 'generation_count_at_creation' in content

        results['latest_content_has_metadata'] = has_set_name and has_set_index and has_gen_count
        results['variation_sets_working'] = results['latest_content_has_metadata']

        results['details'] = {
            'has_variation_set_name': has_set_name,
            'has_variation_set_index': has_set_index,
            'has_generation_count_at_creation': has_gen_count,
            'variation_set_name': content.get('variation_set_name', 'NOT FOUND'),
            'variation_set_index': content.get('variation_set_index', 'NOT FOUND'),
            'generation_count_at_creation': content.get('generation_count_at_creation', 'NOT FOUND'),
            'content_id': content_result['content_id']
        }

    except Exception as e:
        results['error'] = str(e)

    return results


def check_step_functions() -> Dict[str, Any]:
    """Check if Step Functions state machine exists and is properly configured"""
    results = {
        'state_machine_exists': False,
        'details': {}
    }

    try:
        # List state machines
        response = stepfunctions_client.list_state_machines()

        # Find ContentGenerator
        state_machine = None
        for sm in response.get('stateMachines', []):
            if sm['name'] == STEP_FUNCTION_NAME:
                state_machine = sm
                break

        if not state_machine:
            results['error'] = f'State machine "{STEP_FUNCTION_NAME}" not found'
            return results

        results['state_machine_exists'] = True
        results['details'] = {
            'name': state_machine['name'],
            'status': state_machine.get('status', 'unknown'),
            'creation_date': state_machine.get('creationDate', '').isoformat() if state_machine.get('creationDate') else 'unknown',
            'arn': state_machine['stateMachineArn']
        }

        # Get detailed definition
        describe_response = stepfunctions_client.describe_state_machine(
            stateMachineArn=state_machine['stateMachineArn']
        )

        definition = json.loads(describe_response['definition'])

        # Check if key states exist
        required_states = [
            'GetActiveChannels',
            'Phase1ContentGeneration',
            'CollectAllImagePrompts',
            'StartEC2ForAllImages',
            'GenerateAllImagesBatched',
            'DistributeImagesToChannels',
            'Phase3AudioAndSave'
        ]

        states = definition.get('States', {})
        missing_states = [s for s in required_states if s not in states]

        results['details']['has_all_required_states'] = len(missing_states) == 0
        results['details']['missing_states'] = missing_states
        results['details']['total_states'] = len(states)

    except Exception as e:
        results['error'] = str(e)

    return results


def lambda_handler(event, context):
    """
    Comprehensive Schema Validator Lambda Function
    Validates entire system: DynamoDB, Lambda functions, Step Functions, variation sets
    """

    print(f"Event: {json.dumps(event, default=str)}")

    try:
        validation_results = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'PASS',
            'checks': {}
        }

        # 1. Get latest real content from DynamoDB
        print("Fetching latest generated content...")
        content_result = get_latest_generated_content()
        validation_results['checks']['real_content_fetch'] = {
            'status': 'PASS' if content_result['success'] else 'FAIL',
            'details': content_result
        }

        if not content_result['success']:
            validation_results['overall_status'] = 'FAIL'

        # 2. Validate frontend expectations against REAL data
        if content_result['success']:
            print("Validating frontend expectations...")
            frontend_validation = validate_frontend_expectations(content_result['data'])
            validation_results['checks']['frontend_expectations'] = {
                'status': 'PASS' if frontend_validation['all_valid'] else 'FAIL',
                'details': frontend_validation
            }

            if not frontend_validation['all_valid']:
                validation_results['overall_status'] = 'FAIL'

        # 3. Check all Lambda functions exist
        print("Checking Lambda functions...")
        lambda_check = check_lambda_functions()
        validation_results['checks']['lambda_functions'] = {
            'status': 'PASS' if lambda_check['all_exist'] else 'FAIL',
            'details': lambda_check
        }

        if not lambda_check['all_exist']:
            validation_results['overall_status'] = 'FAIL'

        # 4. Check all DynamoDB tables exist
        print("Checking DynamoDB tables...")
        tables_check = check_dynamodb_tables()
        validation_results['checks']['dynamodb_tables'] = {
            'status': 'PASS' if tables_check['all_exist'] else 'FAIL',
            'details': tables_check
        }

        if not tables_check['all_exist']:
            validation_results['overall_status'] = 'FAIL'

        # 5. Check variation sets tracking
        print("Checking variation sets...")
        variation_check = check_variation_sets()
        validation_results['checks']['variation_sets'] = {
            'status': 'PASS' if variation_check['variation_sets_working'] else 'FAIL',
            'details': variation_check
        }

        if not variation_check['variation_sets_working']:
            validation_results['overall_status'] = 'FAIL'

        # 6. Check Step Functions
        print("Checking Step Functions...")
        sf_check = check_step_functions()
        validation_results['checks']['step_functions'] = {
            'status': 'PASS' if sf_check['state_machine_exists'] else 'FAIL',
            'details': sf_check
        }

        if not sf_check['state_machine_exists']:
            validation_results['overall_status'] = 'FAIL'

        # Summary
        validation_results['summary'] = {
            'total_checks': len(validation_results['checks']),
            'passed_checks': sum(1 for c in validation_results['checks'].values() if c['status'] == 'PASS'),
            'failed_checks': sum(1 for c in validation_results['checks'].values() if c['status'] == 'FAIL'),
            'all_systems_operational': validation_results['overall_status'] == 'PASS'
        }

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps(validation_results, default=decimal_default)
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'overall_status': 'ERROR',
                'error': str(e),
                'type': 'ValidationError',
                'timestamp': datetime.now().isoformat()
            })
        }
