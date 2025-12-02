# CTA (Call to Action) Architecture & Implementation

**Date:** 2025-11-26
**Status:** 🔶 Частково реалізовано
**Критичне:** ❌ CTA НЕ вставляється у відео (логіка відсутня)

---

## 📋 Поточний стан системи

### ✅ Що вже працює:

1. **CTA Template** - є у DynamoDB
   - Table: `CTATemplates`
   - Template ID: `cta_template_1762366857242_3zx29p`
   - Template Name: "Universal Subscribe CTA"
   - Status: ✅ Активовано (2025-11-26)

2. **CTA Configuration** - визначає де вставляти CTA:
   ```json
   {
     "enabled": true,
     "placements": [
       {
         "type": "subscribe",
         "relative_to": "after_scene",
         "scene_number": 5
       },
       {
         "type": "like",
         "relative_to": "before_scene",
         "scene_number": 12
       }
     ]
   }
   ```

3. **CTA AI Generation** - MEGA v3.0 Lambda генерує CTA:
   - Location: `content-narrative/lambda_function.py`
   - Повертає: `cta_data.cta_segments[]`
   - Структура:
     ```json
     {
       "cta_segments": [
         {
           "position": "35%",
           "type": "subscribe",
           "cta_text": "<speak>...</speak>",
           "style_note": "Mysterious and inviting tone"
         }
       ]
     }
     ```

4. **CTA Data Storage** - зберігається у DynamoDB:
   - Table: `GeneratedContent`
   - Field: `cta_data.cta_segments`
   - Приклад з бази: ✅ Структура є

5. **CTA Display** - показується на фронтенді:
   - File: `content.html`
   - Function: `populateCTA(item)`
   - Показує: тип, позицію, текст, стиль

### ❌ Що НЕ працює:

1. **CTA INSERTION INTO VIDEO** - **КРИТИЧНО!**
   - File: `content-video-assembly/lambda_function.py`
   - Current: Лише рахує тривалість CTA для estimate (line 229-235)
   - Missing: **НЕМАЄ коду для вставки CTA у відео!**

---

## 🎯 Логіка генерації CTA

### Крок 1: AI генерація (MEGA Lambda)

**Location:** `content-narrative/lambda_function.py:419-422`

```python
# CTA data for SaveFinalContent
'cta_data': {
    'cta_segments': cta_segments  # Згенеровано OpenAI
},
```

**OpenAI отримує:**
- CTA template з `CTATemplates` table
- Placements конфігурацію
- Story context (тема, сцени, стиль)

**OpenAI повертає:**
```json
{
  "cta_segments": [
    {
      "position": "35%",           // Де у відео (% від загальної тривалості)
      "type": "subscribe",          // subscribe/like/comment
      "cta_text": "<speak>...</speak>",  // SSML текст
      "style_note": "..."           // Опис стилю
    }
  ]
}
```

### Крок 2: Збереження (content-save-result Lambda)

**Location:** Step Functions → SaveFinalContent state

```json
{
  "cta_data.$": "$.narrativeResult.Payload.cta_data"
}
```

Зберігається у DynamoDB `GeneratedContent` table.

### Крок 3: TTS генерація для CTA ❌ НЕ РЕАЛІЗОВАНО

**Відсутня логіка:**
- Немає окремого CTA TTS Lambda
- Немає коду для генерації CTA аудіо
- CTA текст (SSML) є, але аудіо не генерується

**Що потрібно:**
```python
# Псевдокод
for cta in cta_segments:
    cta_audio = generate_polly_audio(
        text=cta['cta_text'],
        voice=channel_config.tts_voice,
        output_format='mp3'
    )
    cta['cta_audio_segment'] = {
        's3_url': upload_to_s3(cta_audio),
        'duration_ms': get_duration(cta_audio),
        'target_duration_seconds': 10
    }
```

### Крок 4: Video Assembly ❌ НЕ РЕАЛІЗОВАНО

**Current code:** `content-video-assembly/lambda_function.py:374-473`

**Що є зараз:**
```python
# Line 398-458: Обробка сцен
for i, (audio, image) in enumerate(zip(assets['audio'], assets['images'])):
    # Створює scene_1.mp4, scene_2.mp4, ...
    scene_videos.append(scene_video)

# Line 460-466: Конкатенація
# Просто з'єднує всі сцени підряд
concat_list.txt:
  file 'scene_1.mp4'
  file 'scene_2.mp4'
  file 'scene_3.mp4'
  ...
```

