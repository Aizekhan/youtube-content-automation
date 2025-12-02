# Dashboard Monitoring System

**Оновлено:** 2025-11-06
**Статус:** ✅ Повністю функціональна
**URL:** https://n8n-creator.space/dashboard.html

---

## Огляд

Dashboard Monitoring - це повнофункціональна система моніторингу та відладки для YouTube Content Automation. Система надає real-time візуалізацію виконання Step Functions, детальний перегляд кожного кроку генерації контенту, та інструменти для debugging.

---

## Основні Можливості

### 1. 📊 Real-time Monitoring Tab

**Що показує:**
- Running executions (поточні виконання)
- Succeeded today (успішні за сьогодні)
- Failed today (невдалі за сьогодні)
- Average duration (середня тривалість)

**Функціональність:**
- Auto-refresh кожні 30 секунд
- Ручне оновлення кнопкою "Refresh"
- Статистика в реальному часі

### 2. 🔄 Workflow Visualization

**7-крокова візуалізація:**

```
1. GetActiveChannels
   └─ Output: channel_id, config_id, genre

2. QueryTitles
   └─ Output: video_titles[], view_counts[]

3. ThemeAgent
   └─ Loads: ChannelConfigs + Theme Template
   └─ Merge: Config + Template → OpenAI Request
   └─ Output: generated_titles[] (4 теми)

4. SelectTopic
   └─ Output: selected_topic (random.choice)

5. NarrativeArchitect
   └─ Loads: ChannelConfigs + Narrative Template
   └─ Merge: Config + Template + Topic → OpenAI Request
   └─ Output: narrative_text, scene_ssml[]

6. GenerateAudio
   └─ Uses: Channel TTS settings + SSML
   └─ Output: audio_urls[], total_duration_sec

7. SaveResult
   └─ Output: Saved to GeneratedContent table
```

**Інтерактивні функції:**
- ✅ Кожен блок клікабельний
- ✅ Показує детальну Data Flow інформацію
- ✅ Візуальні статуси (✓ succeeded, ✗ failed)
- ✅ Hover ефекти для кращої UX

### 3. 📜 Step Functions Executions

**Список виконань:**
- Показує останні 20 виконань
- Кольорове кодування статусів:
  - 🟢 Зелений = SUCCEEDED
  - 🔴 Червоний = FAILED
  - 🔵 Синій = RUNNING
- Інформація про кожне виконання:
  - Назва execution
  - Timestamp (час запуску)
  - Тривалість виконання
  - Статус

**Як використовувати:**
1. Клікніть на будь-яке виконання в списку
2. Відкриється модальне вікно з інформацією
3. Система завантажить детальну історію кроків
4. Закрийте модалку
5. Прокрутіть до workflow візуалізації
6. Клікайте на блоки щоб побачити Input/Output JSON!

### 4. 🔍 Step Details Modal

**Що показує для кожного кроку:**

#### Data Flow Section (завжди):
- **📥 Завантажує з DynamoDB:**
  - Які таблиці читає
  - Які поля використовує

- **🔄 Merge & Processing:**
  - Як мерджиться config + template
  - Як формується OpenAI request
  - Логіка обробки

- **📤 Output:**
  - Що повертає Lambda
  - Які дані передаються далі

#### Execution Data (якщо вибране execution):
- **Status:** SUCCEEDED / FAILED / RUNNING
- **Start Time:** Час початку
- **End Time:** Час завершення
- **Input JSON:** Повний Input для Lambda
- **Output JSON:** Повний Output з Lambda
- **Error:** Деталі помилки (якщо є)

### 5. 🐛 Debug Test Runner

**Lambda:** `debug-test-runner`
**URL:** https://huooyve5uullyeh7safuexpawm0jidlu.lambda-url.eu-central-1.on.aws/

**Що робить:**
- Послідовно викликає всі Lambda функції
- Збирає детальну інформацію про кожен крок
- Повертає повний звіт про виконання

