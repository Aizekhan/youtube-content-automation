# Architecture Nuances - Critical Details

## 🔴 КРИТИЧНІ НЮАНСИ (обов'язково знати!)

### 1. channel_id vs config_id
**ПРОБЛЕМА:** В системі є 2 типи ID і вони РІЗНІ!

- **channel_id** (YouTube): `UCRmO5HB89GW_zjX3dJACfzw`
  - Використовується в Step Functions workflow
  - Зберігається в GeneratedContent table
  - GetActiveChannels фільтрує саме по ньому

- **config_id** (Internal): `cfg_1761314000730452906_UCRmO5HB89`
  - Primary key в ChannelConfigs table
  - Генерується як `cfg_{timestamp}_{shortened_channel_id}`
  - НЕ використовується в Step Functions!

**Рішення:** Завжди витягуй channel_id з ChannelConfigs.channel_id, не використовуй config_id!

```python
# ❌ WRONG:
channel_ids = ["cfg_1761314000730452906_UCRmO5HB89"]

# ✅ CORRECT:
config = dynamodb.get_item(Key={"config_id": "cfg_..."})
channel_id = config["channel_id"]  # "UCRmO5HB89GW_zjX3dJACfzw"
channel_ids = [channel_id]
```

---

### 2. TTS Router НЕ читає TTSTemplates
**СЮРПРИЗ:** Router (`content-audio-tts`) НЕ дивиться в TTSTemplates table!

**Що він робить:**
1. Читає `channel_config` з ChannelConfigs
2. Читає `tts_settings` з event (якщо є)
3. Мерджить їх (event має пріоритет)
4. Будує `voice_description` з `tone` + `narration_style`
5. Викликає content-audio-qwen3tts

**Що він НЕ робить:**
- ❌ НЕ читає TTSTemplates
- ❌ НЕ маппить template_id → provider
- ❌ НЕ вибирає між Polly/Qwen3 (завжди Qwen3!)

**Чому так?**
Спрощення після видалення Polly. Тепер router - це просто "merger + voice_description builder".

**Висновок:** `selected_tts_template` в ChannelConfigs більше не використовується router'ом! Він залишився для UI compatibility.

---

### 3. Voice Description Magic
**Як працює:**

```javascript
// ChannelConfigs table:
{
  "tone": "Epic, mysterious, powerful",
  "narration_style": "Omniscient narrator with dramatic flair"
}

// Router combines:
voice_description = "Epic, mysterious, powerful. Omniscient narrator with dramatic flair"

// Qwen3-TTS Lambda sends to EC2:
{
  "voice_description": "Epic, mysterious, powerful. Omniscient narrator with dramatic flair"
}

// EC2 FastAPI calls model:
wavs, sr = tts_model.generate_custom_voice(
    text="...",
    speaker="Ryan",
    language="English",
    instruct="Epic, mysterious, powerful. Omniscient narrator with dramatic flair"  # ← HERE!
)
```

**instruct parameter** контролює:
- Voice tone (epic, calm, mysterious)
- Speaking style (narrator, conversational, documentary)
- Emotional delivery (dramatic, neutral, energetic)

**Limitations:**
- Works best with clear, concise instructions (max ~50 words)
- Too vague → no effect
- Too complex → unpredictable results

---

### 4. EC2 Auto-Stop Mechanism
**Де реалізовано:** Systemd timer на EC2 instance

**Як працює:**
1. FastAPI server логує останній request timestamp
2. Systemd timer запускається кожні 1 хв: `check-idle.sh`
3. Якщо idle > 5 min → `sudo shutdown -h now`
4. Instance stops (не terminate!)

**Restart flow:**
1. Lambda invoke ec2-qwen3-control with `{"action": "start"}`
2. ec2-qwen3-control calls `ec2.start_instances()`
3. Instance boots (~2-3 min)
4. Systemd auto-starts qwen3-tts.service
5. Model loads on GPU (~1-2 min)
6. Server ready (~3-5 min total cold start)

