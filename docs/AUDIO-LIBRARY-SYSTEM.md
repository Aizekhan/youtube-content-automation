# Audio Library Management System
**Система керування SFX та фоновою музикою для MEGA-GENERATION**

*Створено: 2025-11-08*

---

## 📋 Огляд

Система дозволяє завантажувати, зберігати та керувати звуковими ефектами (SFX) та фоновою музикою, які використовуються в MEGA-GENERATION для автоматичного додавання аудіо до відеоконтенту.

## 🏗️ Архітектура

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│ Prompts Editor  │─────▶│ Lambda Function  │─────▶│ S3 Bucket       │
│ (UI)            │      │ audio-library-   │      │ youtube-        │
│                 │◀─────│ manager          │◀─────│ automation-     │
└─────────────────┘      └──────────────────┘      │ audio-files     │
                                │                   └─────────────────┘
                                ▼
                         ┌──────────────────┐
                         │ DynamoDB         │
                         │ SFXTemplates     │
                         │ (бібліотеки)     │
                         └──────────────────┘
```

## 📂 S3 Структура

### Bucket: `youtube-automation-audio-files`

```
youtube-automation-audio-files/
├── sfx/                    # Звукові ефекти
│   ├── ambient/            # Фонові звуки (ліс, дощ, вітер)
│   ├── action/             # Дії (вибух, удар, стрілянина)
│   ├── nature/             # Природа (птахи, грім, вода)
│   ├── dramatic/           # Драматичні ефекти
│   └── comedy/             # Комедійні звуки
│
└── music/                  # Фонова музика
    ├── epic/               # Епічна музика
    ├── calm/               # Спокійна музика
    ├── dramatic/           # Драматична музика
    ├── upbeat/             # Енергійна музика
    └── mysterious/         # Таємнича музика
```

### Формати файлів
- **Підтримувані**: MP3, WAV, OGG
- **Рекомендований**: MP3 (найкраще стиснення)
- **Naming**: Будь-яка назва (краще англійською без пробілів)

---

## ⚙️ Lambda Function

### Деталі
- **Назва**: `audio-library-manager`
- **Runtime**: Python 3.9
- **URL**: https://6kxbwzzvsoi23qxzlwauad2ttu0fzxrk.lambda-url.eu-central-1.on.aws/
- **Timeout**: 300 секунд
- **Memory**: 512 MB
- **Role**: ContentGeneratorLambdaRole

### API Endpoints

#### 1. Отримати Presigned URL для завантаження
```json
POST /
{
  "action": "get_upload_url",
  "file_type": "sfx",           // або "music"
  "category": "ambient",        // ambient, action, nature, etc.
  "filename": "rain_loop.mp3"
}

Response:
{
  "success": true,
  "upload_url": "https://s3...",
  "file_key": "sfx/ambient/rain_loop.mp3"
}
```

#### 2. Сканування S3 та оновлення бібліотек
```json
POST /
{
  "action": "scan_and_update",
  "template_id": "sfx_universal_v1"  // optional
}

Response:
{
  "success": true,
  "message": "Libraries updated successfully",
  "stats": {
    "sfx_files": 15,
    "sfx_categories": 3,
    "music_files": 8,
    "music_categories": 2,
    "total_files": 23
  },
  "sfx_library": {
    "ambient": ["rain.mp3", "forest.mp3"],
    "action": ["explosion.mp3"]
  },
  "music_library": {
    "epic": ["battle.mp3"]
  }
}
```

#### 3. Список файлів
```json
POST /
{
  "action": "list_files",
  "file_type": "sfx"  // optional, null = всі
}