**Як використовувати:**
1. Перейдіть на вкладку "Debug"
2. Оберіть канал зі списку
3. (Опціонально) Вкажіть тему
4. Натисніть "Start Test"
5. Чекайте результати (~2-3 хвилини)
6. Переглядайте деталі кожного кроку

**Output:**
```json
{
  "success": true,
  "steps": [
    {
      "step_number": 1,
      "step_name": "get-channel-config",
      "status": "completed",
      "duration_ms": 234,
      "input": {...},
      "output": {...}
    }
  ],
  "summary": {
    "total_duration_sec": 156.2,
    "total_cost_usd": 0.025,
    "scene_count": 18
  }
}
```

---

## Технічна Архітектура

### Frontend Files

**dashboard.html** (79KB)
- Bootstrap 5 для UI
- Vanilla JavaScript (no frameworks)
- Real-time API calls
- Workflow visualization
- Modal windows для details

**css/workflow.css** (5.1KB)
- Workflow node styles
- Execution item styles
- Merge node styles (не використовуються в UI, тільки в metadata)
- Animations та transitions

### Backend Lambda

**dashboard-monitoring**
```python
# Endpoints:
GET /monitoring/executions
  → List Step Functions executions

GET /monitoring/logs?limit=50
  → CloudWatch logs

GET /monitoring/execution-details?executionArn=...
  → Detailed step-by-step history
```

**debug-test-runner**
```python
# POST with body:
{
  "channel_id": "UCRmO5HB89...",
  "topic": "Optional topic"
}

# Returns:
{
  "success": true,
  "steps": [...],
  "summary": {...}
}
```

### IAM Permissions

**ContentGeneratorLambdaRole → DashboardAccessPolicy:**
```json
{
  "Action": [
    "states:ListStateMachines",
    "states:ListExecutions",
    "states:DescribeExecution",
    "states:DescribeStateMachine",
    "states:GetExecutionHistory"  ← ДОДАНО
  ],
  "Resource": "*"
}
```

### API Gateway

**REST API:** e2c5y2h1qj
**Stage:** prod
**Base URL:** https://e2c5y2h1qj.execute-api.eu-central-1.amazonaws.com/prod

**Resources:**
- /monitoring
  - /executions (GET)
  - /logs (GET)
  - /execution-details (GET)

**CORS:** Enabled with OPTIONS methods

---

## Workflow Data Flow Metadata

### GetActiveChannels
```
Завантажує: ChannelConfigs таблиця
Merge: None
Output: channel_id, config_id, channel_name, genre
```

### QueryTitles
```
Завантажує: Nothing
Merge: YouTube API call
Output: video_titles[], view_counts[]
```

### ThemeAgent
```
Завантажує:
  - ChannelConfigs (genre, tone, keywords, target_audience)
  - AIPromptConfigs (Theme Template via selected_theme_template)

Merge:
  - Channel Config + Theme Template → OpenAI system_prompt + user_message
  - Формується JSON з channel info + titles для GPT

Output: generated_titles[] (4 теми), selected_topic
```

### SelectTopic
```
Завантажує: Nothing
Merge: random.choice() з generated_titles
Output: selected_topic, all_titles[]
```

### NarrativeArchitect
```
Завантажує:
  - ChannelConfigs (genre, target_audience, style, character_count)
  - AIPromptConfigs (Narrative Template via selected_narrative_template)

Merge:
  - Config + Template + selected_topic → OpenAI request
  - system_prompt містить: role_definition + genre + style
  - user_prompt містить: selected_topic + character_count
  - Формується prompt з structure guidelines, tone, SSML settings

Output: narrative_text, scene_ssml[], metadata, scene_count
```

### GenerateAudio
```
Завантажує:
  - ChannelConfigs ТІЛЬКИ (tts_service, tts_voice_profile)
  - SSML markup вже готовий з narrative

Merge:
  - Map voice_profile → AWS Polly voice_id (Brian, Emma, Matthew...)
  - Validate and fix SSML markup
  - scenes + voice settings → AWS Polly API

Output: audio_urls[] (S3), total_duration_sec, voice_id, tts_service
```

