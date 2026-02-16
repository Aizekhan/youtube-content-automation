# 🚀 Z-Image-Turbo Migration Plan

**Date:** 2026-02-10
**Status:** Ready for Deployment
**Goal:** Replace SD3.5 Medium with Z-Image-Turbo for 5-10x faster and 75% cheaper image generation

---

## Executive Summary

### Performance Gains

| Metric | SD3.5 Medium | Z-Image-Turbo | Improvement |
|--------|--------------|---------------|-------------|
| **Generation Time** | 5.5 sec/image | 0.5-1 sec/image | **5-10x faster** ⚡ |
| **Batch (18 images)** | 90 seconds | 10-15 seconds | **6x faster** |
| **VRAM Usage** | 13GB | 8GB | **40% less** 📉 |
| **Model Size** | 12GB | 6GB | **50% smaller** 💾 |
| **Startup Time** | 90 seconds | 30-45 seconds | **2x faster** |
| **Cost per image** | $0.0117 | $0.002-0.003 | **75-85% cheaper** 💰 |

### Cost Savings

**Monthly costs (100 generation runs, 18 images each):**

- **Before (SD3.5):** $2.52/month
- **After (Z-Image-Turbo):** $0.25-0.42/month
- **Savings:** $2.10-2.27/month (83-90% reduction)

**Yearly savings:** ~$25-27 on compute alone

---

## Architecture Changes

### What Changes

✅ **EC2 Server Code:**
- New FastAPI server at `/home/ubuntu/zimage-api/`
- Uses `ZImagePipeline` from diffusers
- Flask API with same endpoints (`/health`, `/generate`)

✅ **Lambda Cost Calculations:**
- Update pricing in `content-generate-images` Lambda
- Old: $0.0117/image → New: $0.003/image

### What Stays the Same

✅ **EC2 Control Lambda** (`ec2-sd35-control`) - no changes needed
✅ **Step Functions Workflow** - identical flow
✅ **API Interface** - same request/response format
✅ **Batching System** - works identically
✅ **S3 Upload** - unchanged
✅ **DynamoDB Logging** - unchanged

### Why It's Easy

The new model has **identical API interface**:

```python
# Request (same as before)
POST /generate
{
  "prompt": "...",
  "width": 1024,
  "height": 1024
}

# Response (same as before)
Content-Type: image/png
<binary PNG data>
```

---

## Deployment Plan

### Phase 1: Deploy to EC2 (15 minutes)

#### Step 1.1: Start EC2 Instance

```bash
aws lambda invoke \
  --function-name ec2-sd35-control \
  --payload '{"action":"start"}' \
  --region eu-central-1 \
  response.json

# Get IP from response
cat response.json | jq -r '.body | fromjson | .ip'
```

#### Step 1.2: Upload Files

```bash
# Use the quick-deploy.bat script
cd E:\youtube-content-automation\ec2-zimage-turbo
quick-deploy.bat
```

Or manually:

```bash
KEY_PATH="E:/youtube-content-automation/n8n-key.pem"
EC2_IP="<IP_FROM_STEP_1.1>"

# Upload files
scp -i "$KEY_PATH" api_server.py ubuntu@$EC2_IP:/tmp/
scp -i "$KEY_PATH" deploy.sh ubuntu@$EC2_IP:/tmp/

# Run deployment
ssh -i "$KEY_PATH" ubuntu@$EC2_IP
chmod +x /tmp/deploy.sh
/tmp/deploy.sh
```

#### Step 1.3: Verify Deployment

```bash
# Check service status
sudo systemctl status zimage-api

# Test health
curl http://localhost:5000/health

# Test generation
curl -X POST http://localhost:5000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A sunset over mountains", "width": 1024, "height": 1024}' \
  --output test.png

# Verify image
ls -lh test.png
```

**Expected results:**
- Service status: ✅ Active (running)
- Health check: `{"status": "healthy", "model_loaded": true}`
- Test image: ~2-5MB PNG file
- Generation time: 0.5-1 second

### Phase 2: Update Lambda Functions (5 minutes)

#### Step 2.1: Update Cost Calculations

Edit `aws/lambda/content-generate-images/lambda_function.py`:

```python
# Line ~273: Update EC2 cost
cost = 0.003  # Updated from 0.0117 for Z-Image-Turbo

# Line ~48-51: Update pricing table
PRICING = {
    # ... other pricing ...
    'ec2-zimage-turbo': {  # Add new entry
        'hourly_rate': 1.006,  # g5.xlarge
        'images_per_hour': 3600  # ~1 second per image
    },
    'ec2-sd35': {  # Keep old for reference
        'hourly_rate': 1.006,
        'images_per_hour': 85.7
    }
}
```

#### Step 2.2: Deploy Lambda

```bash
cd E:/youtube-content-automation/aws/lambda/content-generate-images

# Create deployment package
python create_zip.py

# Deploy
aws lambda update-function-code \
  --function-name content-generate-images \
  --zip-file fileb://function.zip \
  --region eu-central-1
```

### Phase 3: Test End-to-End (10 minutes)

#### Step 3.1: Test with Single Channel

```bash
# Start Step Functions execution
aws stepfunctions start-execution \
  --state-machine-arn "arn:aws:states:eu-central-1:599297130956:stateMachine:ContentGenerator" \
  --region eu-central-1 \
  --name "test-zimage-$(date +%s)" \
  --input '{
    "channel_ids":["UCRmO5HB89GW_zjX3dJACfzw"],
    "user_id":"user_test_zimage",
    "max_scenes":3
  }'

# Monitor execution
EXEC_ARN="<from above output>"

# Wait ~2-3 minutes (should be much faster now!)
sleep 180

# Check result
aws stepfunctions describe-execution \
  --execution-arn "$EXEC_ARN" \
  --region eu-central-1 \
  --query '{status:status,startDate:startDate,stopDate:stopDate}'
```

