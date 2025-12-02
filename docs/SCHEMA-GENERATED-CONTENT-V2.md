# GeneratedContent Table Schema v2.0

## 📊 Primary Keys
- **Partition Key**: `channel_id` (String) - ID YouTube каналу
- **Sort Key**: `created_at` (String) - ISO 8601 timestamp

## 📝 Core Fields (Existing)

### Metadata
| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `type` | String | Тип контенту | `"narrative_generation"`, `"theme_generation"` |
| `channel_name` | String | Назва каналу | `"Horror Stories UA"` |
| `genre` | String | Жанр контенту | `"Horror"`, `"Mystery"` |
| `model` | String | AI модель | `"gpt-4o"` |
| `api_version` | String | Версія config merger | `"config_merger_v2"` |
| `cost_usd` | Number | Вартість генерації | `0.0234` |

### Story Content
| Field | Type | Description |
|-------|------|-------------|
| `story_title` | String | Назва історії |
| `narrative_text` | String | Повний текст наративу |
| `character_count` | Number | Кількість символів |
| `scene_count` | Number | Кількість сцен |
| `generated_titles` | List<String> | Згенеровані теми (для theme_generation) |

### Scenes Structure
```json
"scenes": [
  {
    "id": 1,
    "paragraph_text": "Текст сцени...",
    "image_prompt": "Prompt для генерації зображення"
  }
]
```

### Audio Files (Existing)
```json
"audio_files": [
  {
    "scene_id": 1,
    "s3_url": "s3://bucket/path/scene_1.mp3",
    "duration_ms": 5420,
    "voice_id": "Matthew",
    "created_at": "2025-11-05T12:00:00Z"
  }
]
```

## 🆕 NEW FIELDS - Production Pipeline

### 1. Thumbnail (Обложка)
```json
{
  "thumbnail": {
    "image_url": "s3://youtube-content-automation/thumbnails/UCxxx/2025-11-05_thumbnail.png",
    "prompt": "Horror story thumbnail with dark atmosphere...",
    "generated_at": "2025-11-05T12:05:00Z",
    "service": "midjourney|dall-e-3|stable-diffusion",
    "status": "completed|pending|failed",
    "width": 1280,
    "height": 720
  }
}
```

### 2. Call to Action (Заклик до дії)
```json
{
  "call_to_action": {
    "text": "Підписуйтесь на канал і натискайте дзвіночок!",
    "audio_url": "s3://youtube-content-automation/cta/UCxxx/cta_2025-11-05.mp3",
    "duration_ms": 3200,
    "voice_id": "Matthew",
    "placement": "end|start|both",
    "generated_at": "2025-11-05T12:10:00Z",
    "status": "completed|pending|failed"
  }
}
```

### 3. Background Music
```json
{
  "background_music": {
    "track_url": "s3://youtube-content-automation/music/horror_ambient_01.mp3",
    "track_name": "Dark Ambient Horror",
    "duration_ms": 180000,
    "volume_level": 0.3,
    "source": "epidemic-sound|artlist|royalty-free",
    "license": "royalty-free",
    "fade_in_ms": 2000,
    "fade_out_ms": 3000,
    "status": "completed|pending|failed"
  }
}
```

### 4. Sound Effects
```json
{
  "sound_effects": [
    {
      "effect_id": "sfx_001",
      "effect_url": "s3://youtube-content-automation/sfx/door_creak.mp3",
      "effect_name": "Door Creak",
      "scene_id": 3,
      "timestamp_ms": 5200,
      "duration_ms": 1500,
      "volume_level": 0.5,
      "source": "freesound|epidemic-sound"
    }
  ]
}
```

### 5. Scene Images (Візуали)
```json
{
  "scene_images": [
    {
      "scene_id": 1,
      "image_url": "s3://youtube-content-automation/images/UCxxx/scene_1.png",
      "prompt": "Dark haunted house at night...",
      "service": "midjourney|dall-e-3",
      "generated_at": "2025-11-05T12:15:00Z",
      "width": 1920,
      "height": 1080,
      "status": "completed|pending|failed",
      "cost_usd": 0.04
    }
  ]
}
```

