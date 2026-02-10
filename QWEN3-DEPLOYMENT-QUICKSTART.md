# Qwen3-TTS Deployment - Quick Start Guide

**Target:** AWS Production Environment
**Time Required:** ~10 minutes
**Prerequisites:** AWS CLI configured, Python 3.11+

---

## 🚀 3-Step Deployment

### Step 1: Setup IAM (One-Time)

```bash
cd /path/to/youtube-content-automation
bash aws/scripts/setup-qwen3-iam.sh
```

**What it does:**
- Creates Qwen3LambdaPolicy (Lambda permissions)
- Creates Qwen3EC2Policy (EC2 instance permissions)
- Creates qwen3-ec2-role and instance profile
- Attaches policies to appropriate roles

**Expected output:**
```
[OK] Lambda policy configured
[OK] EC2 policy configured
[OK] Instance profile configured
SUCCESS: IAM setup complete!
```

---

### Step 2: Deploy Lambda Functions

```bash
bash aws/scripts/deploy-qwen3-lambdas.sh
```

**What it does:**
- Packages ec2-qwen3-control Lambda
- Packages content-audio-qwen3tts Lambda
- Updates content-audio-tts Lambda (adds router)
- Deploys/updates all 3 functions

**Expected output:**
```
[1/3] Deploying ec2-qwen3-control Lambda...
   Creating deployment package...
   [OK] Function created/updated

[2/3] Deploying content-audio-qwen3tts Lambda...
   Creating deployment package...
   [OK] Function created/updated

[3/3] Updating content-audio-tts Lambda...
   Creating deployment package...
   [OK] Function code updated

SUCCESS: Lambda deployment complete!
```

---

### Step 3: Test Integration (Optional but Recommended)

```bash
bash aws/scripts/test-qwen3-integration.sh
```

**What it does:**
- Tests ec2-qwen3-control (status, start)
- Waits for EC2 to be ready (max 5 min)
- Tests content-audio-qwen3tts with sample payload
- Tests provider router in content-audio-tts
- Verifies audio generation

**Expected output:**
```
[1/5] Testing ec2-qwen3-control - Status... [OK]
[2/5] Testing ec2-qwen3-control - Start EC2... [OK]
[3/5] Waiting for EC2 server to be ready... [OK]
[4/5] Testing content-audio-qwen3tts Lambda... [OK]
[5/5] Testing provider router... [OK]

Test Summary:
All tests passed!
```

---

## 🎯 Verify Deployment

### Check Lambda Functions

```bash
aws lambda list-functions --region eu-central-1 \
  --query 'Functions[?contains(FunctionName, `qwen3`)].FunctionName'
```

**Expected:**
```json
[
    "ec2-qwen3-control",
    "content-audio-qwen3tts"
]
```

### Check DynamoDB Templates

```bash
python aws/scripts/create-qwen3-templates.py --list
```

**Expected:**
```
QWEN3_TTS:
   [+] tts_qwen3_emily_v1 - Qwen3-TTS Emily (Neutral Female)
   [+] tts_qwen3_jane_v1 - Qwen3-TTS Jane (Warm Female)
   [+] tts_qwen3_lily_v1 - Qwen3-TTS Lily (Soft Female)
   [+] tts_qwen3_mark_v1 - Qwen3-TTS Mark (Neutral Male)
   [+] tts_qwen3_ryan_v1 - Qwen3-TTS Ryan (Deep Male)
```

### Test EC2 Control

```bash
aws lambda invoke \
  --function-name ec2-qwen3-control \
  --payload '{"action":"status"}' \
  response.json && cat response.json
```

**Expected (no instance):**
```json
{
  "status": "no_instance",
  "message": "No Qwen3-TTS instance found"
}
```

**Expected (instance exists):**
```json
{
  "status": "running",
  "instance_id": "i-xxxxxxxxx",
  "endpoint": "http://x.x.x.x:8000",
  "health": "healthy"
}
```

---

## 🎨 Using in Production

### For Users (UI)

1. Go to **Channel Config** page
2. Find **TTS Template** dropdown
3. Select one of:
   - Qwen3-TTS Ryan (Deep Male)
   - Qwen3-TTS Lily (Soft Female)
   - Qwen3-TTS Emily (Neutral Female)
   - Qwen3-TTS Mark (Neutral Male)
   - Qwen3-TTS Jane (Warm Female)
