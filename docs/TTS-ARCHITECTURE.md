# TTS Pipeline Architecture v2.0

**Date:** 2025-11-25
**Status:** Production Ready ✅

## Overview

New multi-provider TTS architecture with programmatic SSML generation, separating content generation from voice synthesis markup.

### Key Innovation

**Before:** LLM generates narrative WITH SSML tags → Polly TTS
**After:** LLM generates PLAIN TEXT → SSML Generator (programmatic) → Multi-Provider TTS

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Step Functions Pipeline                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────┐  Plain Text  ┌──────────────────┐
│ content-        │─────────────>│ ssml-            │
│ narrative       │  + genre     │ generator        │
│ Lambda          │  + variation │ Lambda           │
└─────────────────┘              └──────────────────┘
    │                                     │
    │ Generates:                          │ Generates:
    │ - story_title                       │ - scene_narration_ssml
    │ - scenes (plain text)               │   (with genre-specific markup)
    │ - variation_used                    │
    │   (whisper/dramatic/normal)         │
    │                                     │
    └─────────────┬───────────────────────┘
                  │ SSML + metadata
                  ▼
         ┌─────────────────┐
         │ Multi-Provider  │
         │ TTS Router      │
         └─────────────────┘
                  │
         ┌────────┴────────┐
         │                 │
         ▼                 ▼
┌─────────────┐   ┌─────────────┐
│ AWS Polly   │   │ ElevenLabs  │
│ (Neural/    │   │ (Future)    │
│  Standard)  │   │             │
└─────────────┘   └─────────────┘
         │                 │
         └────────┬────────┘
                  │ MP3 files
                  ▼
           ┌──────────────┐
           │ S3 Storage   │
           └──────────────┘
```

---

## Components

### 1. **content-narrative Lambda**
**Purpose:** Generate story content using OpenAI GPT-4
**Input:** Channel config + topic
**Output:** Plain text narrative with mood detection

**Key Changes:**
- ✅ Generates PLAIN TEXT (no SSML tags)
- ✅ Detects scene mood: whisper, dramatic, action, normal
- ✅ Sets `variation_used` field for each scene
- ✅ Reduced output tokens (~15-20% savings)

**Prompt Update:**
```
OLD: "Add SSML markup to scene_narration field"
NEW: "Generate PLAIN TEXT narration WITHOUT any markup tags"
```

---

### 2. **ssml-generator Lambda** ⭐ NEW
**Purpose:** Programmatically generate TTS-specific markup
**Input:** Plain text scenes + genre + TTS service
**Output:** Scenes with SSML/plain text based on provider

**Supported Providers:**
- ✅ AWS Polly (SSML with genre-specific effects)
- ✅ ElevenLabs (plain text - no SSML support)
- 🚧 Kokoro TTS (future)

**Genre Rules:**
| Genre   | Rate  | Volume | Whisper | Pause Multiplier |
|---------|-------|--------|---------|------------------|
| Horror  | slow  | -      | Yes     | 1.5x (450ms)     |
| Action  | fast  | loud   | No      | 0.7x (210ms)     |
| Mystery | med   | medium | Selective| 1.2x (360ms)    |

**SSML Features:**
- Automatic pause insertion (sentence/comma boundaries)
- Genre-specific prosody (rate, pitch, volume)
- Amazon Polly effects (whisper phonation)
- Variation support (normal/dramatic/whisper/action/fast)

**Example Output:**
```xml
<!-- Horror Genre -->
<speak><amazon:effect phonation="soft"><prosody rate="slow">
The inn stood at the edge of the forgotten village,
<break time="225ms"/> shrouded in mist and melancholy.
<break time="450ms"/> As I approached...
</prosody></amazon:effect></speak>
```

---

### 3. **content-audio-polly Lambda**
**Purpose:** AWS Polly TTS synthesis
**Input:** Scenes with SSML
**Output:** MP3 audio files on S3

**Updates:**
- ✅ Accepts `scene_narration_ssml` field
- ✅ Falls back to `scene_narration` if SSML not present
- ✅ Supports both Neural and Standard engines
- ✅ Cost tracking to DynamoDB CostTracking table

---

### 4. **Step Functions Updates**
**New State:** `GenerateSSML`
**Position:** Between `GetTTSConfig` and `GenerateAudioPolly`

**Flow:**
```
GetTTSConfig → GenerateSSML → GenerateAudioPolly → SaveFinalContent
```

**Critical Fix:**
- Genre parameter now uses JsonPath syntax: `"genre.$": "$.genre"`
- Previously passed as object: `"genre": {"$": "$.genre"}` ❌

---

## Benefits

### 1. **LLM-Agnostic**
- OpenAI often generates invalid/inconsistent SSML
- Any LLM can now generate plain text
- No need to teach SSML syntax to LLM

### 2. **Quality Control**
- Programmatic SSML is always valid
- Consistent formatting across all content
- Easy to update voice rules without regenerating stories

### 3. **Cost Savings**
- ~15-20% reduction in OpenAI output tokens
- No SSML markup in LLM response

### 4. **Flexibility**
- Change voice style without regenerating narrative
- A/B test different voice effects on same story
- Quick genre rule updates

### 5. **Multi-Provider Support**
- Same plain text input works for all TTS services
- Provider-specific markup generated automatically
- Easy to add new TTS providers

---

## Monitoring

### CloudWatch Alarms
- `ssml-generator-high-error-rate` - >3 errors in 5 min
- `content-narrative-high-error-rate` - >2 errors in 5 min
- `content-generator-execution-failures` - Step Functions failures
- `high-daily-tts-costs` - >$5 per day

### Metrics
- `SuccessfulSSMLGeneration` - tracks SSML generator success
- `FailedSSMLGeneration` - tracks errors
- Standard Lambda metrics (invocations, duration, errors)

### Dashboard
Navigate to: CloudWatch → Dashboards → `TTS-Pipeline-Monitoring`

---

## Deployment

### Prerequisites
- AWS CLI configured
- Python 3.11
- Appropriate IAM permissions

### Deploy SSML Generator
```bash
cd aws/lambda/ssml-generator
python -m zipfile -c function.zip lambda_function.py
aws lambda update-function-code \
  --function-name ssml-generator \
  --zip-file fileb://function.zip \
  --region eu-central-1
