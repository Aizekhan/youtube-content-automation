import json
import boto3
import hashlib
from datetime import datetime

s3 = boto3.client('s3', region_name='eu-central-1')
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')

S3_BUCKET = 'youtube-automation-audio-files'
CHANNEL_CONFIGS_TABLE = 'ChannelConfigs'

def lambda_handler(event, context):
    """TTS Router - QWEN3-TTS ONLY"""
    
    print("TTS Router - Qwen3-TTS Only")
    
    user_id = event.get('user_id')
    channel_id = event.get('channel_id')
    
    try:
        # Get config
        tts_settings = event.get('tts_settings', {})
        channel_config = get_channel_config(channel_id)
        
        # Merge
        merged_config = {
            'tts_voice_profile': tts_settings.get('tts_voice_profile') or channel_config.get('tts_voice_profile', 'deep_male'),
            'tone': tts_settings.get('tone') or channel_config.get('tone', ''),
            'narration_style': tts_settings.get('narration_style') or channel_config.get('narration_style', ''),
            'language': tts_settings.get('language') or channel_config.get('language', 'English')
        }
        
        print(f"Config: {json.dumps(merged_config)}")
        
        # Invoke Qwen3
        result = invoke_qwen3_provider(event, merged_config, user_id)
        return result if result else {'error': 'Qwen3-TTS failed'}
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e), 'audio_files': [], 'total_duration_ms': 0}


def invoke_qwen3_provider(event, merged_config, user_id):
    """Delegate to Qwen3-TTS"""
    try:
        lambda_client = boto3.client('lambda', region_name='eu-central-1')
        
        # Map voice
        voice_profile = merged_config.get('tts_voice_profile', 'deep_male')
        speaker = map_voice_profile_to_qwen3_speaker(voice_profile)
        
        # Build voice_description
        tone = merged_config.get('tone', '')
        narration_style = merged_config.get('narration_style', '')
        voice_description = None
        if tone or narration_style:
            parts = [p for p in [tone, narration_style] if p]
            voice_description = '. '.join(parts)
            print(f"Voice Description: {voice_description}")
        
        # Payload
        payload = {
            'channel_id': event.get('channel_id'),
            'narrative_id': event.get('narrative_id'),
            'scenes': event.get('scenes', []),
            'story_title': event.get('story_title', 'Untitled'),
            'user_id': user_id,
            'language': merged_config.get('language', 'English'),
            'speaker': speaker,
            'voice_description': voice_description
        }
        
        print(f"Invoking content-audio-qwen3tts: speaker={speaker}")
        
        response = lambda_client.invoke(
            FunctionName='content-audio-qwen3tts',
            InvocationType='RequestResponse',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        if 'error' in result:
            print(f"Qwen3 error: {result['error']}")
            return None
        
        print(f"Success: {result.get('scene_count', 0)} scenes")
        return result
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def map_voice_profile_to_qwen3_speaker(voice_profile):
    """Map profile to Qwen3 speaker"""
    mapping = {
        'deep_male': 'Ryan', 'authoritative_male': 'Ryan', 'neutral_male': 'Mark',
        'soft_female': 'Lily', 'gentle_female': 'Lily', 'warm_female': 'Emily',
        'Ryan': 'Ryan', 'Lily': 'Lily', 'Emily': 'Emily', 'Mark': 'Mark', 'Jane': 'Jane'
    }
    return mapping.get(voice_profile, 'Ryan')


def get_channel_config(channel_id):
    """Get channel config from DynamoDB"""
    try:
        table = dynamodb.Table(CHANNEL_CONFIGS_TABLE)
        response = table.scan(FilterExpression='channel_id = :cid', ExpressionAttributeValues={':cid': channel_id})
        
        if response['Items']:
            return response['Items'][0]
        
        print(f"Channel {channel_id} not found, using defaults")
        return {'channel_id': channel_id, 'tone': '', 'narration_style': '', 'tts_voice_profile': 'deep_male'}
    except Exception as e:
        print(f"Error loading config: {e}")
        return {'channel_id': channel_id, 'tone': '', 'narration_style': '', 'tts_voice_profile': 'deep_male'}
