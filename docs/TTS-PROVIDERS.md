# Adding New TTS Providers

Guide for integrating additional Text-to-Speech providers into the pipeline.

## Overview

The TTS pipeline supports multiple providers through a pluggable architecture:
1. **SSML Generator** - Converts plain text to provider-specific markup
2. **Provider Lambda** - Handles TTS API calls and audio generation
3. **Step Functions Router** - Routes to correct provider based on config

---

## Current Providers

| Provider | Status | Markup | Features |
|----------|--------|--------|----------|
| AWS Polly | ✅ Production | SSML | Neural/Standard, 50+ voices, genre effects |
| ElevenLabs | 🚧 Planned | Plain text | Voice cloning, emotional control |
| Kokoro | 🚧 Planned | Custom | Open-source, self-hosted |

---

## Integration Steps

### Step 1: Add Provider to SSML Generator

**File:** `aws/lambda/ssml-generator/lambda_function.py`

#### 1.1 Create Generator Class

```python
class YourProviderGenerator:
    """Generator for YourProvider TTS"""

    def __init__(self, genre: str = 'Default'):
        self.genre = genre
        # Load genre-specific rules if needed

    def generate(self, text: str, variation: str = 'normal') -> str:
        """
        Generate provider-specific markup

        Args:
            text: Plain text narration
            variation: Scene variation (normal, dramatic, whisper, etc.)

        Returns:
            Formatted text for your TTS provider
        """
        # Apply your provider's markup format
        # For example, some providers use JSON:
        return json.dumps({
            'text': text,
            'style': variation,
            'speed': self._get_speed_for_genre()
        })

    def _get_speed_for_genre(self):
        """Map genre to provider's speed settings"""
        speed_map = {
            'Horror': 0.8,    # Slow
            'Action': 1.3,    # Fast
            'Mystery': 1.0,   # Medium
            'Default': 1.0
        }
        return speed_map.get(self.genre, 1.0)
```

#### 1.2 Register in lambda_handler

```python
def lambda_handler(event, context):
    # ... existing code ...

    # Select generator based on TTS service
    if 'polly' in tts_service.lower():
        generator = SSMLGenerator(genre)
    elif 'elevenlabs' in tts_service.lower():
        generator = ElevenLabsGenerator()
    elif 'yourprovider' in tts_service.lower():
        generator = YourProviderGenerator(genre)  # NEW
    else:
        generator = SSMLGenerator(genre)  # Default
```

#### 1.3 Test Locally

```python
# test_your_provider.py
from lambda_function import YourProviderGenerator

generator = YourProviderGenerator(genre='Horror')
result = generator.generate(
    text="Test narration",
    variation="whisper"
)
print(result)
```

#### 1.4 Deploy SSML Generator

```bash
cd aws/lambda/ssml-generator
python -m zipfile -c function.zip lambda_function.py
aws lambda update-function-code \
  --function-name ssml-generator \
  --zip-file fileb://function.zip
```

---

### Step 2: Create Provider Lambda

**Location:** `aws/lambda/content-audio-yourprovider/`

#### 2.1 Create Lambda Function

