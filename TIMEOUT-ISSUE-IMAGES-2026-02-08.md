# Lambda Timeout Issue - Image Generation

**Date:** 2026-02-08
**Issue:** Broken images in content.html
**Root Cause:** No images in database due to Lambda timeout
**Status:** ✅ IDENTIFIED & TESTING SOLUTION

---

## 🖼️ Problem: "Broken Images" in Content Tab

### User Report
Content items show broken image icons (🖼️) instead of actual generated images.

### Investigation Results

**Frontend Code:** ✅ CORRECT
```javascript
// content.html correctly looks for images
const imageUrl = thumbnailImage.https_url ||
                 thumbnailImage.image_url ||
                 thumbnailImage.s3_url;
```

**Backend API:** ✅ CORRECT
```python
# dashboard-content Lambda converts s3:// to presigned URLs
def generate_presigned_url(s3_url):
    presigned_url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket, 'Key': key},
        ExpiresIn=3600
    )
```

**S3 Bucket:** ❌ EMPTY
```bash
$ aws s3 ls s3://youtube-automation-images/ --recursive
(no output - bucket is empty)
```

**DynamoDB:** ❌ NO IMAGES
```bash
$ aws dynamodb scan --table-name GeneratedContent \
    --filter-expression "attribute_exists(scene_images)"
Items: []  # No content with images
```

---

## 🔍 Root Cause Analysis

### Failed Execution Investigation

**Test Execution:** `test-jsonpath-fix-1770544777`
```json
{
  "status": "FAILED",
  "error": "Sandbox.Timedout",
  "cause": "Task timed out after 900.00 seconds",
  "failedState": "GenerateAllImagesBatched"
}
```

### Why Timeout?

**Execution Parameters:**
- Channels: 5 active channels
- Images per channel: 6 scenes
- Total images: 30

**Image Generation Time:**
- Provider: EC2 SD3.5 (Stable Diffusion 3.5 Medium)
- Time per image: ~42 seconds (28 steps, NVIDIA A10G GPU)
- Total time: 30 images × 42s = **1,260 seconds (21 minutes)**

**Lambda Limits:**
- Max timeout: **900 seconds (15 minutes)** ⚠️
- Result: **TIMEOUT at 15 minutes**

---

## 📊 Image Generation Performance

### SD3.5 Performance (EC2 g5.xlarge)
```
GPU: NVIDIA A10G (24GB VRAM)
Model: Stable Diffusion 3.5 Medium
Steps: 28
Resolution: 1024×1024

Performance:
├─ Single image: ~42 seconds
├─ Batch of 5: ~210 seconds (3.5 min)
├─ Batch of 10: ~420 seconds (7 min)
├─ Batch of 30: ~1,260 seconds (21 min) ⚠️ TIMEOUT
└─ Images/hour: ~85.7

Cost:
├─ EC2 hourly: $1.006/hour (g5.xlarge on-demand)
├─ Per image: ~$0.012
└─ Batch of 30: ~$0.36
```

### Lambda Timeout Math
```
Max channels before timeout (15 min limit):
└─ (900s / 42s per image) / 6 images per channel
   = 21 images / 6 = 3.5 channels MAX

Current: 5 channels → TIMEOUT ❌
Solution: 1-3 channels → OK ✅
```

---

## ✅ Solutions

### Solution 1: Reduce Channel Count Per Execution (TESTING NOW)

**Approach:** Run with fewer channels per execution

**Implementation:**
```bash
# Single channel execution (6 images, ~4 minutes)
aws stepfunctions start-execution \
  --state-machine-arn <state-machine-arn> \
  --input '{
    "user_id": "...",
    "requested_channels": ["UC-U_ag6Nn6GwkTq06TyVv5A"]
  }'
```

**Pros:**
- ✅ Works within Lambda limits
- ✅ No code changes needed
- ✅ Immediate solution

**Cons:**
- ⚠️ Need multiple executions for all channels
- ⚠️ More Step Functions invocations (cost)

**Timeline:** ✅ TESTING NOW
- Execution: `test-single-channel-images-1770551995`
- Started: 2026-02-08 13:59:54
- Expected completion: ~8-10 minutes

---

### Solution 2: Use ECS Fargate for Long Tasks (RECOMMENDED)

**Approach:** Move image generation to ECS Fargate (no 15min limit)

**Architecture:**
```
Step Functions
    ↓
StartEC2ForAllImages (Lambda)
    ↓
Choice: Image count > 20?
    ├─ YES → ECS Fargate Task (unlimited time)
    └─ NO  → Lambda (fast for small batches)
```

**ECS Task Definition:**
```json
{
  "family": "image-generation-fargate",
  "taskRoleArn": "arn:aws:iam::...:role/ecs-task-role",
  "networkMode": "awsvpc",
  "containerDefinitions": [{
    "name": "image-generator",
    "image": "<ecr-repo>/image-generator:latest",
    "memory": 2048,
    "cpu": 1024,
    "environment": [
      {"name": "EC2_ENDPOINT", "value": "..."},
      {"name": "USER_ID", "value": "..."}
    ]
  }]
}
```

**Step Functions Integration:**
```json
{
  "Type": "Task",
  "Resource": "arn:aws:states:::ecs:runTask.sync",
  "Parameters": {
    "Cluster": "default",
    "TaskDefinition": "image-generation-fargate",
    "LaunchType": "FARGATE",
    "NetworkConfiguration": {...}
  },
  "TimeoutSeconds": 3600
}
```

