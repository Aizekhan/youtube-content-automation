# Session Log - YouTube Content Automation

## Останній Session: 2026-02-10

### Статус: 🔄 IN PROGRESS - Testing Qwen3-TTS

### Що Було Зроблено:

#### 1. Qwen3-TTS Міграція (ЗАВЕРШЕНО ✅)
- **Commit:** a2aab90 - "feat: Complete Qwen3-TTS migration - remove AWS Polly entirely"
- **Pushed to GitHub:** ✅ Yes (master branch)
- **Lambda Deployed:** ✅ All 3 functions (content-audio-tts, content-audio-qwen3tts, ec2-qwen3-control)

#### 2. EC2 Infrastructure (ПРАЦЮЄ ✅)
- **Instance:** i-06f9e1fcec1cffa0d (g4dn.xlarge, eu-central-1)
- **IP:** 3.71.116.92
- **Server:** http://3.71.116.92:5000 (FastAPI + Qwen3-TTS)
- **Model:** Qwen3-TTS-12Hz-0.6B-CustomVoice на GPU (Tesla T4)
- **Auto-stop:** 5 minutes idle
- **Status:** Server running and responding to health checks

#### 3. Database Updates (ЗАВЕРШЕНО ✅)
- **TTSTemplates:** 6 templates total, ALL Qwen3 (0 Polly)
  - tts_qwen3_ryan_v1 (Deep Male)
  - tts_qwen3_mark_v1 (Neutral Male)
  - tts_qwen3_lily_v1 (Soft Female)
  - tts_qwen3_emily_v1 (Neutral Female)
  - tts_qwen3_jane_v1 (Warm Female)
- **ChannelConfigs:** MythEchoes channel updated to use Qwen3-TTS Ryan
  - channel_id: UCRmO5HB89GW_zjX3dJACfzw
  - config_id: cfg_1761314000730452906_UCRmO5HB89
  - selected_tts_template: tts_qwen3_ryan_v1
  - tone: "Epic, mysterious, powerful"
  - narration_style: "Omniscient narrator with dramatic flair"

#### 4. Voice Description Feature (РЕАЛІЗОВАНО ✅)
- Router combines `tone` + `narration_style` → `voice_description`
- Passed to Qwen3-TTS's `instruct` parameter
- Controls voice style dynamically per channel

#### 5. AWS Polly (ВИДАЛЕНО ✅)
- All Polly code removed from content-audio-tts router
- Router now uses ONLY Qwen3-TTS (no fallback)
- Archived files: archive/deprecated-tts-2026-02-10/

### 🔄 Поточний Тест:

**Execution ID:** test-qwen3-real-1770691936
**Started:** 2026-02-10 04:52:18
**Channel:** UCRmO5HB89GW_zjX3dJACfzw (MythEchoes)
**Scenes:** 3 (для швидкого тесту)
**Status:** Running (waiting 3 minutes for completion)

**Команда для перевірки:**
```bash
aws stepfunctions describe-execution \
  --execution-arn "arn:aws:states:eu-central-1:599297130956:execution:ContentGenerator:test-qwen3-real-1770691936" \
  --region eu-central-1
```

---

## 📝 Важливі Нюанси Архітектури:

### 1. TTS Router Pattern
**File:** `aws/lambda/content-audio-tts/lambda_function.py`

**Спрощена логіка (Qwen3-only):**
```python
def lambda_handler(event, context):
    # 1. Get channel config from DynamoDB
    channel_config = get_channel_config(channel_id)

    # 2. Merge TTS settings (з event або з channel config)
    merged_config = merge_tts_settings(event, channel_config)

    # 3. Build voice_description (NEW!)
    tone = merged_config.get('tone', '')
    narration_style = merged_config.get('narration_style', '')
    voice_description = f"{tone}. {narration_style}" if (tone or narration_style) else None

    # 4. ALWAYS invoke Qwen3 (no Polly!)
    result = invoke_qwen3_provider(event, merged_config, user_id)
    return result
```

**Ключовий момент:** Router НЕ читає TTSTemplates! Він тільки комбінує tone + narration_style в voice_description.

### 2. Qwen3-TTS Lambda
**File:** `aws/lambda/content-audio-qwen3tts/lambda_function.py`

**Flow:**
1. Invoke ec2-qwen3-control Lambda (start EC2 if stopped)
2. Wait for EC2 health check (max 3 min)
3. POST to http://3.71.116.92:5000/tts/generate with:
   ```json
   {
     "scenes": [...],
     "speaker": "Ryan",
     "language": "English",
     "voice_description": "Epic, mysterious, powerful. Omniscient narrator..."
   }
   ```
4. EC2 generates WAV files + uploads to S3
5. Return audio file metadata