```python
# lambda_function.py
import boto3
import json
from datetime import datetime

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
cost_table = dynamodb.Table('CostTracking')

def lambda_handler(event, context):
    """
    Generate audio using YourProvider TTS

    Input:
    {
        "channel_id": "UCxxxx",
        "narrative_id": "unique_id",
        "tts_service": "yourprovider",
        "scenes": [
            {
                "scene_number": 1,
                "scene_narration_ssml": "Formatted text from SSML generator",
                "scene_narration_plain": "Plain text backup"
            }
        ]
    }

    Output:
    {
        "message": "Audio generated successfully",
        "provider": "YourProvider",
        "audio_files": [...],
        "total_duration_ms": 45000,
        "cost_usd": 0.123
    }
    """

    channel_id = event['channel_id']
    narrative_id = event['narrative_id']
    scenes = event['scenes']

    audio_files = []
    total_cost = 0

    for scene in scenes:
        scene_id = scene['scene_number']

        # Get text (provider-specific format from SSML generator)
        text = scene.get('scene_narration_ssml') or scene.get('scene_narration_plain')

        # Call your provider's API
        audio_data, duration_ms, characters = synthesize_speech(text)

        # Upload to S3
        s3_key = f"narratives/{channel_id}/{narrative_id}/scene_{scene_id}.mp3"
        s3.put_object(
            Bucket='youtube-automation-audio-files',
            Key=s3_key,
            Body=audio_data,
            ContentType='audio/mpeg'
        )

        audio_files.append({
            'scene_id': scene_id,
            's3_url': f's3://youtube-automation-audio-files/{s3_key}',
            's3_key': s3_key,
            'duration_ms': duration_ms
        })

        # Track cost
        scene_cost = calculate_cost(characters)
        total_cost += scene_cost

    # Log cost to DynamoDB
    log_cost(channel_id, narrative_id, total_cost)

    return {
        'message': 'Audio generated successfully',
        'provider': 'YourProvider',
        'audio_files': audio_files,
        'total_duration_ms': sum(af['duration_ms'] for af in audio_files),
        'cost_usd': total_cost
    }

def synthesize_speech(text):
    """
    Call your provider's TTS API

    Returns:
        (audio_data, duration_ms, character_count)
    """
    # Example with requests library
    import requests

    response = requests.post(
        'https://api.yourprovider.com/v1/text-to-speech',
        headers={'Authorization': f'Bearer {get_api_key()}'},
        json={'text': text, 'voice': 'default'}
    )

    audio_data = response.content
    duration_ms = int(response.headers.get('X-Audio-Duration', 0))
    characters = len(text)

    return audio_data, duration_ms, characters

def calculate_cost(characters):
    """Calculate cost based on provider's pricing"""
    # Example: $0.015 per 1000 characters
    return (characters / 1000) * 0.015

def log_cost(channel_id, content_id, cost_usd):
    """Log cost to DynamoDB"""
    cost_table.put_item(
        Item={
            'date': datetime.utcnow().strftime('%Y-%m-%d'),
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'service': 'YourProvider',
            'operation': 'text_to_speech',
            'channel_id': channel_id,
            'content_id': content_id,
            'cost_usd': cost_usd,
            'units': 0  # or character count
        }
    )

def get_api_key():
    """Get API key from Secrets Manager"""
    secrets = boto3.client('secretsmanager')
    response = secrets.get_secret_value(SecretId='yourprovider/api-key')
    return json.loads(response['SecretString'])['api_key']
```

#### 2.2 Create requirements.txt

```txt
boto3==1.28.0
requests==2.31.0
```

#### 2.3 Create Deployment Script

```bash
# deploy.sh
#!/bin/bash
pip install -r requirements.txt -t .
zip -r function.zip lambda_function.py requests/ urllib3/ certifi/ charset_normalizer/ idna/

aws lambda create-function \
  --function-name content-audio-yourprovider \
  --runtime python3.11 \
  --role arn:aws:iam::ACCOUNT_ID:role/lambda-execution-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://function.zip \
  --timeout 120 \
  --memory-size 256 \
  --environment Variables={PROVIDER_API_ENDPOINT=https://api.yourprovider.com}
```

#### 2.4 Deploy Lambda

```bash
chmod +x deploy.sh
./deploy.sh
```

---

### Step 3: Store API Credentials

```bash
# Store API key in Secrets Manager
aws secretsmanager create-secret \
  --name yourprovider/api-key \
  --secret-string '{"api_key":"your-api-key-here"}' \
  --region eu-central-1
```

#### Update IAM Role

Add secrets access to Lambda execution role:

```json
{
  "Effect": "Allow",
  "Action": [
    "secretsmanager:GetSecretValue"
  ],
  "Resource": "arn:aws:secretsmanager:*:*:secret:yourprovider/*"
}
```

---

### Step 4: Update Step Functions

#### 4.1 Add Provider Choice State

Edit Step Function definition:

```json
{
  "ChooseTTSProvider": {
    "Type": "Choice",
    "Choices": [
      {
        "Variable": "$.tts_service",
        "StringEquals": "aws_polly_neural",
        "Next": "GenerateAudioPolly"
      },
      {
        "Variable": "$.tts_service",
        "StringEquals": "yourprovider",
        "Next": "GenerateAudioYourProvider"
      }
    ],
    "Default": "GenerateAudioPolly"
  },
  "GenerateAudioYourProvider": {
    "Type": "Task",
    "Resource": "arn:aws:states:::lambda:invoke",
    "Parameters": {
      "FunctionName": "content-audio-yourprovider",
      "Payload": {
        "channel_id.$": "$.channel_id",
        "narrative_id.$": "$.narrative_id",
        "scenes.$": "$.ssmlResult.Payload.scenes",
        "tts_service.$": "$.tts_service"
      }
    },
    "ResultPath": "$.audioResult",
    "Next": "SaveFinalContent"
  }
}
```

#### 4.2 Deploy Step Functions

```bash
aws stepfunctions update-state-machine \
  --state-machine-arn arn:aws:states:eu-central-1:ACCOUNT:stateMachine:ContentGenerator \
  --definition file://updated-step-function.json
```

---

### Step 5: Update Channel Config

Add TTS provider option to channel config:

```python
# In admin dashboard or API
channel_config = {
    'channel_id': 'UCxxxx',
    'tts_service': 'yourprovider',  # NEW option
    'tts_voice_profile': 'default',
    # ... other config
}
```