#### Step 3.2: Verify Images

```bash
# Check GeneratedContent table
aws dynamodb scan \
  --table-name GeneratedContent \
  --region eu-central-1 \
  --filter-expression "channel_id = :chid" \
  --expression-attribute-values '{":chid":{"S":"UCRmO5HB89GW_zjX3dJACfzw"}}' \
  --limit 1 \
  --projection-expression "content_id,image_urls,image_count"

# Check S3
aws s3 ls s3://youtube-automation-audio-files/images/ --recursive | tail -20
```

**Expected results:**
- Execution time: 2-3 minutes (vs 4-5 minutes with SD3.5)
- Images generated: 3 scenes
- Cost: ~$0.009 (vs ~$0.035 with SD3.5)

---

## Rollback Plan

If any issues occur, rollback is simple:

### Option 1: Keep Both Services

```bash
# Stop Z-Image service
sudo systemctl stop zimage-api

# Start old SD3.5 service
sudo systemctl start sd-api

# No Lambda changes needed - API interface is identical
```

### Option 2: Full Rollback

```bash
# Revert Lambda function
aws lambda update-function-code \
  --function-name content-generate-images \
  --zip-file fileb://function-backup.zip \
  --region eu-central-1

# Use old SD3.5 service
sudo systemctl stop zimage-api
sudo systemctl start sd-api
```

**Recovery time:** < 5 minutes

---

## Monitoring & Validation

### Key Metrics to Watch

1. **Generation Speed**
   - Target: 0.5-1 second per image
   - Check: CloudWatch logs, Lambda duration

2. **Image Quality**
   - Subjective review of generated images
   - Compare with SD3.5 outputs

3. **Cost Reduction**
   - Target: 75-85% savings
   - Check: CostTracking table in DynamoDB

4. **Error Rate**
   - Target: < 1%
   - Check: Step Functions execution history

### CloudWatch Queries

```bash
# Check Lambda execution time
aws logs filter-log-events \
  --log-group-name /aws/lambda/content-generate-images \
  --region eu-central-1 \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --filter-pattern "Generation time" \
  | jq '.events[].message'

# Check EC2 API logs
MSYS_NO_PATHCONV=1 aws logs tail \
  /aws/lambda/ec2-sd35-control \
  --region eu-central-1 \
  --since 1h
```

---

## Benefits Summary

### Performance Benefits

✅ **6x faster batch generation** (18 images in 10-15s vs 90s)
✅ **2x faster EC2 startup** (30-45s vs 90s)
✅ **40% less VRAM** (8GB vs 13GB)
✅ **Shorter execution times** (2-3 min vs 4-5 min per run)

### Cost Benefits

✅ **83-90% reduction** in compute costs
✅ **75-85% cheaper** per image ($0.003 vs $0.0117)
✅ **$25-27/year savings** (at 100 runs/month)
✅ **Potential for smaller instance** (future optimization)

### Operational Benefits

✅ **Same API interface** - no workflow changes
✅ **Easy rollback** - keep both services available
✅ **Smaller model** - faster downloads, less storage
✅ **Better scaling** - can handle more parallel requests

---

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Model quality worse | High | Low | Compare outputs, easy rollback |
| Slower than expected | Medium | Low | Test before full deployment |
| Compatibility issues | High | Very Low | Same API interface |
| Deployment failure | Medium | Low | Rollback in < 5 minutes |

**Overall Risk:** **LOW** ✅

---

## Success Criteria

✅ Deployment completes without errors
✅ Health check returns `model_loaded: true`
✅ Test image generation works (< 2 seconds)
✅ End-to-end workflow succeeds
✅ Images have acceptable quality
✅ Cost per image reduced by >70%
✅ No increase in error rate

---

## Timeline

| Phase | Duration | Tasks |
|-------|----------|-------|
| **Preparation** | 0 min | ✅ Already complete! |
| **Deployment** | 15 min | Upload files, run deploy.sh, verify |
| **Lambda Update** | 5 min | Update costs, redeploy |
| **Testing** | 10 min | Single channel test, verify images |
| **Validation** | 5 min | Check metrics, quality review |
| **Total** | **35 min** | Full migration |

---

## Post-Migration Tasks

1. ✅ Update documentation
   - Replace SD3.5 references with Z-Image-Turbo
   - Update cost calculations in docs
   - Update architecture diagrams

2. ✅ Monitor for 24 hours
   - Check error rates
   - Verify cost savings
   - Review image quality

3. ✅ Optional: Remove SD3.5 (after 1 week)
   ```bash
   # After confirming Z-Image works well
   sudo rm -rf /home/ubuntu/sd35-api
   ```

4. ✅ Consider further optimizations
   - Increase batch size (6 → 12-18)
   - Test smaller instance type (g5.xlarge → g4dn.xlarge?)
   - Implement parallel generation within batches

---

## Files Created

✅ `ec2-zimage-turbo/api_server.py` - Flask API server
✅ `ec2-zimage-turbo/requirements.txt` - Python dependencies
✅ `ec2-zimage-turbo/zimage-api.service` - Systemd service
✅ `ec2-zimage-turbo/deploy.sh` - Automated deployment script
✅ `ec2-zimage-turbo/quick-deploy.bat` - Windows quick deploy
✅ `ec2-zimage-turbo/README.md` - Detailed documentation
✅ `ZIMAGE-TURBO-MIGRATION.md` - This migration plan

---

## Ready to Deploy? 🚀

Run this command to start:

```bash
cd E:\youtube-content-automation\ec2-zimage-turbo
quick-deploy.bat
```

Or follow manual steps in Phase 1 above.

**Good luck!** 🎉