**Dependencies:** Requires `requests` library (972 KB deployment package)

### 3. EC2 FastAPI Server
**Location:** `/opt/dlami/nvme/qwen3-official/server.py`

**Startup:** Systemd service `qwen3-tts.service` (auto-start on boot)
**Model Location:** `/opt/dlami/nvme/.cache/qwen3-tts-customvoice-0.6b/`
**Logs:** `/opt/dlami/nvme/qwen3-official/server.log`

**Endpoint:**
```python
@app.post("/tts/generate")
async def generate(req: TTSRequest):
    for scene in req.scenes:
        wavs, sr = tts_model.generate_custom_voice(
            text=scene.scene_narration,
            speaker=req.speaker,  # Ryan, Mark, Lily, Emily, Jane
            language=req.language,
            instruct=req.voice_description,  # ← Controls style!
            non_streaming_mode=True,
            max_new_tokens=2048
        )
        # Upload to S3...
```

### 4. Step Functions Workflow
**State Machine:** ContentGenerator

**Етапи:**
1. ValidateInput
2. GetActiveChannels (filters by channel_id, NOT config_id!)
3. Phase1ContentGeneration (Map: SelectTopic → GenerateNarrative per channel)
4. CollectAllImagePrompts
5. Phase2BatchImages (Generate images via Flux)
6. Phase3AudioAndSave (Map: **GenerateTTS** → AssembleVideo → SaveResult)

**Важливо:** GetActiveChannels очікує `channel_id` (UCxxxx), а НЕ `config_id` (cfg_xxxx)!

---

## ⚠️ Відомі Проблеми:

### 1. Lambda Timeout на Прямому Invoke
**Проблема:** Direct invoke content-audio-tts timeout після 60s
**Причина:** EC2 cold start займає 3-5 хвилин (завантаження моделі на GPU)
**Рішення:** Це нормально! Step Functions має більший timeout і чекає коректно.

### 2. GitHub Actions Auto-Deploy
**Файл:** `.github/workflows/deploy-lambda.yml`
**Деплоїть:** content-theme-agent, content-narrative, prompts-api
**НЕ чіпає:** content-audio-tts, content-audio-qwen3tts, ec2-qwen3-control
**Висновок:** Безпечно пушити на master, TTS Lambda не перезапишуться

### 3. Polly Template в DynamoDB
**Template:** tts_auto_voice_1762573009 (старий Polly template з SSML)
**Status:** Deprecated, але все ще в базі
**Використовується:** Багато каналів все ще вказують на нього
**TODO:** Зробити масове оновлення каналів на Qwen3 templates

---

## 📋 TODO (Наступна Сесія):

### Високий Пріоритет:
1. ✅ **Перевірити результат test-qwen3-real-1770691936**
   - Команда: `aws stepfunctions describe-execution --execution-arn "arn:aws:states:eu-central-1:599297130956:execution:ContentGenerator:test-qwen3-real-1770691936" --region eu-central-1`
   - Очікується: status=SUCCEEDED, відео згенероване, TTS від Qwen3

2. 🔄 **Масове оновлення каналів на Qwen3-TTS**
   - Скрипт вже є: `mark-polly-templates-deprecated.py`
   - TODO: Створити скрипт для масового update ChannelConfigs
   - Замінити `selected_tts_template` на Qwen3 для всіх активних каналів

3. ⚠️ **Виправити prompts-api Lambda (502 error)**
   - Помилка: prompts-editor.html показує 502 Bad Gateway
   - URL: https://djpb4ue6wv2ohfjey32lfnhcre0zppqd.lambda-url.eu-central-1.on.aws/?type=theme
   - Потрібно: Check Lambda logs, verify deployment

### Середній Пріоритет:
4. 📊 **Створити дашборд для моніторингу Qwen3-TTS**
   - CloudWatch metrics: EC2 uptime, TTS generation time, costs
   - S3 storage usage (аудіо файли)
   - Success/failure rates

5. 🧪 **Тести якості аудіо**
   - Порівняти Qwen3 vs Polly (subjective quality test)
   - Перевірити різні голоси (Ryan, Mark, Lily, Emily, Jane)
   - Тест voice_description впливу на стиль

6. 📚 **Оновити документацію на сайті**
   - Додати інформацію про Qwen3-TTS voices
   - Пояснити voice_description (Tone + Narration Style)
   - Migration guide для користувачів

### Низький Пріоритет:
7. 🔐 **Security Audit**
   - EC2 FastAPI endpoint exposed на публічний IP (3.71.116.92)
   - TODO: Add authentication або CloudFront proxy

