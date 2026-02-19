"""
Telegram Error Notifier Lambda
Sends error notifications to Telegram bot when critical failures occur
Reads Telegram credentials from SystemSettings DynamoDB table
"""
import json
import urllib.request
import urllib.parse
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
settings_table = dynamodb.Table('SystemSettings')

def get_telegram_settings():
    """
    Retrieve Telegram settings from DynamoDB
    Returns: dict with bot_token and chat_id, or None if not configured
    """
    try:
        response = settings_table.get_item(
            Key={
                'setting_type': 'telegram_notifications',
                'setting_id': 'default'
            }
        )

        if 'Item' in response:
            config = response['Item'].get('config', {})
            if config.get('enabled') and config.get('bot_token') and config.get('chat_id'):
                return {
                    'bot_token': config['bot_token'],
                    'chat_id': config['chat_id']
                }

        print("Telegram notifications not configured or disabled")
        return None

    except ClientError as e:
        print(f"Error retrieving Telegram settings from DynamoDB: {e}")
        return None

def send_telegram_message(bot_token, chat_id, message):
    """Send message to Telegram bot"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    data = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }

    data_encoded = urllib.parse.urlencode(data).encode('utf-8')
    req = urllib.request.Request(url, data=data_encoded, method='POST')

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get('ok', False)
    except Exception as e:
        print(f"Failed to send Telegram message: {str(e)}")
        return False

def lambda_handler(event, context):
    """
    Handle error notifications from SNS (CloudWatch Alarms) or direct invocation
    """
    print(f"Received notification: {json.dumps(event, default=str)[:500]}")

    # Check if this is an SNS event
    if 'Records' in event and len(event['Records']) > 0:
        # This is an SNS notification (from CloudWatch Alarm)
        sns_record = event['Records'][0]
        if 'Sns' in sns_record:
            sns_message = sns_record['Sns']
            alarm_message = sns_message.get('Message', '')
            alarm_subject = sns_message.get('Subject', 'CloudWatch Alarm')

            # Parse alarm message
            try:
                alarm_data = json.loads(alarm_message)
                alarm_name = alarm_data.get('AlarmName', 'Unknown Alarm')
                new_state = alarm_data.get('NewStateValue', 'UNKNOWN')
                reason = alarm_data.get('NewStateReason', 'No reason provided')

                # Convert SNS alarm to our standard format
                event = {
                    'error_type': f'CloudWatch: {alarm_name}',
                    'execution_arn': 'N/A',
                    'error_details': {
                        'Error': f'State: {new_state}',
                        'Cause': reason
                    },
                    'timestamp': sns_message.get('Timestamp', datetime.utcnow().isoformat())
                }
                print(f"Converted SNS alarm: {alarm_name} -> {new_state}")
            except json.JSONDecodeError:
                # Message is plain text
                event = {
                    'error_type': alarm_subject,
                    'execution_arn': 'N/A',
                    'error_details': {
                        'Error': 'CloudWatch Alarm',
                        'Cause': alarm_message[:500]
                    },
                    'timestamp': sns_message.get('Timestamp', datetime.utcnow().isoformat())
                }

    try:
        # Get Telegram settings from DynamoDB
        telegram_settings = get_telegram_settings()

        if not telegram_settings:
            print(" Telegram notifications not configured - skipping")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': False,
                    'message': 'Telegram not configured',
                    'skipped': True
                })
            }

        bot_token = telegram_settings['bot_token']
        chat_id = telegram_settings['chat_id']

        error_type = event.get('error_type', 'Unknown Error')
        execution_arn = event.get('execution_arn', 'N/A')
        error_details = event.get('error_details', {})
        timestamp = event.get('timestamp', datetime.utcnow().isoformat())

        # Extract execution name from ARN
        execution_name = execution_arn.split(':')[-1] if execution_arn != 'N/A' else 'Unknown'

        # Extract error message
        error_message = error_details.get('Error', 'Unknown')
        error_cause = error_details.get('Cause', 'No details available')

        # Try to parse Cause if it's JSON
        try:
            if isinstance(error_cause, str) and error_cause.startswith('{'):
                cause_json = json.loads(error_cause)
                error_cause = cause_json.get('errorMessage', error_cause)
        except:
            pass

        # Format error message for Telegram
        message = f""" <b>YouTube Automation Alert</b>

<b>Type:</b> {error_type}
<b>Time:</b> {timestamp}
<b>Execution:</b> {execution_name}

<b>Error:</b> {error_message}

<b>Details:</b>
{error_cause[:500]}

 Check AWS Console for full details.

<b>ARN:</b>
<code>{execution_arn}</code>
"""

        # Send to Telegram
        success = send_telegram_message(bot_token, chat_id, message)

        if success:
            print(" Telegram notification sent successfully")
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'message': 'Notification sent to Telegram'
                })
            }
        else:
            print(" Failed to send Telegram notification")
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'success': False,
                    'message': 'Failed to send Telegram notification'
                })
            }

    except Exception as e:
        error_msg = f"Error in telegram-error-notifier: {str(e)}"
        print(error_msg)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'message': error_msg
            })
        }
