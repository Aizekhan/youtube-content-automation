# Debug Test Runner Lambda Function

## Overview
This Lambda function sequentially executes all content generation steps and collects detailed debug information for each step.

## What it does
1. **Get Channel Config** - Fetches channel configuration from ChannelConfigs
2. **Generate Theme** - Calls content-theme-agent Lambda
3. **Generate Narrative** - Calls content-narrative Lambda
4. **Generate Audio** - Calls content-audio-tts Lambda
5. **Save Result** - Calls content-save-result Lambda

For each step, it collects:
- Input payload
- Output response
- Duration (ms)
- Errors (if any)
- Timestamps

## Input
```json
{
  "channel_id": "UCRmO5HB89GW...",
  "topic": "Optional topic (leave empty for auto-generation)",
  "target_character_count": 8000,  // Optional override
  "scene_count_target": 18         // Optional override
}
```

## Output
```json
{
  "success": true,
  "steps": [
    {
      "step_number": 1,
      "step_name": "get-channel-config",
      "lambda_function": "content-get-channels",
      "status": "completed",
      "duration_ms": 234,
      "input": {...},
      "output": {...},
      "error": null,
      "timestamp": "2025-11-05T..."
    },
    // ... more steps
  ],
  "summary": {
    "total_duration_ms": 12345,
    "total_duration_sec": 12.35,
    "total_cost_usd": 0.025,
    "scene_count": 18,
    "character_count": 8756,
    "audio_duration_sec": 45.2,
    "narrative_id": "...",
    "story_title": "..."
  },
  "test_data": {
    "channel_name": "Myths & Legends",
    "channel_id": "...",
    "topic": "The Forgotten Goddess"
  }
}
```

## Deployment

### Option 1: Deploy via SSH (Recommended)
```powershell
# From this directory
./deploy-via-ssh.ps1
```

### Option 2: Deploy locally (requires AWS CLI configured)
```bash
chmod +x deploy.sh
./deploy.sh
```

### Option 3: Manual deployment
```bash
# Create package
zip -r function.zip lambda_function.py

# Create function (first time)
aws lambda create-function \
    --function-name debug-test-runner \
    --runtime python3.11 \
    --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-execution-role \
    --handler lambda_function.lambda_handler \
    --zip-file fileb://function.zip \
    --timeout 300 \
    --memory-size 512 \
    --region eu-central-1

# Or update existing
aws lambda update-function-code \
    --function-name debug-test-runner \
    --zip-file fileb://function.zip \
    --region eu-central-1

# Create Function URL
aws lambda create-function-url-config \
    --function-name debug-test-runner \
    --auth-type NONE \
    --cors AllowOrigins="*",AllowMethods="POST,GET,OPTIONS",AllowHeaders="Content-Type" \
    --region eu-central-1
```

## Required IAM Permissions
The Lambda execution role needs permissions to:
- Invoke other Lambda functions (lambda:InvokeFunction)
- Read from DynamoDB (dynamodb:Query, dynamodb:GetItem)
- Write CloudWatch Logs

Example policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": [
        "arn:aws:lambda:eu-central-1:*:function:content-*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:Query",
        "dynamodb:GetItem"
      ],
      "Resource": "arn:aws:dynamodb:eu-central-1:*:table/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

## Testing
```bash
# Get the Function URL
aws lambda get-function-url-config \
    --function-name debug-test-runner \
    --region eu-central-1

# Test with curl
curl -X POST https://YOUR_FUNCTION_URL.lambda-url.eu-central-1.on.aws/ \
  -H "Content-Type: application/json" \
  -d '{"channel_id": "YOUR_CHANNEL_ID", "topic": "Test Topic"}'
```

## Integration with debug-dashboard.html
After deployment, update the `DEBUG_API_URL` in `debug-dashboard.html`:
```javascript
const DEBUG_API_URL = 'https://YOUR_FUNCTION_URL.lambda-url.eu-central-1.on.aws/';
```

## Timeout Settings
- Function timeout: 300 seconds (5 minutes)
- Expected duration: 10-30 seconds depending on content length
- If timeout occurs, check individual Lambda function logs

## Cost Tracking
The function collects cost information from:
- OpenAI API calls (theme-agent, narrative)
- AWS Polly TTS calls (audio-tts)
- Total cost is summed in the summary

## Troubleshooting
- **Lambda invocation errors**: Check IAM permissions
- **Timeout errors**: Increase timeout or optimize individual Lambda functions
- **Missing output**: Check CloudWatch logs for each Lambda function
- **CORS errors**: Ensure Function URL has CORS configured correctly