**Cost savings:**
- Running: $0.526/hour
- Stopped: $0 (тільки EBS storage: ~$0.10/month)
- Typical usage: 10-20 min/day → $3-5/month

---

### 5. Step Functions Map State Behavior
**Phase1ContentGeneration:**
```json
{
  "Type": "Map",
  "ItemsPath": "$.channels",
  "Iterator": {
    "StartAt": "SelectTopic",
    "States": {
      "SelectTopic": {...},
      "GenerateNarrative": {...}
    }
  }
}
```

**Критично:**
- Map state виконує ітератор ПАРАЛЕЛЬНО для кожного каналу
- Max concurrency: default (без ліміту)
- Якщо 1 channel fails → весь Map fails (unless Catch блок)
- Output: масив результатів у тому ж порядку що input

**Phase3AudioAndSave:**
- Теж Map state
- Виконує TTS → Video Assembly → Save для кожного каналу
- TTS генерація найдовша (60-120s з EC2 cold start)
- Якщо EC2 не стартує → Lambda timeout → Map fails

**Висновок:** Завжди перевіряй що EC2 працює перед запуском Step Functions, інакше перший канал провалиться на TTS.

---

### 6. S3 Audio File Naming
**Pattern:** `qwen3-tts/{channel_id}/{content_id}/scene_{scene_id}.wav`

**Example:**
```
s3://youtube-automation-audio-files/qwen3-tts/UCRmO5HB89GW_zjX3dJACfzw/content_1770691936/scene_1.wav
s3://youtube-automation-audio-files/qwen3-tts/UCRmO5HB89GW_zjX3dJACfzw/content_1770691936/scene_2.wav
```

**Metadata:**
```python
{
    "scene_id": "scene_1",
    "audio_file": "scene_1.wav",
    "s3_key": "qwen3-tts/UCRmO5HB89GW_zjX3dJACfzw/content_1770691936/scene_1.wav",
    "duration": 6.06,
    "sample_rate": 24000,
    "format": "wav"
}
```

**Format:** Always WAV (not MP3!)
- Sample rate: 24kHz
- Channels: Mono
- Bit depth: 16-bit PCM

**Чому WAV, а не MP3?**
- Video assembly (FFmpeg) працює краще з lossless
- Якість важливіша за розмір
- S3 storage дешевий ($0.023/GB/month)

---

### 7. Lambda Deployment Package Quirks

**content-audio-tts (Router):**
- Size: 1.5 KB (tiny!)
- No external dependencies
- Deployment: просто zip lambda_function.py

**content-audio-qwen3tts (TTS Generator):**
- Size: 972 KB (великий!)
- Dependencies: requests + urllib3 + certifi + charset_normalizer + idna
- Deployment:
  ```bash
  pip install requests -t .
  python create_zip_with_deps.py
  aws lambda update-function-code --function-name content-audio-qwen3tts --zip-file fileb://function.zip
  ```

**Проблема:** Windows encoding issues
- Emoji characters (✅, 🚀) в коді → UnicodeEncodeError
- Рішення: використовуй ASCII ([OK], [Deploy])

**Проблема:** Lambda caching
- Lambda може кешувати старий код до 15 min
- Рішення: update environment variable щоб force refresh
  ```bash
  aws lambda update-function-configuration --function-name XXX --environment Variables={FORCE_UPDATE=1}
  ```

---

### 8. GitHub Actions Auto-Deploy
**File:** `.github/workflows/deploy-lambda.yml`

**Triggers:**
- Push to master branch
- Path filter: `aws/lambda/**`

**Deploys:** (hardcoded list!)
1. content-theme-agent
2. content-narrative
3. prompts-api

**Does NOT deploy:**
- ❌ content-audio-tts
- ❌ content-audio-qwen3tts
- ❌ ec2-qwen3-control
- ❌ Any other Lambda!

**Чому?**
Workflow не знає про нові TTS Lambda. Треба або:
1. Додати їх в workflow (recommended)
2. Або деплоїти вручну (current approach)

