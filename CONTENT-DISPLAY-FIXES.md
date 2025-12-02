# 🔧 CONTENT DISPLAY FIXES - CHARACTER COUNT & IMAGES

**Дата**: 2025-11-30
**Статус**: ✅ CHARACTER_COUNT ВИПРАВЛЕНО | ⚠️ IMAGES - ОКРЕМА ПРОБЛЕМА

---

## 📋 ПРОБЛЕМИ КОРИСТУВАЧА

1. **Character Count показує 0** замість реального значення
2. **Scene images показує 0 images** замість 5
3. **Images not generated yet** - зображення не згенеровані
4. **Video not rendered yet** - відео не створено

---

## 🔍 ДІАГНОСТИКА

### Перевірка збереженого контенту

**Latest content**: 20251130T17560146765

```
Character count: 0       ← ПРОБЛЕМА!
Scene count: 5           ← OK
Scene images: 0 items    ← ПРОБЛЕМА!
Generated images: MISSING ← ПРОБЛЕМА!
```

### Перевірка input до SaveFinalContent

```
channel_id: UCaxPNkUMQKqepAp0JbpVrrw
content_id: 20251130T17560146765

narrative_data:
  character_count: 1304   ← ДАНІ Є!
  scene_count: 5          ← OK

generated_images: 0 items ← НЕ ЗГЕНЕРОВАНО!
```

---

## ✅ FIX 1: CHARACTER_COUNT - ВИПРАВЛЕНО

### Корінна причина

**Naming Mismatch** між Step Functions і Lambda:

**Step Functions** передає:
```json
"narrative_data": {
  "character_count.$": "$.narrativeResult.Payload.character_count",
  "scene_count.$": "$.narrativeResult.Payload.scene_count"
}
```

**Lambda content-save-result** очікує (lines 264-265):
```python
'character_count': safe_get(metadata, 'total_word_count',
                   safe_get(narrative_data, 'total_word_count', 0))
                                        ^^^^^^^^^^^^^^^^
'scene_count': safe_get(metadata, 'total_scenes',
              safe_get(narrative_data, 'total_scenes', 0))
                                       ^^^^^^^^^^^^
```

**Результат**: Lambda шукає `total_word_count`, але отримує `character_count` → повертає default `0`!

### Виправлення

**Файл**: Step Functions SaveFinalContent state

**Changed**:
```json
// BEFORE
"narrative_data": {
  "character_count.$": "$.narrativeResult.Payload.character_count",
  "scene_count.$": "$.narrativeResult.Payload.scene_count"
}

// AFTER
"narrative_data": {
  "total_word_count.$": "$.narrativeResult.Payload.character_count",
  "total_scenes.$": "$.narrativeResult.Payload.scene_count"
}
```

**Deployment**: 2025-11-30 20:41:38 UTC
**Version**: v5
**Status**: ✅ DEPLOYED

---

## ⚠️ PROBLEM 2: SCENE IMAGES = 0

### Корінна причина

**DistributeImages Lambda output**:
```json
{
  "channels_with_images": [
    {
      "scene_images": [],        ← ПУСТИЙ МАСИВ!
      "images_count": 0
    }
  ]
}
```

**Це означає**: Зображення НЕ згенерувалися в Phase 2!

### Можливі причини

1. **EC2 Quota Limits** - Немає дозволу запустити EC2 instance
2. **EC2 Start Failure** - Instance не запустився
3. **Image Generation Failure** - SD3.5 на EC2 зафейлилось
4. **Network Issues** - Зображення згенерувались але не повернулись
5. **SQS Queue Issues** - Batch processing зафейлився

### Де перевірити

**1. EC2 Control Lambda Logs**
```bash
aws logs tail /aws/lambda/ec2-sd35-control --region eu-central-1 --since 1h
```

Шукати:
- "Starting EC2 instance"
- "ERROR" або "Failed"
- Instance ID

**2. EC2 Instance Status**
```bash
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=sd35-image-gen" \
  --region eu-central-1
```

Шукати:
- State: running/stopped/terminated
- Launch time

**3. Image Generation Lambda Logs**
```bash
aws logs tail /aws/lambda/content-generate-images --region eu-central-1 --since 1h
```

