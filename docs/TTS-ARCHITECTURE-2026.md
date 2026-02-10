# TTS Architecture - 2026 (Qwen3-TTS Primary)

## Executive Summary

**Date:** February 2026
**Status:** Qwen3-TTS is PRIMARY provider (97% cost savings)
**Fallback:** AWS Polly (rarely used)
**User Impact:** ZERO (UI unchanged)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│              USER INTERFACE (channels.html)              │
│  User selects TTS voice from dropdown (Qwen3 or Polly)  │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │   DynamoDB Tables    │
              ├──────────────────────┤
              │ • TTSTemplates       │ ← 5 Qwen3 + ~10 Polly voices
              │ • ChannelConfigs     │ ← selected_tts_template
              └──────────┬───────────┘
                         │
                         ▼
           ┌─────────────────────────┐
           │   Step Functions Flow   │
           │ (multi-channel content) │
           └────────────┬────────────┘
                        │
                        ▼
         ┌──────────────────────────────┐
         │   content-audio-tts (Router) │
         │  - Reads channel config       │
         │  - Maps template → provider   │
         └────────────┬─────────────────┘
                      │
          ┌───────────┴────────────┐
          ▼                        ▼
┌─────────────────────┐   ┌──────────────────┐
│ content-audio-      │   │ content-audio-   │
│ qwen3tts            │   │ polly            │
│ (PRIMARY - 97%      │   │ (FALLBACK ONLY)  │
│  cost savings)      │   │                  │
└──────┬──────────────┘   └────────┬─────────┘
       │                           │
       ▼                           ▼
┌──────────────────┐      ┌────────────────┐
│ ec2-qwen3-control│      │ AWS Polly API  │
│ (Start/Stop EC2) │      │ (Neural/Std)   │
└──────┬───────────┘      └────────┬───────┘
       │                           │
       ▼                           │
┌──────────────────┐              │
│ EC2 g4dn.xlarge  │              │
│ 3.71.116.92:5000 │              │
│ Qwen3-TTS-0.6B   │              │
│ Auto-stop: 5min  │              │
└──────┬───────────┘              │
       │                          │
       └──────────┬───────────────┘
                  ▼
          ┌──────────────┐
          │ S3 Bucket    │
          │ Audio Files  │
          └──────────────┘
```

---

## Component Details

### 1. TTS Router (content-audio-tts)

**Location:** `aws/lambda/content-audio-tts/lambda_function.py`
**Role:** Routes TTS requests to appropriate provider

**Logic:**
```python
# 1. Read channel config
channel_config = get_channel_config(channel_id)
selected_template = channel_config['selected_tts_template']

# 2. Lookup template in TTSTemplates
template = get_tts_template(selected_template)
provider = template['tts_config']['provider']  # "qwen3_tts" or "aws_polly_neural"

# 3. Route to provider
if provider == "qwen3_tts":
    result = invoke_qwen3_provider(event, merged_config, user_id)
else:
    result = invoke_polly_provider(event, merged_config, user_id)
```

**Key Features:**
- Provider-agnostic interface
- Automatic fallback if Qwen3 fails
- Cost tracking per provider
- Voice profile mapping (abstract → actual voice)

---

### 2. Qwen3-TTS Provider (PRIMARY)

**Location:** `aws/lambda/content-audio-qwen3tts/lambda_function.py`
**EC2 Instance:** `i-06f9e1fcec1cffa0d` (g4dn.xlarge, eu-central-1)
**Endpoint:** `http://3.71.116.92:5000`

**Flow:**
1. Lambda invokes `ec2-qwen3-control` to start EC2
2. Waits for FastAPI server to be ready (max 3 min)
3. Sends batch TTS request to EC2
4. EC2 generates audio using Qwen3-TTS-12Hz-0.6B-CustomVoice
5. Uploads WAV files to S3
6. Returns audio file metadata

**Available Voices:**
- **Ryan** (Deep Male) - Default
- **Mark** (Neutral Male)
- **Lily** (Soft Female)
- **Emily** (Neutral Female)
- **Jane** (Warm Female)