```

### Deploy Updated Narrative Lambda
```bash
cd aws/lambda/content-narrative
python create_zip.py
aws lambda update-function-code \
  --function-name content-narrative \
  --zip-file fileb://function.zip \
  --region eu-central-1
```

### Update Step Functions
```bash
aws stepfunctions update-state-machine \
  --state-machine-arn arn:aws:states:eu-central-1:599297130956:stateMachine:ContentGenerator \
  --definition file://step-function-with-ssml-generator.json \
  --region eu-central-1
```

---

## Testing

### Test Individual Components

**SSML Generator:**
```bash
aws lambda invoke \
  --function-name ssml-generator \
  --payload '{"scenes":[{"scene_number":1,"scene_narration":"Test text","variation_used":"normal"}],"tts_service":"aws_polly_neural","genre":"Horror"}' \
  output.json
```

**Full Pipeline:**
```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:eu-central-1:599297130956:stateMachine:ContentGenerator \
  --name "test-$(date +%s)"
```

### Verify SSML Output
1. Check CloudWatch logs: `/aws/lambda/ssml-generator`
2. Verify SSML structure contains: `<speak>`, `<prosody>`, `<break>`
3. Check genre-specific effects applied correctly

---

## Troubleshooting

### SSML Generator Errors

**Error:** `unhashable type: 'dict'`
**Cause:** Genre passed as JsonPath object instead of string
**Fix:** Use `"genre.$": "$.genre"` in Step Function definition

**Error:** `No scenes provided`
**Cause:** Empty scenes array
**Fix:** Check Narrative Lambda output

### Audio Generation Issues

**Problem:** Polly returns empty audio
**Cause:** Field name mismatch
**Fix:** content-audio-polly checks multiple fields: `scene_narration_ssml`, `scene_narration`, `text_with_ssml`

### Step Functions Failures

1. Check execution history in AWS Console
2. Look for `ExecutionFailed` events
3. Check Lambda logs for error details
4. Verify all Lambda functions are deployed

---

## Future Enhancements

### Planned
- [ ] ElevenLabs TTS integration (Q1 2026)
- [ ] Kokoro TTS integration (Q2 2026)
- [ ] Voice cloning support
- [ ] Multi-language SSML generation
- [ ] Real-time voice preview in dashboard

### Under Consideration
- [ ] Custom voice profiles per channel
- [ ] Emotion detection and voice modulation
- [ ] Background music integration in SSML
- [ ] Voice A/B testing framework

---

## References

- [SSML Reference (AWS Polly)](https://docs.aws.amazon.com/polly/latest/dg/supportedtags.html)
- [Genre Rules Documentation](./GENRE-RULES.md)
- [TTS Provider Integration Guide](./TTS-PROVIDERS.md)
- [Cost Analysis Report](./COST-ANALYSIS.md)

---

## Changelog

### v2.0 (2025-11-25)
- ✅ Implemented ssml-generator Lambda
- ✅ Updated Narrative Lambda to generate plain text
- ✅ Modified Step Functions pipeline
- ✅ Added CloudWatch monitoring
- ✅ Genre-specific SSML rules (Horror, Action, Mystery)
- ✅ End-to-end testing completed

### v1.0 (Prior to 2025-11-24)
- OpenAI generates SSML directly
- Single TTS provider (AWS Polly)
- Limited genre support

---

**Maintained by:** YouTube Content Automation Team
**Last Updated:** 2025-11-25
**Status:** ✅ Production Ready