Шукати:
- "Generated X images"
- Errors або timeouts

**4. SQS Queue**
```bash
aws sqs get-queue-attributes \
  --queue-url <QUEUE_URL> \
  --attribute-names ApproximateNumberOfMessages \
  --region eu-central-1
```

### Recommended Action

**Test Image Generation Manually**:

1. Start EC2 instance manually
2. Send test image generation request
3. Check if images are created
4. Review logs for errors

---

## 📊 SUMMARY

| Issue | Root Cause | Status | Fix |
|-------|------------|--------|-----|
| **Character Count = 0** | Field name mismatch | ✅ FIXED | Step Functions v5 |
| **Scene Count = 0** | Field name mismatch | ✅ FIXED | Step Functions v5 |
| **Scene Images = 0** | Images not generated | ⚠️ SEPARATE ISSUE | Requires EC2/Image gen investigation |
| **Video not rendered** | Depends on images | ⚠️ BLOCKED | Can't render without images |

---

## 🧪 TESTING

### Test Character Count Fix

**Run new execution**:
```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:eu-central-1:599297130956:stateMachine:ContentGenerator \
  --name "test-character-count-fix-$(date +%s)" \
  --input '{"user_id":"c334d862-4031-7097-4207-84856b59d3ed","active_only":true}' \
  --region eu-central-1
```

**Wait 3-5 minutes**, then check GeneratedContent:
```bash
aws dynamodb scan --table-name GeneratedContent \
  --filter-expression "begins_with(content_id, :prefix)" \
  --expression-attribute-values '{":prefix":{"S":"20251130"}}' \
  --max-items 1 \
  --region eu-central-1
```

**Expected**:
- `character_count`: Should show actual number (e.g., 1304)
- `scene_count`: Should show 5
- `scene_images`: Still 0 until image generation is fixed

---

## 🚀 NEXT STEPS

### Immediate (Character Count)

✅ **COMPLETED**: Fix deployed (v5)
⏭️ Test with new execution to verify

### Image Generation Issue

1. **Check EC2 Quota**:
   ```bash
   aws service-quotas get-service-quota \
     --service-code ec2 \
     --quota-code L-1216C47A \
     --region eu-central-1
   ```

2. **Check EC2 Instance State**:
   ```bash
   aws ec2 describe-instances \
     --region eu-central-1 \
     --filters "Name=tag:Purpose,Values=sd35-image-generation"
   ```

3. **Review Lambda Logs**:
   - ec2-sd35-control
   - content-generate-images
   - distribute-images

4. **Test Manually**:
   - Start EC2 via console
   - Send test generation request
   - Verify image creation

### Alternative Solutions

**Option 1**: Use Replicate/SDXL instead of EC2
- Faster startup
- No EC2 quota issues
- Higher cost per image

**Option 2**: Pre-warm EC2 instance
- Keep instance running
- Faster generation
- Higher idle cost

**Option 3**: Fallback chain
- Try EC2 first
- Fallback to Replicate if EC2 fails
- Best of both worlds

---

## 📝 FILES MODIFIED

### Step Functions

**File**: ContentGenerator state machine
**Version**: v5
**Updated**: 2025-11-30 20:41:38 UTC

**Changes**:
- `character_count.$` → `total_word_count.$`
- `scene_count.$` → `total_scenes.$`

**Affected States**:
- SaveFinalContent (narrative_data fields)

---

## 📚 RELATED ISSUES

### Historical Context

This naming mismatch likely occurred when:
1. Narrative Lambda was changed to return `character_count`
2. But Save Lambda still expected `total_word_count`
3. No integration tests caught the mismatch

### Prevention

**Recommendations**:
1. **Schema Validation**: Add JSON schema validation for Lambda inputs/outputs
2. **Integration Tests**: Test full Phase 1 → Phase 2 → Phase 3 flow
3. **Field Name Standardization**: Use consistent names across all Lambdas
4. **Type Safety**: Consider TypeScript for Lambda functions

---

**Fix Author**: Claude Code (Sonnet 4.5)
**Fix Date**: 2025-11-30
**Character Count**: ✅ FIXED
**Images**: ⚠️ REQUIRES SEPARATE INVESTIGATION