**Voice Description Feature (NEW):**
```python
# Combines Tone + Narration Style from channel config
voice_description = f"{channel.tone}. {channel.narration_style}"
# Example: "Epic, mysterious, powerful. Omniscient narrator with dramatic flair"

# Passed to Qwen3-TTS model's 'instruct' parameter
wavs, sr = tts_model.generate_custom_voice(
    text=scene.narration,
    speaker="Ryan",
    language="English",
    instruct=voice_description  # ← Controls voice style
)
```

**Cost:**
- **Per video:** ~$0.02 (2 minutes generation time)
- **100 videos/month:** $2/month
- **EC2 Auto-stop:** Stops after 5 min idle
- **Instance cost:** $0.526/hour (only when running)

---

### 3. AWS Polly Provider (FALLBACK)

**Location:** `aws/lambda/content-audio-polly/lambda_function.py`
**Status:** Active but rarely used

**When Used:**
- Qwen3-TTS EC2 fails to start
- Qwen3-TTS generation errors
- Manual override in channel config

**Voices Available:** 15+ voices (Matthew, Joanna, Brian, Amy, etc.)

**Cost:**
- **Per video:** ~$0.72 (4,500 characters × $0.016/1000)
- **100 videos/month:** $72/month
- **36x more expensive than Qwen3**

---

## Database Schema

### TTSTemplates Table

```javascript
{
  template_id: "tts_qwen3_ryan_v1",           // Primary Key
  template_name: "Qwen3-TTS Ryan (Deep Male)",
  type: "tts",
  is_active: true,
  is_default: false,
  created_at: "2026-02-09T...",
  tts_config: {
    provider: "qwen3_tts",                     // or "aws_polly_neural"
    voice_id: "Ryan",                          // Qwen3 speaker name
    voice_profile: "deep_male",                // Abstract profile
    language: "English",
    engine: "neural"                           // (Polly only)
  }
}
```

**Current Templates:**
- 5 Qwen3-TTS voices (tts_qwen3_*)
- ~10 AWS Polly voices (tts_polly_* or legacy)

### ChannelConfigs Table

**TTS-Related Fields:**
```javascript
{
  channel_id: "UCxxxx",
  channel_name: "My Channel",

  // TTS Configuration
  selected_tts_template: "tts_qwen3_ryan_v1",  // Links to TTSTemplates
  tts_service: "qwen3_tts",                     // Override (optional)
  tts_voice_profile: "deep_male",               // Override (optional)

  // Voice Style (NEW - for Qwen3)
  tone: "Epic, mysterious, powerful",           // Merged into voice_description
  narration_style: "Omniscient narrator",       // Merged into voice_description

  // Language
  language: "English"
}
```

---

## Frontend Integration

### UI Component: channels.html

**TTS Template Selector:**
```html
<!-- Line 584-589 -->
<div class="form-group">
  <label>TTS Template</label>
  <select id="selected_tts_template" class="form-control">
    <!-- Populated dynamically from TTSTemplates -->
    <option value="tts_qwen3_ryan_v1">Qwen3-TTS Ryan (Deep Male)</option>
    <option value="tts_qwen3_lily_v1">Qwen3-TTS Lily (Soft Female)</option>
    <option value="tts_polly_matthew_v1">AWS Polly Matthew</option>
    <!-- ... -->
  </select>
</div>
```

**Voice Style Fields (NEW):**
```html
<div class="form-group">
  <label>Tone</label>
  <input type="text" id="tone" placeholder="Epic, Investigative, Calm">
</div>

<div class="form-group">
  <label>Narration Style</label>
  <input type="text" id="narration_style" placeholder="Third-person documentary">
</div>
```

### JavaScript: channels-unified.js

**Template Loading:**
```javascript
// Lines 874-944
async function initializeTemplateSelects() {
  const templates = await fetchTemplates('tts');

  templates.forEach(template => {
    const option = document.createElement('option');
    option.value = template.template_id;
    option.textContent = template.template_name;

    // Mark Qwen3 templates with icon
    if (template.tts_config.provider === 'qwen3_tts') {
      option.textContent += ' ⚡'; // Faster/cheaper
    }

    select.appendChild(option);
  });
}
```

---

## Migration Guide

### From Polly to Qwen3-TTS

**For a single channel:**
1. Open Channel Configuration UI
2. Find "TTS Template" dropdown
3. Select any "Qwen3-TTS" voice (e.g., "Qwen3-TTS Ryan")
4. Optionally set **Tone** and **Narration Style**
5. Save configuration