### 6. Final Video
```json
{
  "final_video": {
    "video_url": "s3://youtube-content-automation/videos/UCxxx/2025-11-05_final.mp4",
    "video_title": "Моторошна історія про прокляте місто | Хоррор Українською",
    "video_description": "Сьогодні розповім вам моторошну історію...\n\n🔔 Підписуйтесь на канал!",
    "video_tags": ["horror", "story", "ukrainian", "scary"],
    "duration_ms": 183400,
    "resolution": "1920x1080",
    "fps": 30,
    "file_size_mb": 245,
    "rendered_at": "2025-11-05T12:30:00Z",
    "rendering_service": "ffmpeg|remotion|cloudflare-stream",
    "status": "completed|rendering|pending|failed"
  }
}
```

### 7. YouTube Publishing
```json
{
  "youtube_publishing": {
    "video_id": "dQw4w9WgXcQ",
    "published_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
    "published_at": "2025-11-05T14:00:00Z",
    "visibility": "public|private|unlisted",
    "scheduled_publish_time": "2025-11-06T18:00:00Z",
    "upload_status": "uploaded|scheduled|draft|failed",
    "views": 0,
    "likes": 0,
    "comments": 0,
    "last_synced": "2025-11-05T15:00:00Z"
  }
}
```

## 🔄 Production Status Tracking

### Pipeline Progress
```json
{
  "pipeline_status": {
    "overall_status": "in_progress|completed|failed",
    "progress_percentage": 75,
    "stages": {
      "1_overview": {"status": "completed", "updated_at": "2025-11-05T11:50:00Z"},
      "2_thumbnail": {"status": "completed", "updated_at": "2025-11-05T12:05:00Z"},
      "3_story": {"status": "completed", "updated_at": "2025-11-05T12:00:00Z"},
      "4_voice": {"status": "completed", "updated_at": "2025-11-05T12:10:00Z"},
      "5_cta": {"status": "completed", "updated_at": "2025-11-05T12:12:00Z"},
      "6_audio": {"status": "in_progress", "updated_at": "2025-11-05T12:15:00Z"},
      "7_visuals": {"status": "pending", "updated_at": null},
      "8_video": {"status": "pending", "updated_at": null}
    },
    "last_updated": "2025-11-05T12:15:00Z"
  }
}
```

## 📦 Complete Example Record

```json
{
  "channel_id": "UCxxxxxxxxxxxxx",
  "created_at": "2025-11-05T11:50:23Z",
  "type": "narrative_generation",
  "channel_name": "Horror Stories UA",
  "genre": "Horror",
  "model": "gpt-4o",
  "api_version": "config_merger_v2",
  "cost_usd": 0.0234,

  "story_title": "Прокляте місто Прип'ять",
  "narrative_text": "...",
  "character_count": 8543,
  "scene_count": 12,

  "scenes": [...],
  "audio_files": [...],

  "thumbnail": {...},
  "call_to_action": {...},
  "background_music": {...},
  "sound_effects": [...],
  "scene_images": [...],
  "final_video": {...},
  "youtube_publishing": {...},
  "pipeline_status": {...}
}
```

## 🔧 Migration Notes

### Existing Records
- Всі існуючі записи залишаться без змін
- Нові поля будуть `null` або відсутні для старих записів
- UI має gracefully обробляти відсутність нових полів

### Backward Compatibility
- Lambda функції мають перевіряти наявність полів перед використанням
- Default values для відсутніх полів:
  - `thumbnail.status = "pending"`
  - `pipeline_status.overall_status = "partial"` (якщо є narrative але немає решти)

## 📊 DynamoDB Considerations

### Cost Impact
- Додаткові поля збільшать розмір записів
- Estimated size increase: ~5-10 KB per record
- Рекомендується включити TTL для старих записів (>90 днів)

### Queries
- Жодних змін в індексах не потрібно
- Всі нові поля - звичайні атрибути
- Можна додати GSI на `pipeline_status.overall_status` для фільтрації

---

**Version**: 2.0
**Last Updated**: 2025-11-05
**Status**: Draft - Ready for Implementation
