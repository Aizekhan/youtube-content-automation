# Session: Parallel Audio Batching - 2026-02-13

## ЗАВЕРШЕНО (Completed Tasks)

### 1. content-audio-qwen3tts Lambda - Parallel Batching
**Файл:** `aws/lambda/content-audio-qwen3tts/lambda_function.py`

**Зміни:**
- Замінено `requests` на `urllib.request` (no external dependencies)
- Додано `concurrent.futures.ThreadPoolExecutor` для паралельної обробки
- Створено `process_single_scene()` worker function
- Замінено sequential loop на parallel processing з `max_workers=8`
- **Результат:** Тепер 18 scenes генеруються паралельно (до 8 одночасно) замість послідовно

**Файли:**
- Modified: `aws/lambda/content-audio-qwen3tts/lambda_function.py`
- Script: `modify_audio_lambda.py` (може бути видалений)

---

### 2. collect-audio-scenes Lambda
**Файл:** `aws/lambda/collect-audio-scenes/lambda_function.py`

**Призначення:** Збирає всі audio scenes з усіх каналів для централізованого батчингу

**Input:**
```json
{
  "channels_data": [...]  // Phase1 results with narrativeResult.Payload
}
```

**Output:**
```json
{
  "all_audio_scenes": [
    {
      "channel_id": "UCxxx",
      "content_id": "temp_xxx",
      "narrative_id": "...",
      "scene_id": "scene_1",
      "text": "...",
      "language": "en",
      "speaker": "default",
      "voice_description": "..."
    }
  ],
  "total_scenes": 18,
  "ec2_endpoint": "http://..."
}
```

---

### 3. distribute-audio Lambda
**Файл:** `aws/lambda/distribute-audio/lambda_function.py`

**Призначення:** Розподіляє згенеровані аудіо файли назад по каналах

**Input:**
```json
{
  "generated_audio": [...],  // From content-audio-qwen3tts
  "channels_data": [...]      // Original channel data
}
```

**Output:**
```json
{
  "channels_with_audio": [
    {
      "channel_id": "UCxxx",
      "audio_files": [...],
      "total_duration_ms": 45000,
      "scene_images": [...],  // Preserved from previous step
      ...
    }
  ]
}
```

**Важливо:** Preserves `scene_images` from previous distribute-images step

---

## ЗАЛИШАЄТЬСЯ ЗРОБИТИ (Remaining Tasks)

### 4. Модифікувати Step Functions (IN PROGRESS)

**Файл:** `E:/tmp/add_audio_to_phase2.py` (створено, але НЕ ЗАПУЩЕНО)

**Поточна архітектура Phase2:**
```
Branch 0: Qwen3 EC2 Control (Start)
Branch 1: CollectImagePrompts -> GenerateImages -> DistributeImages
Branch 2: Collect Videos
```

**Нова архітектура Phase2 Branch 1:**
```
CollectAssetsData (Parallel):
  - CollectImagePrompts
  - CollectAudioScenes

GenerateAssets (Parallel):
  - GenerateImages
  - GenerateAudio (content-audio-qwen3tts with parallel batching)

DistributeAssets (Parallel):
  - DistributeImages
  - DistributeAudio
```

**ПОПЕРЕДЖЕННЯ:** Скрипт створено, але потребує:
1. Перевірки JSONPath references
2. Тестування на валідність Step Functions syntax
3. Можливо, потрібні додаткові зміни в ResultPath/ResultSelector

**Наступні кроки:**
1. Запустити скрипт: `python E:/tmp/add_audio_to_phase2.py`
2. Перевірити generated definition на валідність
3. Можливо, потрібні ручні правки JSONPath
4. Deploy modified Step Functions

---

### 5. Видалити генерацію аудіо з Phase3

**Що потрібно:**
- Видалити audio generation з Phase3CollectSaveParallel
- Залишити тільки Save operations
- Audio вже буде згенеровано в Phase2

**Файл для модифікації:** Step Functions definition (після deploy з попереднього кроку)

---

### 6. Задеплоїти всі Lambda