### SaveResult
```
Завантажує: Nothing
Merge: Збір всіх даних з попередніх кроків
Output: Запис в GeneratedContent table
```

---

## Використання

### Сценарій 1: Перегляд останніх виконань

1. Відкрийте https://n8n-creator.space/dashboard.html
2. Перейдіть на вкладку "Monitoring"
3. Перегляньте статистику вгорі
4. Прокрутіть до "Step Functions Executions"
5. Бачите останні 20 виконань

### Сценарій 2: Детальний аналіз execution

1. В списку executions клікніть на будь-яке виконання
2. Відкриється модалка з інформацією
3. Побачите "✅ Виконання завантажено!"
4. Закрийте модалку
5. Прокрутіть до workflow візуалізації вгорі
6. Workflow блоки тепер показують статуси (✓/✗)
7. Клікайте на блоки щоб побачити Input/Output JSON!

### Сценарій 3: Розуміння data flow

1. Відкрийте Dashboard
2. Клікніть на будь-який workflow блок (навіть без вибраного execution)
3. Побачите Data Flow секцію:
   - Що завантажується з DynamoDB
   - Як відбувається merge
   - Що виходить на output
4. Це допоможе зрозуміти як працює кожен крок!

### Сценарій 4: Debug тестування

1. Перейдіть на вкладку "Debug"
2. Оберіть канал (наприклад "Mythology / Fantasy")
3. Натисніть "Start Test"
4. Чекайте ~2-3 хвилини
5. Переглядайте результати по кроках

---

## Troubleshooting

### Помилка: "No execution details loaded"
**Причина:** Не вибране execution
**Рішення:** Клікніть на виконання в списку "Step Functions Executions"

### Помилка: "AccessDeniedException ... GetExecutionHistory"
**Причина:** Lambda не має IAM прав
**Рішення:** Перевірте що DashboardAccessPolicy містить `states:GetExecutionHistory`

### Помилка: "CORS policy: multiple values"
**Причина:** Подвійний CORS header (Lambda + Lambda URL)
**Рішення:** Видаліть CORS headers з Lambda response (Lambda URL додає автоматично)

### Execution items не клікабельні
**Причина:** CSS не завантажився
**Рішення:**
1. Hard refresh (Ctrl + Shift + R)
2. Перевірте що workflow.css завантажився
3. Перевірте hover ефект - має бути підсвічування

### Workflow візуалізація не оновлюється після клікання на execution
**Причина:** API помилка або execution без кроків
**Рішення:**
1. Перевірте console logs (F12)
2. Перевірте що execution має статус SUCCEEDED або FAILED (не RUNNING)
3. Спробуйте інше execution

---

## Changelog

### 2025-11-06 - v1.0.0 (Current)
- ✅ Повна система моніторингу
- ✅ 7-крокова workflow візуалізація
- ✅ Execution history з Input/Output
- ✅ Debug test runner
- ✅ Data Flow metadata для кожного кроку
- ✅ Enhanced UX з інструкціями

### 2025-11-05
- 🔧 Базова структура dashboard
- 🔧 Prompts Editor TTS/Voice rename
- 🔧 SSML migration

---

## Майбутні Покращення

### Планується:
- [ ] Real-time execution tracking (WebSocket)
- [ ] Execution filtering по каналах/датах
- [ ] Export execution data to JSON/CSV
- [ ] Cost tracking per execution
- [ ] Performance metrics та charts
- [ ] Retry failed executions кнопка
- [ ] Comparison між executions

### Розглядається:
- [ ] Notifications (email/Slack) для failed executions
- [ ] Advanced search по execution history
- [ ] Custom dashboards
- [ ] API rate limiting monitoring

---

## Підтримка

**Документація:** https://n8n-creator.space/docs/
**Production URL:** https://n8n-creator.space/dashboard.html
**Git Repo:** E:/youtube-content-automation/

**Контакти:**
- Dashboard issues → перевірте console logs та IAM permissions
- Debug test issues → перевірте channel_id та Lambda logs
- UI issues → hard refresh (Ctrl + Shift + R)
