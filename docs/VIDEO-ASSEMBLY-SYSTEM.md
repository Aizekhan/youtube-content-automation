# 🎬 Video Assembly - Система Автоматичного Монтажу

**Версія:** 1.0
**Дата:** 2025-11-18
**Статус:** ✅ Production Ready
**Регіон:** eu-central-1

---

## 📋 Зміст

1. [Огляд](#огляд)
2. [Архітектура](#архітектура)
3. [Гібридний підхід (Lambda + ECS)](#гібридний-підхід-lambda--ecs)
4. [Візуальні ефекти](#візуальні-ефекти)
5. [Вартість та оптимізація](#вартість-та-оптимізація)
6. [Робочий процес](#робочий-процес)
7. [Налаштування](#налаштування)
8. [Troubleshooting](#troubleshooting)

---

## Огляд

### Що це?

**Video Assembly System** - це система автоматичного монтажу готового MP4 відео з окремих компонентів:
- 📝 Narrative scenes
- 🎙️ Audio files (TTS)
- 🖼️ Generated images
- 🎵 Background music & SFX
- 📢 CTA segments (Call-To-Action)

### Що генерує система?

**Вхід:**
```
DynamoDB (GeneratedContent):
  - narrative_data (сцени з текстом)
  - audio_urls (S3 шляхи до TTS файлів)
  - image_urls (S3 шляхи до згенерованих зображень)
  - sfx_data (звукові ефекти)
  - cta_segments (заклики до дії)
```

**Вихід:**
```
S3 (youtube-automation-data-grucia/videos/):
  final-video-{content_id}.mp4

Характеристики:
  - Resolution: 1920x1080 (Full HD)
  - FPS: 30
  - Codec: H.264
  - Audio: AAC, 192 kbps
  - Готове до завантаження на YouTube
```

### Ключові можливості

✅ **Автоматичний вибір режиму** - Lambda (<15 хв) або ECS Fargate (15 хв - 3 год)
✅ **Візуальні ефекти** - Ken Burns zoom, transitions, CTA graphics
✅ **Синхронізація аудіо-відео** - точна прив'язка зображень до аудіо
✅ **Оптимізація вартості** - вибір найдешевшого методу рендерингу
✅ **Повна інтеграція** - частина Step Functions workflow

---

## Архітектура

### Повний workflow

```
Phase 1: Content Generation
  ├─ Theme Agent
  ├─ MEGA Narrative Generator
  └─ Результат: narrative_data, image_prompts, sfx_data, cta_segments

       ↓

Phase 2: Media Generation
  ├─ Generate Images (SD3.5)
  └─ Generate Audio (AWS Polly)

       ↓

Phase 3: Save & Estimate
  ├─ SaveFinalContent → DynamoDB
  │   Зберігає ВСІ дані контенту
  │
  └─ EstimateVideoDuration → Lambda
      Оцінює тривалість відео на основі:
      - Кількість сцен
      - Тривалість аудіо файлів
      - CTA segments

       ↓

Phase 4: Video Assembly (АВТОМАТИЧНО)

  ChooseRenderingMode (Choice State)
     │
     ├─ duration <= 15 min → AssembleVideoLambda
     │   • Lambda Function (15 min timeout)
     │   • Швидко (в межах хвилини)
     │   • Дешево ($0.002 за відео)
     │
     └─ duration > 15 min → AssembleVideoECS
         • ECS Fargate (до 3 годин)
         • Повільніше (залежить від довжини)
         • Дорожче ($0.40-$2.00 за відео)

       ↓

Result: S3 + DynamoDB updated
  - video_url: s3://...final-video-{content_id}.mp4
  - video_status: "completed"
```

---

## Гібридний підхід (Lambda + ECS)

### Чому два режими?

**Lambda Обмеження:**
- ❌ Timeout: 15 хвилин максимум
- ❌ Memory: 10GB максимум
- ❌ Storage: /tmp обмежений

**ECS Fargate Переваги:**
- ✅ Timeout: До 3 годин (налаштовується)
- ✅ Memory: До 30GB
- ✅ Storage: Необмежений через S3

### Автоматичний вибір

**VideoEditingTemplate (DynamoDB):**
```json
{
  "template_id": "video_template_universal_v2",
  "rendering_config": {
    "mode": "auto",
    "auto_selection": {
      "enabled": true,
      "rules": [
        {
          "condition": "duration_minutes <= 15",
          "mode": "lambda"
        },
        {
          "condition": "duration_minutes > 15",
          "mode": "ecs_fargate"
        }
      ]
    }
  }
}
```

**Step Functions Choice State:**
```json
{
  "Type": "Choice",
  "Choices": [
    {
      "Variable": "$.estimated_duration_minutes",
      "NumericLessThanEquals": 15,
      "Next": "AssembleVideoLambda"
    },
    {
      "Variable": "$.estimated_duration_minutes",
      "NumericGreaterThan": 15,
      "Next": "AssembleVideoECS"
    }
  ]
}
```

### Порівняння режимів

| Критерій | Lambda | ECS Fargate |
|----------|--------|-------------|
| **Max тривалість відео** | 15 хвилин | 3 години |
| **Час рендерингу** | 30-60 секунд | 5-20 хвилин |
| **Вартість (10 хв відео)** | $0.002 | $0.40 |
| **Cold start** | Немає | ~2 хвилини |
| **Масштабування** | Автоматичне | Manual/Auto |
| **Складність** | Низька | Середня |

**Рекомендації:**
- 🎬 **Короткі відео (3-10 хв):** Lambda - швидко і дешево
- 🎥 **Довгі відео (15-45 хв):** ECS - єдина опція

---

## Візуальні ефекти

### Ken Burns Effect

**Що це?** Плавний zoom/pan на зображеннях для створення динаміки.

**Налаштування:**
```json
{
  "ken_burns": {
    "enabled": true,
    "zoom_range": {
      "min": 1.0,
      "max": 1.2
    },
    "easing": "ease-in-out",
    "duration_per_scene": "auto"
  }
}
```

**Ефект:**
- Кожна сцена починається зі zoom=1.0
- Плавно збільшується до zoom=1.2
- Створює відчуття руху на статичних зображеннях

### Transitions

**Fade in/out між сценами:**
```json
{
  "transitions": {
    "enabled": true,
    "type": "fade",
    "duration_seconds": 0.5
  }
}
```

### CTA Graphics

**Call-To-Action оверлеї:**
```json
{
  "cta_graphics": {
    "enabled": true,
    "templates": {
      "subscribe": {
        "text": "Subscribe for more!",
        "position": "bottom-center",
        "duration": 3,
        "style": "modern"
      }
    }
  }
}
```

**Приклад CTA:**
```
╔═══════════════════════════════════╗
║                                   ║
║  [Основне зображення сцени]       ║
║                                   ║
║   ┌────────────────────────┐      ║
║   │  👍 SUBSCRIBE FOR MORE │      ║
║   └────────────────────────┘      ║
╚═══════════════════════════════════╝
```

---

## Вартість та оптимізація

### Breakdown витрат

#### Lambda Режим (<15 хв відео)

**Приклад:** Відео 10 хвилин (18 сцен)

```
Lambda вартість:
- Memory: 4096 MB
- Duration: ~45 секунд
- Cost: $0.002

S3 Upload:
- Size: ~200 MB
- Cost: $0.0001

TOTAL: ~$0.0021 за відео
```

#### ECS Fargate Режим (>15 хв відео)

**Приклад:** Відео 30 хвилин

```
ECS Fargate:
- vCPU: 2
- Memory: 8GB
- Task duration: ~15 хвилин
- Cost: ~$0.40

S3 Upload:
- Size: ~600 MB
- Cost: $0.0003

TOTAL: ~$0.40 за відео
```

### Оптимізація

✅ **Auto-selection** - вибирає найдешевший метод
✅ **Parallel processing** - MoviePy multiprocessing
✅ **S3 direct upload** - без проміжних копій
✅ **Cleanup** - видалення тимчасових файлів
✅ **Compression** - H.264 з оптимальним битрейтом

**Порівняння з ручним монтажем:**
- Ручний монтаж (Premiere Pro): ~30 хв/відео + $20.99/місяць підписка
- **Наша система**: $0.002-$0.40 за відео, повністю автоматично

---

## Робочий процес

### Детальний workflow

**1. SaveFinalContent**
```python
# Зберігає в DynamoDB:
{
  "content_id": "abysstales-1763...",
  "channel_id": "abysstales",
  "narrative_data": {
    "scenes": [
      {
        "scene_id": "scene_1",
        "text": "In the depths of the ocean...",
        "duration": 5.2
      }
    ]
  },
  "audio_urls": {
    "scene_1": "s3://.../scene-1.mp3"
  },
  "image_urls": {
    "scene_1": "s3://.../scene-1.png"
  },
  "sfx_data": { ... },
  "cta_segments": [ ... ]
}
```

**2. EstimateVideoDuration**
```python
# Lambda аналізує:
total_scenes = len(narrative_data["scenes"])
total_audio_duration = sum(audio_durations)
cta_duration = sum(cta_segments_durations)

estimated_duration = total_audio_duration + cta_duration
estimated_minutes = estimated_duration / 60

# Повертає:
{
  "estimated_duration_seconds": 542,
  "estimated_duration_minutes": 9.03,
  "rendering_mode_recommendation": "lambda"
}
```

**3. ChooseRenderingMode (Step Functions)**
```json
{
  "Type": "Choice",
  "Choices": [
    {
      "Variable": "$.estimated_duration_minutes",
      "NumericLessThanEquals": 15,
      "Next": "AssembleVideoLambda"
    }
  ],
  "Default": "AssembleVideoECS"
}
```

**4. AssembleVideoLambda (якщо <= 15 хв)**
```python
# 1. Завантажує DynamoDB record
content = dynamodb.get_item(content_id)

# 2. Завантажує media з S3
images = [download_from_s3(url) for url in image_urls]
audios = [download_from_s3(url) for url in audio_urls]

# 3. Створює відео через MoviePy
clips = []
for scene in scenes:
    img_clip = ImageClip(scene.image)
    img_clip = img_clip.resize(height=1080)
    img_clip = img_clip.set_duration(scene.audio_duration)

    # Ken Burns effect
    img_clip = img_clip.resize(lambda t: 1 + 0.2 * t/duration)

    # Додати аудіо
    img_clip = img_clip.set_audio(scene.audio)
    clips.append(img_clip)

# 4. Concatenate all clips
final_video = concatenate_videoclips(clips, method="compose")

# 5. Додати SFX/Music
final_video = final_video.set_audio(CompositeAudioClip([
    final_video.audio,
    background_music,
    sfx_clips
]))

# 6. Render
final_video.write_videofile(
    "/tmp/output.mp4",
    fps=30,
    codec="libx264",
    audio_codec="aac"
)

# 7. Upload до S3
s3.upload_file("/tmp/output.mp4", "videos/final-video-{id}.mp4")

# 8. Update DynamoDB
dynamodb.update_item(
    content_id,
    video_url="s3://...final-video-{id}.mp4",
    video_status="completed"
)
```

**5. AssembleVideoECS (якщо > 15 хв)**

Той самий процес, але:
- Більше пам'яті (8GB vs 4GB)
- Більше часу (до 3 годин)
- ECS Task замість Lambda

---

## Налаштування

### VideoEditingTemplate

**Розташування:** DynamoDB → `VideoEditingTemplates` таблиця

**Приклад повного темплейту:**
```json
{
  "template_id": "video_template_universal_v2",
  "template_name": "Universal Video Template v2",
  "description": "Auto-selection between Lambda and ECS",

  "rendering_config": {
    "mode": "auto",
    "auto_selection": {
      "enabled": true,
      "rules": [
        {"condition": "duration_minutes <= 15", "mode": "lambda"},
        {"condition": "duration_minutes > 15", "mode": "ecs_fargate"}
      ]
    },
    "lambda": {
      "function_name": "content-video-assembly",
      "timeout": 900,
      "memory": 4096
    },
    "ecs_fargate": {
      "cluster": "content-generation-cluster",
      "task_definition": "video-assembly-task",
      "cpu": "2048",
      "memory": "8192"
    }
  },

  "editing_params": {
    "resolution": {
      "width": 1920,
      "height": 1080
    },
    "fps": 30,
    "video_codec": "libx264",
    "audio_codec": "aac",
    "audio_bitrate": "192k",

    "visual_effects": {
      "ken_burns": {
        "enabled": true,
        "zoom_range": {"min": 1.0, "max": 1.2},
        "easing": "ease-in-out"
      },
      "transitions": {
        "enabled": true,
        "type": "fade",
        "duration_seconds": 0.5
      },
      "cta_graphics": {
        "enabled": true,
        "templates": {
          "subscribe": {
            "text": "Subscribe for more!",
            "position": "bottom-center",
            "duration": 3
          }
        }
      }
    },

    "audio_mixing": {
      "background_music": {
        "enabled": true,
        "volume": 0.15,
        "fade_in": 2,
        "fade_out": 3
      },
      "sfx": {
        "enabled": true,
        "volume": 0.4
      }
    }
  }
}
```

### Як змінити налаштування

**1. Через DynamoDB Console:**
```bash
1. Відкрити AWS Console → DynamoDB
2. Вибрати таблицю VideoEditingTemplates
3. Знайти template_id: "video_template_universal_v2"
4. Edit item
5. Змінити потрібні параметри
6. Save
```

**2. Через AWS CLI:**
```bash
aws dynamodb update-item \
  --table-name VideoEditingTemplates \
  --key '{"template_id": {"S": "video_template_universal_v2"}}' \
  --update-expression "SET editing_params.visual_effects.ken_burns.zoom_range.max = :val" \
  --expression-attribute-values '{":val": {"N": "1.3"}}' \
  --region eu-central-1
```

---

## Моніторинг

### CloudWatch Logs

**Lambda Logs:**
```
Log Group: /aws/lambda/content-video-assembly

Що логується:
- Media downloads (images, audio)
- MoviePy processing stages
- Rendering progress
- S3 upload results
- Errors (if any)
```

**ECS Logs:**
```
Log Group: /ecs/video-assembly-task

Що логується:
- Task start/stop
- Container startup
- Video assembly progress
- Memory/CPU usage
- Errors
```

### Метрики

**Відслідковувати:**
- ⏱️ **Rendering time** - час від старту до upload
- 💰 **Cost per video** - Lambda/ECS duration × pricing
- ✅ **Success rate** - % успішних рендерів
- 📈 **Video length distribution** - скільки Lambda vs ECS

### Dashboard

**Перегляд через WebUI:**
```
https://<your-domain>/content.html

→ Content Browser → View Details для конкретного відео

Показує:
- video_status: "completed" | "rendering" | "failed"
- video_url: S3 link
- rendering_mode: "lambda" | "ecs_fargate"
- video_duration: секунди
```

---

## Troubleshooting

### Video не створилося

**Симптом:** `video_status` = "failed" або відсутній

**Можливі причини:**

1. **Lambda timeout (15 хв)**
   - Відео занадто довге для Lambda
   - **Fix:** System має автоматично використати ECS, перевірте EstimateVideoDuration output

2. **Missing media files**
   - Images або audio не завантажилися в S3
   - **Fix:** Перевірте Phase 2 (image generation, TTS)

3. **MoviePy error**
   - Несумісні формати файлів
   - **Fix:** Перевірте CloudWatch Logs для details

**Перевірка:**
```bash
# 1. Check DynamoDB
aws dynamodb get-item \
  --table-name GeneratedContent \
  --key '{"content_id": {"S": "abysstales-1763..."}}' \
  --region eu-central-1

# 2. Перевірити чи є video_url
# 3. Перевірити video_status

# 4. Check CloudWatch Logs
aws logs tail /aws/lambda/content-video-assembly \
  --follow \
  --region eu-central-1
```

### Відео рендериться повільно

**Симптом:** Lambda виконується >5 хвилин

**Можливі причини:**
1. Великі зображення (>5MB кожне)
2. Багато сцен (>30)
3. Складні ефекти

**Оптимізація:**
```python
# У Lambda code, додати:
img_clip = img_clip.resize(height=1080)  # force resize
img_clip = img_clip.set_fps(30)          # cap FPS
```

### ECS Task failed

**Симптом:** Task status = "STOPPED", exit code != 0

**Debug:**
```bash
# 1. Check ECS Logs
aws logs tail /ecs/video-assembly-task --follow

# 2. Check Task stopped reason
aws ecs describe-tasks \
  --cluster content-generation-cluster \
  --tasks <task-arn>

# 3. Common issues:
#    - Out of memory (підвищити memory в task definition)
#    - Network timeout (перевірити S3 connectivity)
#    - Missing IAM permissions (додати s3:GetObject/PutObject)
```

---

## Корисні посилання

- [SD3.5 Image Generation](SD35-IMAGE-GENERATION.md) - Генерація зображень
- [Image Batching System](IMAGE-BATCHING-SYSTEM.md) - Паралельна обробка
- [MEGA Generation Guide](MEGA-GENERATION-GUIDE.md) - Повний workflow
- [SQS Retry System](SQS-RETRY-SYSTEM.md) - Retry механізм

---

**Статус системи:** ✅ Production Ready (2025-11-18)
**Підтримка:** Автоматичний моніторинг через CloudWatch
**Вартість:** $0.002 (Lambda) до $0.40 (ECS) за відео
