# Auto Voice Display Issue - Fix Report

**Date:** 2025-11-25
**Issue:** Content dashboard shows "Обраний голос: Auto" instead of actual voice name
**Status:** ✅ Fixed

---

## Problem Description

User reported that generated content displays "Обраний голос: Auto" instead of showing the actual voice used (e.g., "Matthew", "deep_male").

---

## Root Cause Analysis

### Investigation Steps

1. **Checked DynamoDB GeneratedContent table:**
   - Found voice data IS being saved correctly:
     - `voice_id`: "Matthew"
     - `voice_profile`: "deep_male"
     - `voice`: "deep_male"
     - `tts_service`: "aws_polly_neural"

2. **Checked content-save-result Lambda:**
   - Lines 230-232, 246 - correctly saves voice fields from event
   - Line 246 sets fallback: `event.get('voice_profile', event.get('voice_id', 'Auto'))`

3. **Checked Step Functions definition:**
   - Lines 223-225 - correctly passes voice data:
     ```json
     "voice_id.$": "$.audioResult.Payload.voice_id",
     "voice_profile.$": "$.audioResult.Payload.voice_profile",
     "tts_service.$": "$.audioResult.Payload.tts_service"
     ```

4. **Found the bug in content.html:**
   - **Line 952** (before fix):
     ```javascript
     const selectedVoice = item.narrative_data?.selected_voice || item.tts_voice_profile || 'Auto';
     ```
   - **Problem:** Looking for wrong field names!
     - `item.narrative_data.selected_voice` ❌ doesn't exist
     - `item.tts_voice_profile` ❌ doesn't exist (actual field is `item.voice_profile`)
     - Always fell through to `'Auto'` default

---

## Solution

### Code Change

**File:** `content.html:952`

**Before:**
```javascript
const selectedVoice = item.narrative_data?.selected_voice || item.tts_voice_profile || 'Auto';
```

**After:**
```javascript
// FIX: Use correct field names (voice, voice_profile, voice_id from content-save-result)
const selectedVoice = item.voice || item.voice_profile || item.voice_id || 'Auto';
```

### Field Priority

Now correctly looks for voice in this order:
1. `item.voice` - frontend-friendly field (e.g., "deep_male")
2. `item.voice_profile` - TTS profile name (e.g., "deep_male")
3. `item.voice_id` - actual Polly voice (e.g., "Matthew")
4. `'Auto'` - fallback if all are null

---

## Data Flow Summary

### Full Voice Data Pipeline

```
1. GetTTSConfig (Step Functions)
   └─> tts_voice_profile from ChannelConfig

2. GenerateAudioPolly Lambda (content-audio-tts)
   ├─> Maps voice_profile to voice_id: "deep_male" → "Matthew"
   └─> Returns:
       ├─ voice_id: "Matthew"
       ├─ voice_profile: "deep_male"
       └─ tts_service: "aws_polly_neural"

3. Step Functions (SaveFinalContent state)
   └─> Passes voice_id, voice_profile, tts_service to content-save-result

4. content-save-result Lambda
   └─> Saves to DynamoDB:
       ├─ voice_id: "Matthew"
       ├─ voice_profile: "deep_male"
       ├─ voice: "deep_male" (frontend field)
       └─ tts_service: "aws_polly_neural"

5. dashboard-content Lambda
   └─> Returns items (no modification to voice fields)

6. content.html (FIXED)
   └─> Displays: item.voice || item.voice_profile || item.voice_id
```

---

## Testing

### Before Fix
```
User sees: "Обраний голос: Auto"
Actual data in DB: voice_id = "Matthew", voice_profile = "deep_male"
```

### After Fix
```
User will see: "Обраний голос: deep_male" (from item.voice)
```

---

## Deployment

### Option 1: Deploy to Server (Recommended)

```bash
# Copy to server
scp content.html ubuntu@3.75.97.188:/home/ubuntu/web-admin/html/content.html

# Or use existing deployment process
```

### Option 2: Verify Locally

```bash
# Open content.html in browser
# Generate new content with full pipeline
# Check that voice displays correctly (not "Auto")
```

---

## Notes

### Why "Auto" was shown for old content?

The issue was that:
1. Old content (type: `theme_generation`) doesn't have voice fields → correctly filtered out by dashboard-content Lambda
2. Full content (type: `mega_generation`) has voice fields, but frontend was looking for wrong field names

### Files Involved

- `content.html:952` - Frontend display (FIXED)
- `aws/lambda/content-save-result/lambda_function.py:230-232,246` - Backend save (OK)
- Step Functions SaveFinalContent state - Parameter passing (OK)
- `aws/lambda/content-audio-tts/lambda_function.py:302-304` - Voice data return (OK)

---

## Related Issues

None - this is an isolated frontend display bug.

---

**Status:** ✅ Fixed in content.html
**Next Steps:** Deploy to production and verify voice displays correctly
**Impact:** Low - cosmetic display issue, no data loss or functional impact
