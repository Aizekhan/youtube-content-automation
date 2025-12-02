# 🎤 TTS Provider Architecture - Deployment Guide

**Архітектура з окремими Lambda для кожного TTS провайдера**

## 📐 Архітектура

```
┌─────────────────────────────────────────────────────────────┐
│                    Step Functions Workflow                   │
│                                                              │
│  Phase 3: Audio Generation                                  │
│  ┌─────────────────┐                                        │
│  │ GetTTSConfig    │  Extract tts_service from channel      │
│  └────────┬────────┘                                        │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐                                        │
│  │ RouteTTSProvider│  Choice State                          │
│  └────┬───┬────┬───┘                                        │
│       │   │    │                                             │
│  ┌────▼───▼────▼─────┐                                      │
│  │ aws_polly_neural  │───► content-audio-polly              │
│  │ aws_polly_standard│───► content-audio-polly              │
│  │ elevenlabs        │───► content-audio-elevenlabs         │
│  │ google_tts        │───► content-audio-google (future)    │
│  └───────────────────┘                                      │
│           │                                                  │
│           ▼                                                  │
│  ┌─────────────────┐                                        │
│  │ FallbackToPolly │  On error → AWS Polly                  │
│  └─────────────────┘                                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Lambda Functions                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ Lambda Layer: tts-common                             │  │
│  │ ├─ BaseTTSProvider (base class)                      │  │
│  │ ├─ config_merger.py (voice mapping)                  │  │
│  │ ├─ ssml_validator.py (SSML validation)               │  │
│  │ └─ cost_logger.py (cost tracking)                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                          ▲                                   │
│                          │ (attached to all Lambdas)         │
│                          │                                   │
│  ┌──────────────┐   ┌───────────────────┐   ┌────────────┐ │
│  │ content-     │   │ content-audio-    │   │ content-   │ │
│  │ audio-polly  │   │ elevenlabs        │   │ audio-     │ │
│  │              │   │                   │   │ google     │ │
│  │ Size: ~5 KB  │   │ Size: ~2 MB       │   │ (future)   │ │
│  │ Timeout: 30s │   │ Timeout: 300s     │   │            │ │
│  │ Memory: 512  │   │ Memory: 512       │   │            │ │
│  └──────────────┘   └───────────────────┘   └────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Deployment Steps

### Крок 1: Deploy Lambda Layer (tts-common)

```bash
cd aws/lambda-layers/tts-common

# Create package
zip -r tts-common-layer.zip python/

# Deploy to AWS
aws lambda publish-layer-version \
  --layer-name tts-common \
  --description "Shared TTS utilities v1.0" \
  --zip-file fileb://tts-common-layer.zip \
  --compatible-runtimes python3.11 python3.10 python3.9 \
  --region eu-central-1

# Save Layer ARN
LAYER_ARN=$(aws lambda list-layer-versions \
  --layer-name tts-common \
  --region eu-central-1 \
  --query 'LayerVersions[0].LayerVersionArn' \
  --output text)

echo "Layer ARN: $LAYER_ARN"
```

### Крок 2: Deploy content-audio-polly Lambda

```bash
cd aws/lambda/content-audio-polly

# Create deployment package
python create_zip.py

# Create Lambda function
aws lambda create-function \
  --function-name content-audio-polly \
  --runtime python3.11 \
  --role arn:aws:iam::599297130956:role/lambda-execution-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://function.zip \
  --timeout 60 \
  --memory-size 512 \
  --region eu-central-1 \
  --description "AWS Polly TTS provider (Neural/Standard)"

# Attach Lambda Layer
aws lambda update-function-configuration \
  --function-name content-audio-polly \
  --layers $LAYER_ARN \
  --region eu-central-1

echo "✅ content-audio-polly deployed"
```

### Крок 3: Setup ElevenLabs API Key

```bash
# Store API key in Secrets Manager
aws secretsmanager create-secret \
  --name elevenlabs-api-key \
  --description "ElevenLabs API key for TTS" \
  --secret-string '{"api_key":"YOUR_ELEVENLABS_API_KEY"}' \
  --region eu-central-1
```

Get your API key from: https://elevenlabs.io/app/settings

### Крок 4: Deploy content-audio-elevenlabs Lambda

```bash
cd aws/lambda/content-audio-elevenlabs

# Install dependencies and create package
python create_zip.py

# Create Lambda function
aws lambda create-function \
  --function-name content-audio-elevenlabs \
  --runtime python3.11 \
  --role arn:aws:iam::599297130956:role/lambda-execution-role \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://function.zip \
  --timeout 300 \
  --memory-size 512 \
  --region eu-central-1 \
  --description "ElevenLabs TTS provider"

# Attach Lambda Layer
aws lambda update-function-configuration \
  --function-name content-audio-elevenlabs \
  --layers $LAYER_ARN \
  --region eu-central-1

# Grant Secrets Manager permission
aws lambda add-permission \
  --function-name content-audio-elevenlabs \
  --statement-id AllowSecretsManager \
  --action lambda:InvokeFunction \
  --principal secretsmanager.amazonaws.com \
  --region eu-central-1

