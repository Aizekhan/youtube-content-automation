# Session: EC2 Service Readiness Fixes — 2026-02-18

## Проблема

Тест `images-fix-test3-1771380925` "успішно завершився" (SUCCEEDED) через `VideoAssemblySkipped`,
але насправді обидві гілки Phase2 тихо провалились:

- **Гілка A (Картинки)**: 10/10 зображень — `[Errno 111] Connection refused`
- **Гілка B (Аудіо)**: Lambda `content-audio-qwen3tts` зависла → timeout → Catch block → пусті дані

Виглядало як "дурдом": один запис каже є картинки, інший каже є тільки озвучка.
Це тому що video assembly читала СТАРИЙ DynamoDB запис з попереднього тесту.

---

## Корінні причини

### Баг 1 — Картинки (Z-Image сервіс не готовий)

**Ланцюжок**:
1. `StartEC2ForImages` (ec2-zimage-control) повернув `statusCode=200` ("instance running")
2. EC2 instance справді запущений, але **Z-Image ML сервіс** на порту 5000 ще завантажується
3. Lambda `content-generate-images` **одразу** намагається з'єднатись → `[Errno 111] Connection refused`
4. Всі 10 зображень отримали `status=failed`

**Ключовий момент**: EC2 "running" ≠ ML сервіс готовий. Z-Image завантажує моделі 30-120с після старту EC2.

### Баг 2 — Аудіо (Lambda timeout)

**Ланцюжок**:
1. `StartEC2ForAudio` (ec2-qwen3-control) повернув `statusCode=202` ("still starting")
2. Lambda `content-audio-qwen3tts` отримала endpoint і почала health check loop
3. `max_wait=300s` health check + аудіо генерація → загальний час перевищив **900s Lambda timeout**
4. Lambda timeout → Step Functions `Catch` block → `AudioGenerationFailed` (Pass state)
5. `AudioGenerationFailed` встановив `distributedAudio.data.channels_with_audio = []`
6. `merge-channel-data` отримав порожній аудіо список → всі канали з `audio_files=[]`

---

## Виправлення

### Фікс 1 — `content-generate-images/lambda_function.py`

**Додана функція** `wait_for_image_service(endpoint, max_wait=120)` (лінія ~216):
- Парсить host:port з EC2 endpoint URL (формат: `http://IP:5000`)
- Пробує `GET /health` кожні 10 секунд до 120 секунд
- Якщо отримав будь-яку HTTP відповідь → сервіс готовий
- Якщо `Connection refused` → чекає і повторює
- Після 120с — попередження і продовжує (не блокує виконання)

**Додано виклик** в `lambda_handler` перед `handle_multi_channel_batch` (лінія ~763):
```python
# Wait for Z-Image service to be ready (EC2 may be running but service still starting)
if EC2_ENDPOINT:
    wait_for_image_service(EC2_ENDPOINT, max_wait=120)
```

### Фікс 2 — Step Function (WaitState для аудіо EC2)

**Доданий стан** `WaitForAudioEC2` між `StartEC2ForAudio` і `GenerateAllAudioBatched`:
```json
"WaitForAudioEC2": {
    "Type": "Wait",
    "Seconds": 90,
    "Comment": "Wait for Qwen3-TTS service to start on EC2 (ML model loading takes 60-120s)",
    "Next": "GenerateAllAudioBatched"
}
```

**Чому WaitState краще ніж зменшення max_wait**:
- SF-рівневий wait завжди надійний, не залежить від Lambda timeout
- Lambda отримує вже-готовий сервіс → `max_wait=300` health check loop майже не використовується
- `max_wait=300` залишається як страхова мережа

**Новий маршрут Branch B**:
```
StartEC2ForAudio → WaitForAudioEC2 (90s) → GenerateAllAudioBatched → ...
```

---

## Файли змінені

| Файл | Зміна |
|------|-------|
| `aws/lambda/content-generate-images/lambda_function.py` | Додана `wait_for_image_service()` + виклик перед генерацією |
| AWS Step Functions `ContentGenerator` | Доданий стан `WaitForAudioEC2` (90s Wait) |

---

## Деплой

```bash
# Lambda
powershell Compress-Archive -Path * -DestinationPath function.zip -Force
aws lambda update-function-code --function-name content-generate-images --zip-file fileb://function.zip

# Step Function (з /tmp/new-sf.json)
aws stepfunctions update-state-machine \
  --state-machine-arn "arn:aws:states:eu-central-1:599297130956:stateMachine:ContentGenerator" \
  --definition file:///tmp/new-sf.json
```

---

## Тест

Запущено: `both-fixes-test2-1771384166`
Input: `{"user_id":"c334d862-4031-7097-4207-84856b59d3ed"}`
Статус: виконується (очікуваний час ~12-15 хв)

**Очікуваний результат**:
- `GenerateAllImagesBatched` → `images_generated=10, images_failed=0`
- `GenerateAllAudioBatched` → `audio_files=9` (9 сцен)
- `merge-channel-data` → `audio_files=9 items, scene_images=10 items`
- `content-save-result` → збережено з `audio_scene_count=9, image_count=10`

---

## Примітки для наступної сесії

### Якщо тест пройшов успішно
- Перевірити що video assembly (`EstimateVideoDuration`, `AssembleVideo`) теж спрацювала
- Перевірити DynamoDB запис — чи збережені audio + image URLs
- Перевірити S3 — чи є реальні файли

### Якщо тест знову провалився
- Перевірити чи `WaitForAudioEC2` 90s достатньо (можливо збільшити до 120s)
- Перевірити чи `/health` endpoint у Z-Image сервісу існує (можливо треба `GET /` або інший endpoint)
- Перевірити логи `content-generate-images` Lambda для рядків "Waiting for image service"

### Архітектура Phase2 Parallel
```
Phase2Parallel {
  Branch A (Images):
    CollectImagePrompts → GenerateAllImagesBatched → DistributeImagesToChannels → BranchADone
    Catch → ImageGenerationFailed (Pass, empty channels_with_images)

  Branch B (Audio):
    CollectAllAudioScenes → CheckIfAnyAudio → StartEC2ForAudio →
    WaitForAudioEC2 (90s) → GenerateAllAudioBatched → DistributeAudioToChannels →
    StopEC2AfterAudio → BranchBDone
    Catch → AudioGenerationFailed (Pass, empty channels_with_audio)
}
→ MergePhase2Results (Pass):
    channels_with_images = phase2Results[0].distributedData.data.channels_with_images
    channels_with_audio  = phase2Results[1].distributedAudio.data.channels_with_audio
→ merge-channel-data Lambda
```

### Важливе: test input
```json
{"user_id":"c334d862-4031-7097-4207-84856b59d3ed"}
```
БЕЗ `user_id` SF одразу FAILED (GetActiveChannels вимагає $.user_id).