**Що ПОТРІБНО:**
```python
# Псевдокод - ВСТАВКА CTA
scene_videos = []

for i, (audio, image) in enumerate(scenes):
    # Створюємо сцену
    scene_videos.append(create_scene(audio, image))

    # ПЕРЕВІРЯЄМО чи є CTA ПІСЛЯ цієї сцени
    for cta in cta_segments:
        if cta['placement']['relative_to'] == 'after_scene' and \
           cta['placement']['scene_number'] == i + 1:
            # ВСТАВЛЯЄМО CTA
            cta_video = create_cta_video(
                audio=cta['cta_audio_segment'],
                visual=cta_visual_template  # Візуал для CTA
            )
            scene_videos.append(cta_video)

# Конкатенація
concat_list.txt:
  file 'scene_1.mp4'
  file 'scene_2.mp4'
  file 'scene_3.mp4'
  file 'scene_4.mp4'
  file 'scene_5.mp4'
  file 'cta_subscribe.mp4'  ← CTA вставлено після сцени 5!
  file 'scene_6.mp4'
  ...
```

---

## 🔧 Як працює placement логіка

### Приклад з CTA Template:

```json
{
  "placements": [
    {
      "type": "subscribe",
      "relative_to": "after_scene",
      "scene_number": 5
    },
    {
      "type": "like",
      "relative_to": "before_scene",
      "scene_number": 12
    }
  ]
}
```

### Результат у відео:

```
Відео таймлайн:
│
├─ Scene 1 (0:00 - 0:15)
├─ Scene 2 (0:15 - 0:30)
├─ Scene 3 (0:30 - 0:45)
├─ Scene 4 (0:45 - 1:00)
├─ Scene 5 (1:00 - 1:15)
│
├─ 🎯 CTA Subscribe (1:15 - 1:25)  ← after_scene 5
│
├─ Scene 6 (1:25 - 1:40)
├─ Scene 7 (1:40 - 1:55)
...
├─ Scene 11 (3:30 - 3:45)
│
├─ 🎯 CTA Like (3:45 - 3:55)  ← before_scene 12
│
├─ Scene 12 (3:55 - 4:10)
...
```

### Типи placement:

1. **after_scene** - CTA після сцени
   ```json
   {"relative_to": "after_scene", "scene_number": 5}
   ```
   → Вставити CTA ПІСЛЯ сцени 5

2. **before_scene** - CTA перед сценою
   ```json
   {"relative_to": "before_scene", "scene_number": 12}
   ```
   → Вставити CTA ПЕРЕД сценою 12

3. **position_based** - CTA за % часу (альтернатива)
   ```json
   {"position": "35%"}
   ```
   → Вставити CTA на 35% відео

---

## 📊 Поточна структура даних

### У DynamoDB GeneratedContent:

```json
{
  "channel_id": "UCaxPNkUMQKqepAp0JbpVrrw",
  "created_at": "2025-11-26T01:00:42Z",
  "type": "mega_generation",

  "cta_data": {
    "cta_segments": [
      {
        "position": "35%",
        "type": "subscribe",
        "cta_text": "<speak><prosody rate=\"slow\">Before the whispers fade, make sure to uncover more tales. Join our journey...</prosody></speak>",
        "style_note": "Mysterious and inviting tone"
      }
    ]
  },

  "narrative_data": {
    "scenes": [/* 5 scenes */]
  },

  "audio_files": [/* 5 audio files */],
  "scene_images": [/* 5 images */]

  // ❌ НЕМАЄ: cta_audio_files, cta_placements_resolved
}
```

### Що потрібно додати:

```json
{
  "cta_data": {
    "cta_segments": [
      {
        "position": "35%",
        "type": "subscribe",
        "cta_text": "<speak>...</speak>",
        "style_note": "...",

        // ✨ ДОДАТИ:
        "cta_audio_segment": {
          "s3_url": "s3://bucket/cta_subscribe.mp3",
          "duration_ms": 10000,
          "voice_id": "Matthew",
          "target_duration_seconds": 10
        },

        "placement": {
          "relative_to": "after_scene",
          "scene_number": 5,
          "insertion_index": 5  // Вставити після scene_5.mp4
        },

        "visual": {
          "type": "animated_text",
          "background_color": "#1a1a1a",
          "text_animation": "fade_in"
        }
      }
    ]
  }
}
```