Response:
{
  "success": true,
  "files": {
    "sfx": {
      "ambient": [
        {
          "filename": "rain.mp3",
          "size": 2456789,
          "last_modified": "2025-11-08T06:00:00Z"
        }
      ]
    }
  }
}
```

---

## 🎨 UI Інтерфейс

### Локація
https://n8n-creator.space/prompts-editor.html

**Шлях**: Prompts → SFX Templates → sfx_universal_v1 → Audio Library Management

### Компоненти

#### 1. Upload Section
- **File Type Selector**: Вибір між SFX та Music
- **Category Selector**: Динамічний список категорій (залежить від типу)
- **File Input**: Підтримує multiple files
- **Upload Button**: Запускає завантаження
- **Progress Bar**: Показує прогрес завантаження

#### 2. Library Tabs
- **SFX Library Tab**: Показує всі звукові ефекти по категоріях
- **Music Library Tab**: Показує всю фонову музику по категоріях

#### 3. Scan & Update Button
Сканує S3 bucket та оновлює бібліотеки в DynamoDB SFXTemplates

---

## 📖 Інструкція по використанню

### Крок 1: Відкрити SFX Template
1. Перейти на https://n8n-creator.space/prompts-editor.html
2. Обрати вкладку **SFX Templates**
3. Відкрити темплейт **Universal SFX + Music** (sfx_universal_v1)

### Крок 2: Завантажити аудіо файли
1. У секції **Audio Library Management**
2. Обрати **File Type**:
   - **Sound Effects (SFX)** - для звукових ефектів
   - **Background Music** - для фонової музики
3. Обрати **Category**:
   - Для SFX: ambient, action, nature, dramatic, comedy
   - Для Music: epic, calm, dramatic, upbeat, mysterious
4. Натиснути на поле **Choose files** та обрати файли (можна кілька)
5. Натиснути **Upload Files**
6. Дочекатись завершення (progress bar покаже прогрес)

### Крок 3: Оновити бібліотеку
1. Після завантаження натиснути **Scan S3 & Update Library**
2. Lambda просканує S3 та оновить каталог
3. Бібліотеки відобразяться у вкладках **SFX Library** та **Music Library**

### Крок 4: Перевірити результат
1. Переключитись між вкладками **SFX Library** та **Music Library**
2. Перевірити що файли з'явились у відповідних категоріях
3. Файли тепер доступні для MEGA-GENERATION

---

## 🔧 Технічні деталі

### DynamoDB Schema (SFXTemplates)

```json
{
  "template_id": "sfx_universal_v1",
  "template_name": "Universal SFX + Music",
  "ai_config": {
    "model": "gpt-4o-mini",
    "temperature": 0.7,
    "max_tokens": 3000,
    "sections": {
      "role_definition": "You are SFX Agent...",
      "core_rules": [...]
    }
  },
  "sfx_library": {
    "ambient": ["rain.mp3", "forest.mp3"],
    "action": ["explosion.mp3"],
    "nature": ["thunder.mp3"]
  },
  "music_library": {
    "epic": ["battle.mp3"],
    "calm": ["peaceful_piano.mp3"]
  },
  "timing_rules": {
    "max_per_scene": 3,
    "words_per_minute": 150
  },
  "library_stats": {
    "sfx_files": 3,
    "music_files": 2,
    "total_files": 5,
    "sfx_categories": 3,
    "music_categories": 2
  },
  "last_library_scan": "2025-11-08T06:00:00.000Z"
}
```

### Lambda Code Location
```
E:/youtube-content-automation/aws/lambda/audio-library-manager/
├── lambda_function.py     # Main handler
└── function.zip          # Deployment package
```

### UI Code Location
```
E:/youtube-content-automation/prompts-editor.html
├── Lines 1534-1604       # HTML UI (Audio Library Management section)
├── Lines 2958-3116       # JavaScript functions
```

---

## 🔄 Інтеграція з MEGA-GENERATION

### Як MEGA використовує бібліотеки

1. **Content-Narrative Lambda** запускається для генерації контенту
2. Завантажує **SFX Template** з DynamoDB
3. Читає `sfx_library` та `music_library` з темплейту
4. Передає бібліотеки в **mega_prompt_builder.py**
5. MEGA-GENERATION генерує JSON з посиланнями на файли:

```json
{
  "sfx_data": {
    "scene_1": [
      {
        "file": "sfx/ambient/rain.mp3",
        "timestamp": 0,
        "duration": 5,
        "volume": 0.3
      }
    ]
  },
  "music_data": {
    "background_track": "music/epic/battle.mp3",
    "volume": 0.2,
    "fade_in": 2,
    "fade_out": 3
  }
}
```

6. **Content-Save-Result Lambda** використовує ці дані для фінальної збірки відео

---

## 📊 Статистика та моніторинг

### Перевірка бібліотек через CLI

```bash
# Показати всі файли в S3
aws s3 ls s3://youtube-automation-audio-files/ --recursive --region eu-central-1

