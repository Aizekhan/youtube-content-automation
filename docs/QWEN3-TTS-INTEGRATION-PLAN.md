# Qwen3-TTS Integration Plan

**Date:** 2026-02-09
**Status:** Design Phase
**Goal:** Add Qwen3-TTS as alternative TTS provider alongside AWS Polly

---

## 📊 Current TTS Architecture

### Configuration Flow

```
ChannelConfigs (DynamoDB)
└── selected_tts_template → TTSTemplates (DynamoDB)
    ├── tts_config
    │   ├── service: "aws_polly_neural"
    │   ├── voice_id: "Matthew"  (optional, direct voice)
    │   └── voice_profile: "deep_male"  (or profile mapping)
    └── tts_settings
        ├── tts_service: "aws_polly_neural"
        └── tts_voice_profile: "deep_male"
```

### Configuration Priority (content-audio-tts Lambda)

```python
# Line 240-242 in content-audio-tts/lambda_function.py
merged_config = {
    'tts_service': tts_settings.get('tts_service') or
                   tts_config.get('service') or
                   channel_config.get('tts_service', 'aws_polly_neural'),
    'tts_voice_profile': final_voice_profile
}
```

**Priority:**
1. TTSTemplate.tts_config.voice_id (direct voice, manual mode)
2. TTSTemplate.tts_settings.tts_voice_profile (template voice profile)
3. TTSTemplate.tts_config.voice_profile (fallback profile)
4. ChannelConfig.tts_voice_profile (channel-level profile)
5. Default: 'neutral_male'

### Voice Mapping (config_merger.py)

```python
# map_voice_profile_to_actual_voice() function
voice_profile (abstract) → actual_voice (provider-specific)

Example:
'deep_male' + 'aws_polly_neural' → 'Matthew'
'deep_male' + 'elevenlabs' → 'Adam'
'deep_male' + 'qwen3_tts' → 'Ryan'  # NEW
```

### Step Functions Integration

```json
{
  "GenerateAudio": {
    "Type": "Task",
    "Resource": "arn:aws:lambda:invoke",
    "Parameters": {
      "FunctionName": "content-audio-tts",
      "Payload": {
        "channel_id.$": "$.channel_id",
        "narrative_id.$": "$.narrativeResult.Payload.narrative_id",
        "scenes.$": "$.narrativeResult.Payload.scenes"
      }
    },
    "ResultPath": "$.audioResult"
  }
}
```

**Output from content-audio-tts:**
```json
{
  "audio_files": [...],
  "voice_id": "Matthew",
  "voice_profile": "deep_male",
  "tts_service": "aws_polly_neural",  // Used for tracking
  "total_duration_ms": 45000,
  "cost_usd": 0.08
}
```

---

## 🔧 Integration Strategy

### Option 1: Provider Router Pattern (RECOMMENDED)

Keep existing `content-audio-tts` Lambda as router, add provider-specific Lambdas.

**Pros:**
- ✅ No breaking changes to Step Functions
- ✅ Easy to add more providers later
- ✅ Centralized configuration logic
- ✅ Backward compatible

**Architecture:**
```
Step Functions
    ↓
content-audio-tts (Router)
    ├── tts_service == "aws_polly_neural" → Call AWS Polly directly
    ├── tts_service == "qwen3_tts" → Invoke content-audio-qwen3tts
    └── tts_service == "elevenlabs" → Invoke content-audio-elevenlabs
```

### Option 2: Step Functions Choice State

Add Choice state in Step Functions to route to different Lambdas.

**Pros:**
- ✅ Clear separation of concerns
- ✅ Better visibility in Step Functions console

**Cons:**
- ❌ Requires Step Functions changes
- ❌ Need to pass tts_service through workflow
- ❌ More complex for adding providers

---

## 🎯 Recommended Implementation

**Use Option 1: Provider Router Pattern**

### Phase 1: Add Qwen3-TTS Infrastructure

**1.1 Create EC2 g4dn.xlarge Setup**
- File: `aws/ec2-qwen3-tts-setup.sh`
- AMI: Deep Learning OSS Nvidia Driver GPU PyTorch 2.7 (Ubuntu 22.04)
- Components:
  - FastAPI server with Qwen3-TTS models
  - Auto-stop service (5 min idle timeout)
  - Health monitoring

**1.2 Create EC2 Control Lambda**
- Function: `ec2-qwen3-control`
- Actions: start, stop, status
- Mirrors: `ec2-sd35-control` architecture

**1.3 Create TTS Lambda**
- Function: `content-audio-qwen3tts`
- Input: Same as `content-audio-tts`
- Output: Same format as AWS Polly Lambda

### Phase 2: Update Provider Router

**2.1 Modify content-audio-tts Lambda**
```python
def lambda_handler(event, context):
    # ... existing config loading ...

    tts_service = merged_config['tts_service']

    # Route to appropriate provider
    if tts_service == 'qwen3_tts':
        # Delegate to Qwen3-TTS Lambda
        return invoke_qwen3_tts(event, merged_config)
    elif tts_service in ['aws_polly_neural', 'aws_polly_standard']:
        # Existing AWS Polly code
        return generate_with_polly(event, merged_config)
    else:
        # Default to Polly
        return generate_with_polly(event, merged_config)
```