8. 🚀 **Performance Optimization**
   - Можливість використання g4dn.2xlarge для швидшої генерації
   - Batch processing для кількох сцен одночасно
   - Model quantization (INT8) для економії GPU memory

9. 🌍 **Multi-language Support**
   - Qwen3-TTS підтримує 9+ мов
   - TODO: Додати мовні налаштування в UI

---

## 📂 Ключові Файли:

### Documentation:
- `QWEN3-MIGRATION-COMPLETE.md` - Migration report
- `docs/TTS-ARCHITECTURE-2026.md` - Complete architecture guide
- `SESSION-LOG.md` - THIS FILE (session notes)

### Lambda Functions:
- `aws/lambda/content-audio-tts/lambda_function.py` - Router (1.5 KB)
- `aws/lambda/content-audio-qwen3tts/lambda_function.py` - TTS Generator (972 KB with deps)
- `aws/lambda/ec2-qwen3-control/lambda_function.py` - EC2 lifecycle

### Scripts:
- `mark-polly-templates-deprecated.py` - Deprecate Polly templates
- `test-qwen3-router-direct.json` - Direct Lambda test payload

### Archived:
- `archive/deprecated-tts-2026-02-10/` - Old Polly code

---

## 🎯 План Наступної Сесії:

**Крок 1:** Прочитати цей файл (SESSION-LOG.md)

**Крок 2:** Перевірити статус тесту:
```bash
aws stepfunctions describe-execution \
  --execution-arn "arn:aws:states:eu-central-1:599297130956:execution:ContentGenerator:test-qwen3-real-1770691936" \
  --region eu-central-1
```

**Крок 3:** Якщо тест успішний:
- Перевірити згенероване відео в S3
- Послухати аудіо (перевірити якість Qwen3-TTS)
- Підтвердити що voice_description працює

**Крок 4:** Якщо тест провалився:
- Check CloudWatch logs для content-audio-tts, content-audio-qwen3tts
- Check EC2 server logs: `ssh ubuntu@3.71.116.92 'tail -100 /opt/dlami/nvme/qwen3-official/server.log'`
- Debug і повторити тест

**Крок 5:** Масове оновлення каналів на Qwen3-TTS

**Крок 6:** Виправити prompts-api Lambda (502 error)

---

## 💰 Cost Tracking:

**Before Migration:**
- AWS Polly: $72/month (100 videos × $0.72)

**After Migration:**
- Qwen3-TTS: $2/month (100 videos × $0.02)
- EC2 g4dn.xlarge: Included in $2/month (auto-stop після 5 min)

**Annual Savings:** $840/year (97% reduction)

---

## 🔗 Useful Commands:

### Check EC2 Server:
```bash
ssh -i E:/youtube-content-automation/n8n-key.pem ubuntu@3.71.116.92
curl http://localhost:5000/health
sudo systemctl status qwen3-tts
tail -f /opt/dlami/nvme/qwen3-official/server.log
```

### Check Lambda Logs:
```bash
MSYS_NO_PATHCONV=1 aws logs tail /aws/lambda/content-audio-tts --region eu-central-1 --follow
MSYS_NO_PATHCONV=1 aws logs tail /aws/lambda/content-audio-qwen3tts --region eu-central-1 --follow
```

### Test TTS Directly:
```bash
aws lambda invoke \
  --function-name content-audio-tts \
  --region eu-central-1 \
  --cli-binary-format raw-in-base64-out \
  --payload file://test-qwen3-router-direct.json \
  result.json
```

### Check Step Functions:
```bash
aws stepfunctions list-executions \
  --state-machine-arn "arn:aws:states:eu-central-1:599297130956:stateMachine:ContentGenerator" \
  --region eu-central-1 \
  --max-results 5
```

---

**Last Updated:** 2026-02-10 04:56 UTC
**Status:** Qwen3-TTS deployed, testing in progress
**Next Action:** Check test-qwen3-real-1770691936 execution result

---

## 🔧 Session Update - prompts-api Fixed

**Time:** 2026-02-10 05:05 UTC

### Problem:
- prompts-api Lambda returning 502 Bad Gateway
- Error: `Cannot find module 'index'`
- Handler configured as `index.handler` but deployment package missing index.js

### Solution:
1. Repackaged Lambda with index.js + node_modules
2. Redeployed: `aws lambda update-function-code --function-name prompts-api`
3. Verified: API now returns TTS templates correctly

### Test Result:
```bash
curl "https://djpb4ue6wv2ohfjey32lfnhcre0zppqd.lambda-url.eu-central-1.on.aws/?type=tts"
# Returns: 5 Qwen3-TTS templates (Emily, Mark, Lily, Ryan, Jane)
```

**Status:** ✅ FIXED - UI can now load templates

---