**Які Lambda потрібно задеплоїти:**
1. `content-audio-qwen3tts` (modified with parallel batching)
2. `collect-audio-scenes` (new)
3. `distribute-audio` (new)

**Команди:**
```bash
# 1. content-audio-qwen3tts
cd aws/lambda/content-audio-qwen3tts
python create_zip.py  # Якщо є, або вручну zip
aws lambda update-function-code --function-name content-audio-qwen3tts --zip-file fileb://function.zip --region eu-central-1

# 2. collect-audio-scenes
cd aws/lambda/collect-audio-scenes
zip -r function.zip lambda_function.py
aws lambda create-function --function-name collect-audio-scenes --runtime python3.12 --role arn:aws:iam::599297130956:role/lambda-execution-role --handler lambda_function.lambda_handler --zip-file fileb://function.zip --region eu-central-1 --timeout 300

# 3. distribute-audio
cd aws/lambda/distribute-audio
zip -r function.zip lambda_function.py
aws lambda create-function --function-name distribute-audio --runtime python3.12 --role arn:aws:iam::599297130956:role/lambda-execution-role --handler lambda_function.lambda_handler --zip-file fileb://function.zip --region eu-central-1 --timeout 60
```

---

### 7. Задеплоїти Step Functions

**Після модифікації definition:**
```bash
aws stepfunctions update-state-machine \
  --state-machine-arn arn:aws:states:eu-central-1:599297130956:stateMachine:ContentGenerator \
  --definition file://E:/tmp/modified-sf-definition.json \
  --region eu-central-1
```

---

### 8. Протестувати повний workflow

**Test execution:**
```bash
EXEC_NAME="PARALLEL-AUDIO-TEST-$(date +%s)"
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:eu-central-1:599297130956:stateMachine:ContentGenerator \
  --name "$EXEC_NAME" \
  --input '{"user_id":"c334d862-4031-7097-4207-84856b59d3ed","channel_id":"UCRmO5HB89GW_zjX3dJACfzw"}' \
  --region eu-central-1
```

**Що перевірити:**
1. Phase2 виконується паралельно (Images + Audio одночасно)
2. Audio генерується швидше (parallel batching works)
3. Audio files правильно attach до channels
4. Phase3 більше НЕ генерує audio (тільки saves)
5. Загальний час виконання <10 minutes (було ~12-18 min)

---

## ОЧІКУВАНІ РЕЗУЛЬТАТИ

**До оптимізації:**
- Sequential audio generation: ~9-18 minutes для 18 scenes
- Total execution time: ~12+ minutes

**Після оптимізації:**
- Parallel audio generation: ~2-4 minutes для 18 scenes (8 workers)
- Audio + Images паралельно: ~4-6 minutes total для Phase2
- **Очікуваний total execution time: ~6-8 minutes**

---

## КРИТИЧНІ NOTES

1. **NO EMOJIS** in any code (user request)
2. Step Functions modification - найскладніша частина, потребує ретельної перевірки
3. JSONPath references можуть бути неправильними в auto-generated script
4. Обов'язково тестувати кожен крок перед deployment
5. Backup поточної Step Functions definition перед deploy

---

## FILES CREATED/MODIFIED

**Modified:**
- `aws/lambda/content-audio-qwen3tts/lambda_function.py` - parallel batching

**Created:**
- `aws/lambda/collect-audio-scenes/lambda_function.py`
- `aws/lambda/distribute-audio/lambda_function.py`
- `E:/tmp/add_audio_to_phase2.py` - script to modify Step Functions (NOT RUN YET)

**Temporary/Helper:**
- `modify_audio_lambda.py` - can be deleted
- `E:/tmp/current-sf-definition.json` - current Step Functions definition

---

## NEXT SESSION START

1. Run `python E:/tmp/add_audio_to_phase2.py`
2. Check generated `E:/tmp/modified-sf-definition.json`
3. Fix any JSONPath issues
4. Deploy Lambdas (collect-audio-scenes, distribute-audio, content-audio-qwen3tts)
5. Deploy Step Functions
6. Test complete workflow
7. Verify performance improvements