---

## 🚀 Що треба реалізувати

### Priority 1: CTA Audio Generation

**Створити:** `content-cta-audio` Lambda (або додати до content-audio-tts)

```python
def generate_cta_audio(cta_segments, channel_config):
    """Generate audio for all CTA segments"""
    for cta in cta_segments:
        # Generate Polly audio from SSML
        audio = polly.synthesize_speech(
            Text=cta['cta_text'],
            VoiceId=channel_config['tts_voice_id'],
            OutputFormat='mp3',
            TextType='ssml'
        )

        # Upload to S3
        s3_url = upload_audio_to_s3(audio, cta['type'])

        # Add to CTA data
        cta['cta_audio_segment'] = {
            's3_url': s3_url,
            'duration_ms': get_duration(audio),
            'target_duration_seconds': 10
        }

    return cta_segments
```

### Priority 2: CTA Video Assembly

**Модифікувати:** `content-video-assembly/lambda_function.py`

```python
def assemble_video_with_cta(content, assets, template, work_dir):
    """Assemble video with CTA insertions"""

    scene_videos = []
    cta_segments = content.get('cta_data', {}).get('cta_segments', [])

    for i, (audio, image) in enumerate(scenes):
        # Створюємо сцену
        scene_video = create_scene(audio, image, work_dir)
        scene_videos.append(scene_video)

        # Перевіряємо CTA після цієї сцени
        for cta in cta_segments:
            placement = cta.get('placement', {})

            if (placement.get('relative_to') == 'after_scene' and
                placement.get('scene_number') == i + 1):

                # Створюємо CTA відео
                cta_video = create_cta_segment(
                    cta_audio=cta['cta_audio_segment'],
                    cta_visual=cta.get('visual', {}),
                    work_dir=work_dir
                )
                scene_videos.append(cta_video)
                print(f"✅ Inserted CTA '{cta['type']}' after scene {i+1}")

    # Конкатенація
    return concatenate_videos(scene_videos, work_dir)

def create_cta_segment(cta_audio, cta_visual, work_dir):
    """Create CTA video segment"""
    # Download CTA audio
    audio_path = download_s3_file(cta_audio['s3_url'], work_dir)

    # Create visual (text overlay, animation, etc.)
    visual_type = cta_visual.get('type', 'static_text')

    if visual_type == 'animated_text':
        # FFmpeg with drawtext filter + fade animation
        cta_video = create_animated_text_cta(audio_path, cta_visual, work_dir)
    else:
        # Simple solid color background with text
        cta_video = create_simple_cta(audio_path, cta_visual, work_dir)

    return cta_video
```

### Priority 3: Step Functions Integration

**Модифікувати:** `step-function-fixed-cta.json`

Додати CTA audio generation перед SaveFinalContent:

```json
{
  "GenerateCTAAudio": {
    "Type": "Task",
    "Resource": "arn:aws:states:::lambda:invoke",
    "Parameters": {
      "FunctionName": "content-cta-audio",
      "Payload": {
        "channel_id.$": "$.channel_id",
        "cta_segments.$": "$.narrativeResult.Payload.cta_data.cta_segments",
        "voice_config.$": "$.ttsConfig"
      }
    },
    "ResultPath": "$.ctaAudioResult",
    "Next": "SaveFinalContent"
  }
}
```

---

## 📝 Summary

### Що працює зараз:

1. ✅ CTA Template активовано
2. ✅ CTA placements конфігурація є
3. ✅ AI генерує CTA текст (SSML)
4. ✅ CTA зберігається у DynamoDB
5. ✅ Фронтенд показує CTA

### Що НЕ працює (критично):

1. ❌ **CTA audio НЕ генерується** (немає Lambda)
2. ❌ **CTA НЕ вставляється у відео** (немає логіки у video-assembly)
3. ❌ **CTA placements НЕ резолвляться** (не перетворюються у insertion_index)

### Наступні кроки для повної реалізації:

1. **Створити CTA Audio Lambda** (або розширити content-audio-tts)
2. **Додати CTA insertion логіку** у content-video-assembly
3. **Оновити Step Functions** для включення CTA audio generation
4. **Тестувати повний pipeline** з CTA

---

**Висновок:** CTA система є "наполовину готовою" - текст генерується, але аудіо та відео вставка відсутні.