4. Save config
5. Generate video normally

### For Developers (API)

```json
{
  "channel_id": "your-channel",
  "narrative_id": "unique-id",
  "scenes": [...],
  "tts_settings": {
    "tts_service": "qwen3_tts",
    "tts_voice_profile": "deep_male",
    "language": "English"
  }
}
```

---

## 💰 Cost Monitoring

### View Costs in DynamoDB

```bash
aws dynamodb scan \
  --table-name CostTracking \
  --filter-expression "service_name = :service" \
  --expression-attribute-values '{":service":{"S":"qwen3_tts"}}' \
  --region eu-central-1
```

### Expected Cost Structure

- **Per video:** ~$0.02 (2 min EC2 time)
- **Per month (100 videos):** ~$2
- **Savings vs Polly:** $70/month (97%)

---

## 🛑 Stop EC2 (Save Costs)

Auto-stop is enabled by default (5 min idle), but you can manually stop:

```bash
aws lambda invoke \
  --function-name ec2-qwen3-control \
  --payload '{"action":"stop"}' \
  response.json
```

---

## 🐛 Troubleshooting

### Issue: Lambda deployment fails

**Solution:**
```bash
# Check AWS credentials
aws sts get-caller-identity

# Verify IAM role exists
aws iam get-role --role-name lambda-execution-role

# Check region
export AWS_DEFAULT_REGION=eu-central-1
```

### Issue: EC2 won't start

**Solution:**
```bash
# Check EC2 quota
aws service-quotas get-service-quota \
  --service-code ec2 \
  --quota-code L-1216C47A

# Check security groups exist
aws ec2 describe-security-groups --region eu-central-1

# Manual EC2 launch
aws ec2 run-instances \
  --image-id ami-0b7fd829e7758b06d \
  --instance-type g4dn.xlarge \
  --region eu-central-1 \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=qwen3-tts-server},{Key=Service,Value=Qwen3-TTS}]'
```

### Issue: Audio generation fails

**Solution:**
```bash
# Check Lambda logs
aws logs tail /aws/lambda/content-audio-qwen3tts --follow

# Check EC2 instance
INSTANCE_ID=$(aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=qwen3-tts-server" \
  --query 'Reservations[0].Instances[0].InstanceId' \
  --output text)

aws ec2 describe-instance-status --instance-ids $INSTANCE_ID

# SSH to EC2 (if key configured)
ssh -i your-key.pem ubuntu@<instance-ip>
sudo journalctl -u qwen3-tts -f
```

### Issue: Templates not showing in UI

**Solution:**
```bash
# Re-create templates
python aws/scripts/create-qwen3-templates.py

# Verify via API
curl https://your-prompts-api.com/templates?type=tts

# Check UI is loading templates from correct endpoint
```

---

## 📊 Success Metrics

After deployment, verify:

- ✅ Lambda functions deployed
- ✅ IAM policies attached
- ✅ DynamoDB templates created
- ✅ EC2 can start/stop
- ✅ Audio generation works
- ✅ UI shows Qwen3 templates
- ✅ Cost tracking enabled

---

## 🔗 Additional Resources

- **Full Documentation:** `QWEN3-TTS-COMPLETE-SUMMARY.md`
- **Architecture Details:** `docs/QWEN3-TTS-INTEGRATION-PLAN.md`
- **Progress Tracker:** `QWEN3-IMPLEMENTATION-PROGRESS.md`

---

## ⚡ Quick Commands Reference

```bash
# Deploy everything
bash aws/scripts/setup-qwen3-iam.sh && \
bash aws/scripts/deploy-qwen3-lambdas.sh && \
bash aws/scripts/test-qwen3-integration.sh

# Check Lambda logs
aws logs tail /aws/lambda/ec2-qwen3-control --follow

# Stop EC2 manually
aws lambda invoke --function-name ec2-qwen3-control \
  --payload '{"action":"stop"}' response.json

# List templates
python aws/scripts/create-qwen3-templates.py --list

# Check costs
aws dynamodb scan --table-name CostTracking \
  --filter-expression "service_name = :s" \
  --expression-attribute-values '{":s":{"S":"qwen3_tts"}}'
```

---

**Status:** Ready for deployment
**Last Updated:** 2026-02-09
**Estimated deployment time:** 10 minutes