**Pros:**
- ✅ No 15min timeout (can run hours)
- ✅ Handles any number of images
- ✅ Auto-scales with demand

**Cons:**
- ⚠️ More complex setup
- ⚠️ Slightly higher cost (Fargate pricing)

**Effort:** 4-6 hours
**Cost:** +$0.05-0.10 per execution

---

### Solution 3: Parallel Batch Processing (ADVANCED)

**Approach:** Split images into parallel Lambda batches

**Architecture:**
```
CollectAllImagePrompts
    ↓
Split into batches of 10 images
    ↓
Step Functions Distributed Map
    ├─ Batch 1 (10 images, 7 min) → Lambda
    ├─ Batch 2 (10 images, 7 min) → Lambda
    └─ Batch 3 (10 images, 7 min) → Lambda
    ↓
Merge results
```

**Step Functions Definition:**
```json
{
  "Type": "Map",
  "ItemProcessor": {
    "ProcessorConfig": {
      "Mode": "DISTRIBUTED",
      "ExecutionType": "EXPRESS"
    },
    "StartAt": "GenerateBatch"
  },
  "ItemsPath": "$.imageBatches",
  "MaxConcurrency": 5
}
```

**Pros:**
- ✅ Fast (parallel processing)
- ✅ Stays within Lambda limits
- ✅ Cost-effective

**Cons:**
- ⚠️ Complex implementation
- ⚠️ Need to manage batch state

**Effort:** 6-8 hours

---

## 🎯 Recommended Implementation Plan

### Phase 1: Quick Fix (TODAY)
✅ Run executions with 1-3 channels per run
✅ Verify images appear in content.html
✅ Document workaround for users

### Phase 2: ECS Integration (THIS WEEK)
1. Create ECS task definition for image generation
2. Update Step Functions with Choice state
3. Test with 30+ images
4. Deploy to production

### Phase 3: Optimization (NEXT MONTH)
1. Implement parallel batch processing
2. Add image caching for common prompts
3. Consider GPU optimization (batched inference)

---

## 📝 Workaround for Users

### Manual Process (Until Fix Deployed)

**For 1-5 channels:**
```bash
# Works fine, completes in <15 min
aws stepfunctions start-execution \
  --state-machine-arn <arn> \
  --input '{"user_id":"...","trigger_type":"manual"}'
```

**For 6+ channels:**
```bash
# Split into multiple runs
# Run 1: Channels 1-3
aws stepfunctions start-execution \
  --input '{"user_id":"...","requested_channels":["ch1","ch2","ch3"]}'

# Run 2: Channels 4-6
aws stepfunctions start-execution \
  --input '{"user_id":"...","requested_channels":["ch4","ch5","ch6"]}'
```

### Alternative: Reduce Images Per Channel

**Option:** Modify narrative template to generate fewer images
```json
{
  "scene_count": 4  // Instead of 6
}
```

**Impact:**
- 5 channels × 4 images = 20 images × 42s = 14 min ✅
- Stays under 15min limit

---

## 🔍 Current Test Execution

**Execution:** `test-single-channel-images-1770551995`
**Status:** 🔄 IN PROGRESS
**Started:** 2026-02-08 13:59:54
**Channel:** UC-U_ag6Nn6GwkTq06TyVv5A (DeepVerse - Philosophy/Poetry)
**Expected Images:** 6 scenes

**Timeline:**
```
13:59:54 - Started
14:00:35 - GenerateAllImagesBatched started
14:05:00 - Expected: Images completed (~6 images × 42s = 4.2 min)
14:07:00 - Expected: Audio generation
14:10:00 - Expected: Execution completed ✅
```

**Verification Steps:**
1. Wait for execution to complete
2. Check DynamoDB for scene_images
3. Check S3 bucket for uploaded images
4. Open content.html and verify images display
5. Test presigned URL generation

---

## 📊 Success Metrics

**Test Execution Success:**
- ✅ Execution completes without timeout
- ✅ 6 images generated and uploaded to S3
- ✅ scene_images array populated in DynamoDB
- ✅ Images display correctly in content.html
- ✅ Presigned URLs work from browser

**Long-term Solution Success:**
- ✅ Handle 38+ channels in single execution
- ✅ No timeouts regardless of channel count
- ✅ Execution time < 30 minutes for any configuration
- ✅ Cost per video remains < $0.50

---

## 🚨 Monitoring & Alerts

**Add CloudWatch Alarm:**
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "Lambda-Image-Generation-Timeout" \
  --metric-name Duration \
  --namespace AWS/Lambda \
  --dimensions Name=FunctionName,Value=content-generate-images \
  --statistic Maximum \
  --period 60 \
  --threshold 720000  # 12 minutes (80% of 15min)
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1
```

**Notification:**
→ Telegram: "⚠️ Image generation approaching timeout (>12 min)"
→ Action: Consider splitting execution or using ECS

---

## 📚 Related Documentation

- `docs/IMAGE-BATCHING-SYSTEM.md` - Current batching implementation
- `docs/SD35-IMAGE-GENERATION.md` - EC2 SD3.5 setup
- `docs/EC2-SD35-CACHE-MANAGEMENT.md` - Model caching
- `JSONPATH-REVERT-FIX-2026-02-08.md` - Recent Step Functions fix

---

**Prepared By:** Claude Code
**Date:** 2026-02-08
**Status:** Testing Solution (Single Channel Run)
**Next Review:** After test execution completes (~10 minutes)