# Перевірити SFX Template
aws dynamodb get-item \
  --table-name SFXTemplates \
  --key '{"template_id": {"S": "sfx_universal_v1"}}' \
  --region eu-central-1

# Викликати Lambda для сканування
aws lambda invoke \
  --function-name audio-library-manager \
  --payload '{"action":"scan_and_update"}' \
  --region eu-central-1 \
  response.json
```

### CloudWatch Logs
```
Log Group: /aws/lambda/audio-library-manager
```

---

## ❗ Важливі зауваження

### Обмеження
- **Max file size**: 100 MB (Lambda timeout 300s)
- **Supported formats**: MP3, WAV, OGG
- **Presigned URL validity**: 10 хвилин
- **Concurrent uploads**: Необмежено (але краще по черзі)

### Best Practices
1. ✅ Використовуй короткі назви файлів без пробілів
2. ✅ Завантажуй файли невеликими батчами (5-10 файлів)
3. ✅ Запускай **Scan S3** після кожного завантаження
4. ✅ Використовуй MP3 для економії місця
5. ✅ Організовуй файли по категоріях логічно

### Troubleshooting

**Проблема**: Файли не з'являються після завантаження
- **Рішення**: Натисни **Scan S3 & Update Library**

**Проблема**: Upload fails з помилкою "Failed to get upload URL"
- **Рішення**: Перевір Lambda URL в prompts-editor.html:2956

**Проблема**: Files не відображаються в MEGA-GENERATION
- **Рішення**: Перевір що template_id правильний і бібліотеки оновлені

**Проблема**: Permission denied при завантаженні
- **Рішення**: Перевір IAM роль ContentGeneratorLambdaRole має доступ до S3

---

## 🔐 Безпека

### IAM Permissions Required
Lambda потребує:
- `s3:GetObject` - читання файлів
- `s3:PutObject` - завантаження файлів
- `s3:ListBucket` - сканування bucket
- `dynamodb:GetItem` - читання темплейтів
- `dynamodb:UpdateItem` - оновлення бібліотек

### CORS Settings
```json
{
  "AllowOrigins": ["*"],
  "AllowMethods": ["*"],
  "AllowHeaders": ["*"]
}
```

**Note**: У production краще обмежити AllowOrigins до `https://n8n-creator.space`

---

## 📝 Changelog

### 2025-11-08 - Initial Release
- ✅ Створено Lambda function `audio-library-manager`
- ✅ Створено S3 структуру для SFX та Music
- ✅ Інтегровано UI в prompts-editor.html
- ✅ Додано автоматичне сканування та оновлення бібліотек
- ✅ Підтримка множинного завантаження файлів
- ✅ Progress tracking для uploads
- ✅ Роздільні вкладки для SFX та Music

---

## 🔗 Пов'язані документи

- [MEGA-GENERATION-GUIDE.md](./docs/MEGA-GENERATION-GUIDE.md) - Повний гайд по MEGA-GENERATION
- [QUICK-START-MEGA.md](./docs/QUICK-START-MEGA.md) - Швидкий старт
- [S3-STORAGE-STRUCTURE.md](./S3-STORAGE-STRUCTURE.md) - Структура S3 storage
- [TEMPLATE-SYSTEM-STRUCTURE.md](./TEMPLATE-SYSTEM-STRUCTURE.md) - Система темплейтів

---

## 💡 Приклади використання

### Приклад 1: Завантажити ambient звуки
```
1. File Type: Sound Effects (SFX)
2. Category: ambient
3. Files: rain.mp3, forest.mp3, wind.mp3
4. Upload → Scan S3 & Update
```

### Приклад 2: Додати епічну музику
```
1. File Type: Background Music
2. Category: epic
3. Files: battle_theme.mp3, victory_march.mp3
4. Upload → Scan S3 & Update
```

### Приклад 3: Перевірити що завантажено
```javascript
// JavaScript console в браузері
const response = await fetch('https://6kxbwzzvsoi23qxzlwauad2ttu0fzxrk.lambda-url.eu-central-1.on.aws/', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ action: 'list_files' })
});
const data = await response.json();
console.log(data.files);
```

---

**Автор**: Claude Code
**Останнє оновлення**: 2025-11-08
**Версія**: 1.0