**2.2 Add Voice Mapping for Qwen3-TTS**
```python
# config_merger.py - map_voice_profile_to_actual_voice()

'deep_male': {
    'aws_polly_neural': 'Matthew',
    'qwen3_tts': 'Ryan',  # NEW
    'elevenlabs': 'Adam'
},
'soft_female': {
    'aws_polly_neural': 'Joanna',
    'qwen3_tts': 'Lily',  # NEW
    'elevenlabs': 'Bella'
}
```

### Phase 3: Add UI Configuration

**3.1 Update TTSTemplates DynamoDB Schema**
```json
{
  "template_id": "tts_qwen3_ryan_v1",
  "template_name": "Qwen3 TTS - Ryan Voice",
  "tts_settings": {
    "tts_service": "qwen3_tts",
    "tts_voice_profile": "deep_male"
  },
  "tts_config": {
    "service": "qwen3_tts",
    "voice_profile": "deep_male",
    "speaker": "Ryan",  // Qwen3-specific
    "language": "English"  // Qwen3-specific
  }
}
```

**3.2 Update channels.html UI**
```html
<select id="tts_service">
  <option value="aws_polly_neural">AWS Polly (Neural)</option>
  <option value="aws_polly_standard">AWS Polly (Standard)</option>
  <option value="qwen3_tts">Qwen3-TTS (Open Source)</option>
  <option value="elevenlabs">ElevenLabs (Premium)</option>
</select>
```

**3.3 Update Voice Selection UI**
```javascript
// Show different voice options based on tts_service
if (tts_service === 'qwen3_tts') {
  showQwen3Voices();  // Ryan, Lily, Emily, etc.
} else if (tts_service.startsWith('aws_polly')) {
  showPollyVoices();  // Matthew, Joanna, etc.
}
```

### Phase 4: Cost Tracking

**4.1 Update Cost Logging**
```python
def log_qwen3_cost(channel_id, content_id, duration_sec, user_id=None):
    """
    Log Qwen3-TTS cost (EC2 usage time)
    """
    # g4dn.xlarge On-Demand: $0.526/hour
    hourly_rate = 0.526
    cost = (duration_sec / 3600) * hourly_rate

    cost_table.put_item(Item={
        'date': datetime.utcnow().strftime('%Y-%m-%d'),
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'service': 'Qwen3-TTS (EC2)',
        'operation': 'audio_generation',
        'channel_id': channel_id,
        'content_id': content_id,
        'cost_usd': Decimal(str(cost)),
        'units': duration_sec,
        'details': {
            'generation_time_sec': duration_sec,
            'instance_type': 'g4dn.xlarge'
        },
        'user_id': user_id
    })
```

---

## 📁 File Structure

```
aws/lambda/
├── content-audio-tts/          # Router Lambda (MODIFY)
│   ├── lambda_function.py       # Add provider routing
│   └── shared/
│       └── config_merger.py     # Add Qwen3 voice mapping
│
├── content-audio-qwen3tts/     # NEW - Qwen3-TTS Provider
│   ├── lambda_function.py       # Qwen3-TTS implementation
│   ├── create_zip.py
│   └── requirements.txt
│
└── ec2-qwen3-control/          # NEW - EC2 Control
    ├── lambda_function.py       # Start/Stop/Status
    └── create_zip.py

aws/
├── ec2-qwen3-tts-setup.sh      # NEW - EC2 UserData script
└── iam-policy-qwen3-ec2.json   # NEW - IAM policy

docs/
└── QWEN3-TTS-INTEGRATION-PLAN.md  # This file
```

---

## 🔄 Migration Path

### Stage 1: Infrastructure (No Breaking Changes)
1. Create EC2 setup script
2. Create ec2-qwen3-control Lambda
3. Create content-audio-qwen3tts Lambda
4. Test Qwen3 Lambda in isolation

### Stage 2: Router Integration (Backward Compatible)
1. Update content-audio-tts to route providers
2. Add Qwen3 voice mapping to config_merger
3. Test with `tts_service=qwen3_tts`
4. Existing configs still use Polly (no change)

### Stage 3: UI and Templates
1. Add Qwen3-TTS option to UI dropdowns
2. Create Qwen3 TTS templates in DynamoDB
3. Users can opt-in to Qwen3-TTS

### Stage 4: Testing and Rollout
1. Test on development channel
2. Compare quality and cost
3. Gradual rollout to production channels

---

## ✅ Success Criteria

- [ ] Qwen3-TTS generates audio identical format to Polly
- [ ] Switching `tts_service` in UI changes provider seamlessly
- [ ] Cost tracking shows separate entries for Polly vs Qwen3
- [ ] Step Functions workflow unchanged (backward compatible)
- [ ] EC2 auto-stops after 5 min idle
- [ ] Total time increase < 2 minutes per video
- [ ] Users can switch back to Polly anytime

---

## 🚀 Next Steps

1. **Review this plan** - Confirm architecture approach
2. **Create infrastructure** - EC2 setup + Lambdas
3. **Test integration** - Isolated testing
4. **Update UI** - Add provider selection
5. **Production rollout** - Gradual migration

---

**Last Updated:** 2026-02-09
**Author:** Claude Code
**Status:** Awaiting approval