echo "✅ content-audio-elevenlabs deployed"
```

### Крок 5: Update IAM Policies

Add permissions for new Lambdas:

```bash
# Add to lambda-execution-role policy
cat > temp-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "polly:SynthesizeSpeech"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:eu-central-1:599297130956:secret:elevenlabs-api-key-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:PutObjectAcl"
      ],
      "Resource": "arn:aws:s3:::youtube-automation-audio-files/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:Query",
        "dynamodb:GetItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:eu-central-1:599297130956:table/CostTracking",
        "arn:aws:dynamodb:eu-central-1:599297130956:table/ChannelConfigs",
        "arn:aws:dynamodb:eu-central-1:599297130956:table/ChannelConfigs/index/*"
      ]
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name lambda-execution-role \
  --policy-name TTSProvidersPolicy \
  --policy-document file://temp-policy.json

rm temp-policy.json
```

### Крок 6: Update Step Functions

**IMPORTANT**: Замініть state "GenerateAudio" в Phase3AudioAndSave Iterator на новий TTS routing logic.

See: `aws/step-functions-tts-provider-routing.json`

```bash
# Update Step Function definition
aws stepfunctions update-state-machine \
  --state-machine-arn arn:aws:states:eu-central-1:599297130956:stateMachine:ContentGenerator \
  --definition file://step-functions-with-tts-routing-FULL.json \
  --region eu-central-1
```

## ✅ Verification

### Test Polly Lambda

```bash
aws lambda invoke \
  --function-name content-audio-polly \
  --payload '{"channel_id":"test","narrative_id":"test123","tts_service":"aws_polly_neural","tts_voice_profile":"matthew_male","scenes":[{"scene_number":1,"text_with_ssml":"<speak>Hello world</speak>"}]}' \
  --region eu-central-1 \
  polly-test-output.json

cat polly-test-output.json
```

### Test ElevenLabs Lambda

```bash
aws lambda invoke \
  --function-name content-audio-elevenlabs \
  --payload '{"channel_id":"test","narrative_id":"test456","tts_service":"elevenlabs","tts_voice_profile":"adam_male","elevenlabs_model":"turbo","scenes":[{"scene_number":1,"text_with_ssml":"Hello from ElevenLabs"}]}' \
  --region eu-central-1 \
  elevenlabs-test-output.json

cat elevenlabs-test-output.json
```

## 🔧 Configuration

### Update ChannelConfigs

Add TTS service field to your channel configs:

```json
{
  "config_id": "channel_config_001",
  "channel_id": "UCRmO5HB89GW_zjX3dJACfzw",
  "channel_name": "My Channel",
  "tts_service": "elevenlabs",  // ← ADD THIS
  "tts_voice_profile": "adam_male",
  "elevenlabs_model": "turbo",  // ← ADD THIS (optional)
  ...
}
```

**Supported values for `tts_service`:**
- `aws_polly_neural` (default)
- `aws_polly_standard`
- `elevenlabs`
- `google_tts` (future)

## 📊 Cost Comparison

| Provider | Model | Cost per 1M chars | 10-min video cost |
|----------|-------|-------------------|-------------------|
| AWS Polly | Neural | $16 | $0.128 |
| AWS Polly | Standard | $4 | $0.032 |
| ElevenLabs | Turbo v2.5 | $30 | $0.24 |
| ElevenLabs | Multilingual v2 | $240 | $1.92 |

**Recommendation**:
- Default channels → AWS Polly Neural
- Premium channels → ElevenLabs Turbo
- High-volume channels → AWS Polly Standard

## 🎯 Next Steps

1. ✅ Deploy all components
2. ✅ Test each Lambda individually
3. ✅ Update Step Functions definition
4. ✅ Run end-to-end test with Step Functions
5. ✅ Monitor CloudWatch logs for errors
6. ✅ Update channel configs with `tts_service` field
7. ✅ Run production test with 1 channel
8. ✅ Scale to all channels

## 📚 Documentation

- **Lambda Layer**: `aws/lambda-layers/tts-common/README.md`
- **Polly Lambda**: `aws/lambda/content-audio-polly/README.md`
- **ElevenLabs Lambda**: `aws/lambda/content-audio-elevenlabs/README.md`
- **Step Functions**: `aws/step-functions-tts-provider-routing.json`

## 🔍 Troubleshooting

### Lambda Layer not found
```bash
# Verify layer exists
aws lambda list-layer-versions --layer-name tts-common --region eu-central-1
```

### ElevenLabs API key error
```bash
# Verify secret exists
aws secretsmanager get-secret-value --secret-id elevenlabs-api-key --region eu-central-1
```

### Polly voice not supported
- Check voice ID in `config_merger.py` voice mapping
- Ensure voice is available in `eu-central-1` region

---

**Version**: 2.0 (Provider Architecture)
**Date**: 2025-11-25
**Author**: AI + Human collaboration 🤖🤝👨‍💻
