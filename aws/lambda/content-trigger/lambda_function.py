"""
Lambda Function: content-trigger
Description: Manual trigger for ContentGenerator Step Functions workflow
Multi-tenant version - requires user_id
"""

import json
import boto3
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS clients
stepfunctions = boto3.client('stepfunctions')
dynamodb = boto3.resource('dynamodb')

# Configuration
STATE_MACHINE_ARN = 'arn:aws:states:eu-central-1:599297130956:stateMachine:ContentGenerator'
CHANNELS_TABLE = dynamodb.Table('ChannelConfigs')

def lambda_handler(event, context):
    """Manual trigger for content generation workflow (Multi-tenant)"""
    try:
        logger.info(' Content Trigger Lambda started')
        logger.info(f' Event: {json.dumps(event, default=str)}')

        # Parse request
        body = event.get('body')
        if body and isinstance(body, str):
            body = json.loads(body)
        else:
            body = event

        # Get user_id (REQUIRED)
        user_id = body.get('user_id') or event.get('user_id')
        if not user_id:
            logger.error(' Missing user_id')
            return error_response(400, 'user_id is required')

        channels_input = body.get('channels', 'all')
        options = body.get('options', {})
        dry_run = options.get('dry_run', False)
        force = options.get('force', False)

        logger.info(f' User ID: {user_id}')
        logger.info(f' Channels: {channels_input}')

        # Get channel IDs
        if channels_input == 'all':
            channel_ids = get_all_active_channels(user_id)
        elif isinstance(channels_input, list):
            channel_ids = channels_input
        else:
            return error_response(400, 'Invalid channels parameter')

        if not channel_ids:
            return error_response(400, f'No active channels for user {user_id}')

        logger.info(f' Found {len(channel_ids)} channels')

        if dry_run:
            return success_response({
                'success': True,
                'dry_run': True,
                'user_id': user_id,
                'channels_count': len(channel_ids)
            })

        # Start Step Functions
        execution_name = f'manual-trigger-{datetime.utcnow().strftime("%Y%m%d-%H%M%S")}'

        response = stepfunctions.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            name=execution_name,
            input=json.dumps({
                'user_id': user_id,
                'trigger_type': 'manual',
                'trigger_time': datetime.utcnow().isoformat(),
                'force': force,
                'requested_channels': channel_ids if channels_input != 'all' else None
            })
        )

        logger.info(f' Started: {response["executionArn"]}')

        return success_response({
            'success': True,
            'user_id': user_id,
            'execution_arn': response['executionArn'],
            'execution_name': execution_name,
            'channels_count': len(channel_ids),
            'started_at': response['startDate'].isoformat()
        })

    except Exception as e:
        logger.error(f' Error: {str(e)}', exc_info=True)
        return error_response(500, str(e))


def get_all_active_channels(user_id):
    """Get active channels for user"""
    try:
        response = CHANNELS_TABLE.query(
            IndexName='user_id-channel_id-index',
            KeyConditionExpression='user_id = :uid',
            FilterExpression='is_active = :active',
            ExpressionAttributeValues={
                ':uid': user_id,
                ':active': True
            }
        )

        channels = response.get('Items', [])
        channel_ids = [ch['channel_id'] for ch in channels if 'channel_id' in ch]
        
        logger.info(f' Found {len(channel_ids)} active channels for {user_id}')
        return channel_ids

    except Exception as e:
        logger.error(f' Error: {str(e)}')
        raise


def success_response(data):
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(data, default=str)
    }


def error_response(status_code, message):
    return {
        'statusCode': status_code,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps({'success': False, 'error': message})
    }