**Next video generated will use Qwen3-TTS automatically**

### Bulk Migration (DynamoDB)

```bash
# Update all channels to use Qwen3-TTS Ryan
aws dynamodb scan --table-name ChannelConfigs \
  --projection-expression "config_id" \
  | jq -r '.Items[].config_id.S' \
  | xargs -I {} aws dynamodb update-item \
      --table-name ChannelConfigs \
      --key '{"config_id":{"S":"{}"}}' \
      --update-expression "SET selected_tts_template = :tpl" \
      --expression-attribute-values '{":tpl":{"S":"tts_qwen3_ryan_v1"}}'
```

---

## Cost Comparison

| Provider | Cost/Video | Cost/100 Videos | Notes |
|----------|------------|-----------------|-------|
| **Qwen3-TTS** | $0.02 | $2/month | EC2 g4dn.xlarge, auto-stop |
| AWS Polly Neural | $0.72 | $72/month | Pay per character |
| AWS Polly Standard | $0.18 | $18/month | Lower quality |

**Savings:** 97% with Qwen3-TTS

---

## Monitoring & Troubleshooting

### Check Qwen3-TTS Health

```bash
# Via ec2-qwen3-control Lambda
aws lambda invoke \
  --function-name ec2-qwen3-control \
  --payload '{"action":"status"}' \
  response.json

# Direct SSH to EC2
ssh -i n8n-key.pem ubuntu@3.71.116.92
curl http://localhost:5000/health
```

### Check Cost Tracking

```bash
# Query CostTracking table
aws dynamodb scan --table-name CostTracking \
  --filter-expression "service = :svc" \
  --expression-attribute-values '{":svc":{"S":"Qwen3-TTS (EC2)"}}'
```

### Fallback to Polly

If Qwen3-TTS fails, router automatically falls back to Polly:
- Check CloudWatch Logs: `/aws/lambda/content-audio-tts`
- Look for "Qwen3-TTS failed, falling back to AWS Polly"

---

## File Locations

### Lambda Functions
- Router: `aws/lambda/content-audio-tts/lambda_function.py`
- Qwen3: `aws/lambda/content-audio-qwen3tts/lambda_function.py`
- Polly: `aws/lambda/content-audio-polly/lambda_function.py`
- EC2 Control: `aws/lambda/ec2-qwen3-control/lambda_function.py`

### Frontend
- UI: `channels.html` (lines 584-589)
- JS: `js/channels-unified.js` (lines 874-944)

### EC2
- FastAPI: `/opt/dlami/nvme/qwen3-official/server.py`
- Model: `/opt/dlami/nvme/.cache/qwen3-tts-customvoice-0.6b/`
- Service: `systemd` → `qwen3-tts.service`

---

## Future Enhancements

### Planned Features:
1. **Voice Cloning** - Upload audio sample → Custom voice
2. **Multi-language** - Currently English only, expand to 9 languages
3. **Batch Optimization** - Process multiple channels in parallel
4. **Quality Presets** - Fast (0.6B) vs High Quality (1.2B model)

### Provider Roadmap:
- **Q1 2026:** Qwen3-TTS as primary ✅ (DONE)
- **Q2 2026:** Monitor reliability, potentially deprecate Polly
- **Q3 2026:** Add ElevenLabs as premium option
- **Q4 2026:** Custom voice cloning production-ready

---

## FAQ

**Q: Can I still use AWS Polly?**
A: Yes! Polly templates remain available. Select "AWS Polly Matthew" or any Polly voice in the dropdown.

**Q: What happens if Qwen3-TTS fails?**
A: Router automatically falls back to AWS Polly. User sees no error.

**Q: How long does EC2 take to start?**
A: 3-5 minutes on cold start. Once warm, <10 seconds.

**Q: Can I customize voice style?**
A: Yes! Set "Tone" and "Narration Style" fields in channel config. These are passed to Qwen3-TTS as instructions.

**Q: Is audio quality good?**
A: Yes! Qwen3-TTS-0.6B produces natural-sounding speech. Comparable to AWS Polly Neural at 1/36th the cost.

---

**Last Updated:** February 10, 2026
**Document Version:** 2.0
**Author:** Claude Code
**Status:** Production