**Висновок:** Безпечно пушити TTS зміни на master, вони не перезапишуться автоматично.

---

### 9. DynamoDB Scan Limitations
**GetActiveChannels Lambda:**

```python
# This is SLOW (scans whole table):
response = table.scan(
    FilterExpression=Attr('channel_id').is_in(channel_ids)
)
```

**Проблема:**
- ChannelConfigs table має 100+ records
- Scan читає ВСЮ таблицю, потім фільтрує
- Cost: 1 RCU per 4KB scanned (не filtered!)
- Latency: ~500ms для 100 records

**Рішення (TODO):**
- Створити GSI (Global Secondary Index) по channel_id
- Query замість Scan (100x швидше)
- Or: batch get_item якщо channel_ids < 100

---

### 10. Voice Models на EC2
**Location:** `/opt/dlami/nvme/.cache/qwen3-tts-customvoice-0.6b/`

**Size:** ~2.5 GB

**Available Speakers:**
- Ryan (deep_male)
- Mark (neutral_male)
- Lily (soft_female)
- Emily (neutral_female)
- Jane (warm_female)

**Extensibility:**
Model підтримує до 50+ voices з різних мов:
- English: 10+ voices
- Chinese: 15+ voices
- Japanese, Korean, Spanish, French, German, Russian, Arabic

**TODO:** Додати більше voices в TTSTemplates table

**Custom Voice Cloning (experimental):**
```python
# Upload audio sample (10-30 seconds of clean speech)
tts_model.generate_custom_voice(
    text="...",
    speaker_audio_path="sample.wav",  # Reference voice
    language="English",
    instruct="..."
)
```

---

## 🔧 Debug Patterns

### Pattern 1: Lambda Timeout
**Symptom:** Lambda runs for 60s then fails

**Root Cause:** EC2 cold start
- Instance stopped
- Takes 3-5 min to start + load model
- Lambda timeout: 60s (too short!)

**Solution:**
1. Start EC2 manually before testing:
   ```bash
   aws lambda invoke --function-name ec2-qwen3-control --payload '{"action":"start"}' response.json
   ```
2. Wait 3 minutes
3. Test TTS Lambda

### Pattern 2: Empty Step Functions Output
**Symptom:** Execution succeeds but returns empty array

**Root Cause:** GetActiveChannels filters out all channels

**Debug:**
```bash
# Check what GetActiveChannels received:
aws stepfunctions get-execution-history \
  --execution-arn "arn:..." \
  --query "events[?type=='TaskSucceeded' && contains(taskSucceededEventDetails.resource, 'get-active-channels')]"
```

**Common mistakes:**
- Passed config_id instead of channel_id
- Channel not active in database
- channel_id typo

### Pattern 3: 502 Bad Gateway from Lambda URL
**Symptom:** UI shows "502 Bad Gateway" when calling Lambda

**Root Causes:**
1. Lambda crashed during cold start
2. Runtime error (import failed)
3. Lambda timeout (> 30s for URL invocation)

**Debug:**
```bash
MSYS_NO_PATHCONV=1 aws logs tail /aws/lambda/prompts-api --region eu-central-1 --since 5m
```

Look for:
- `ImportError`
- `SyntaxError`
- `Task timed out`

---

## 📊 Monitoring Checklist

Перед production release перевір:

- [ ] EC2 auto-stop працює (check after 5 min idle)
- [ ] TTS generation successful для всіх 5 voices
- [ ] Audio quality acceptable (subjective listening test)
- [ ] S3 storage не переповнюється (set lifecycle policy!)
- [ ] CloudWatch alarms for:
  - [ ] EC2 instance status check failed
  - [ ] Lambda errors > 5% (content-audio-*)
  - [ ] Step Functions failed executions
- [ ] Cost tracking в CostTracking table
- [ ] Backup strategy для GeneratedContent

---

**Last Updated:** 2026-02-10
**Author:** Claude Code (based on implementation experience)