---

## Testing Checklist

### Unit Tests

- [ ] SSML generator produces correct format
- [ ] Provider Lambda accepts valid input
- [ ] API calls work with test credentials
- [ ] Audio files upload to S3 correctly
- [ ] Cost tracking works

### Integration Tests

```bash
# Test SSML generator
aws lambda invoke \
  --function-name ssml-generator \
  --payload '{"scenes":[{"scene_number":1,"scene_narration":"Test","variation_used":"normal"}],"tts_service":"yourprovider","genre":"Default"}' \
  ssml-test.json

# Test provider Lambda
aws lambda invoke \
  --function-name content-audio-yourprovider \
  --payload '{"channel_id":"test","narrative_id":"test123","scenes":[...]}' \
  audio-test.json

# Test full pipeline
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:...:stateMachine:ContentGenerator \
  --input '{"tts_service":"yourprovider"}'
```

### Validation

- [ ] Audio quality acceptable
- [ ] Duration matches expectations
- [ ] Costs tracked correctly in DynamoDB
- [ ] Files accessible in S3
- [ ] No errors in CloudWatch logs

---

## Provider-Specific Considerations

### API Rate Limits

```python
import time
from functools import wraps

def rate_limit(calls_per_second=5):
    min_interval = 1.0 / calls_per_second
    last_called = [0.0]

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            ret = func(*args, **kwargs)
            last_called[0] = time.time()
            return ret
        return wrapper
    return decorator

@rate_limit(calls_per_second=10)
def call_tts_api(text):
    # Your API call
    pass
```

### Retry Logic

```python
from botocore.exceptions import ClientError
import time

def call_api_with_retry(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt  # Exponential backoff
            time.sleep(wait_time)
```

### Voice Selection

Map generic voice profiles to provider voices:

```python
VOICE_MAP = {
    'aws_polly_neural': {
        'deep_male': 'Matthew',
        'female': 'Joanna',
        'british_male': 'Brian'
    },
    'yourprovider': {
        'deep_male': 'voice_id_123',
        'female': 'voice_id_456',
        'british_male': 'voice_id_789'
    }
}

def get_voice_id(profile, provider):
    return VOICE_MAP.get(provider, {}).get(profile, 'default')
```

---

## Cost Management

### Track Per-Provider Costs

```python
def log_tts_cost(channel_id, content_id, provider, cost):
    cost_table.put_item(
        Item={
            'date': datetime.utcnow().strftime('%Y-%m-%d'),
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'service': f'TTS-{provider}',
            'operation': 'text_to_speech',
            'channel_id': channel_id,
            'content_id': content_id,
            'cost_usd': Decimal(str(cost)),
            'provider': provider  # Tag for filtering
        }
    )
```

### Cost Comparison Dashboard

Query DynamoDB to compare costs:

```python
from boto3.dynamodb.conditions import Key
from datetime import datetime, timedelta

def get_provider_costs(days=7):
    start_date = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')

    response = cost_table.query(
        KeyConditionExpression=Key('date').gte(start_date)
    )

    costs_by_provider = {}
    for item in response['Items']:
        provider = item.get('provider', 'unknown')
        cost = float(item['cost_usd'])
        costs_by_provider[provider] = costs_by_provider.get(provider, 0) + cost

    return costs_by_provider
```

---

## Monitoring

### Add CloudWatch Alarms

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name yourprovider-high-error-rate \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=FunctionName,Value=content-audio-yourprovider
```

### Custom Metrics

```python
import boto3
cloudwatch = boto3.client('cloudwatch')

def publish_metric(metric_name, value):
    cloudwatch.put_metric_data(
        Namespace='ContentPipeline',
        MetricData=[{
            'MetricName': metric_name,
            'Value': value,
            'Unit': 'Count',
            'Timestamp': datetime.utcnow()
        }]
    )

# Usage
publish_metric('YourProviderAPICallSuccess', 1)
publish_metric('YourProviderAudioDuration', duration_ms)
```

---

## Example: ElevenLabs Integration

### SSML Generator

```python
class ElevenLabsGenerator:
    """ElevenLabs doesn't support SSML, return plain text"""

    def generate(self, text: str, variation: str = 'normal') -> str:
        # Strip any SSML tags that might be present
        text = re.sub(r'<[^>]+>', '', text)
        return text.strip()
```

### Provider Lambda

```python
def synthesize_with_elevenlabs(text, voice_id):
    import requests

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": get_api_key()
    }
    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }

    response = requests.post(url, json=data, headers=headers)
    return response.content
```

---

## Resources

- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [Step Functions Task States](https://docs.aws.amazon.com/step-functions/latest/dg/amazon-states-language-task-state.html)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)

---

**Last Updated:** 2025-11-25
**Status:** ✅ Complete Guide
