# 🎬 YouTube Content Automation

> Автоматизована система генерації контенту для YouTube каналів з використанням AWS Lambda, DynamoDB та OpenAI API

[![Deploy](https://github.com/Aizekhan/youtube-content-automation/workflows/Deploy%20Website/badge.svg)](https://github.com/Aizekhan/youtube-content-automation/actions)

---

## 📋 Зміст

- [Огляд](#огляд)
- [Архітектура](#архітектура)
- [Функціональність](#функціональність)
- [AWS Dashboard](#aws-dashboard)
- [Встановлення](#встановлення)
- [Конфігурація](#конфігурація)
- [Deployment](#deployment)
- [API Endpoints](#api-endpoints)
- [Lambda Functions](#lambda-functions)
- [DynamoDB Tables](#dynamodb-tables)
- [Розробка](#розробка)

---

## 🎯 Огляд

Система автоматизації створення контенту для YouTube з використанням AI-агентів. Включає генерацію тем, написання нарративів, управління каналами та повний моніторинг через веб-dashboard.

### Ключові можливості:

- ✅ **AI-генерація контенту** - Theme Agent та Narrative Architect
- ✅ **Управління каналами** - Конфігурація параметрів для кожного каналу
- ✅ **AWS Dashboard** - Моніторинг, аналітика витрат, браузер контенту
- ✅ **Step Functions** - Оркестрація workflow
- ✅ **Auto-deployment** - GitHub Actions → nginx

---

## 🏗 Архітектура

```
┌─────────────────────────────────────────────────────────────┐
│                    Web Dashboard (nginx)                     │
│  https://n8n-creator.space                                  │
├──────────────┬──────────────┬──────────────┬────────────────┤
│  index.html  │ dashboard    │   costs      │   content      │
│  prompts     │ channel-cfg  │              │                │
└──────┬───────┴──────┬───────┴──────┬───────┴────────┬───────┘
       │              │              │                │
       ▼              ▼              ▼                ▼
┌──────────────────────────────────────────────────────────────┐
│           API Gateway: youtube-content-api                    │
│           https://e2c5y2h1qj.execute-api...                  │
├──────────────┬──────────────┬──────────────┬─────────────────┤
│ /monitoring  │   /costs     │  /content    │  (other)        │
└──────┬───────┴──────┬───────┴──────┬───────┴─────────┬───────┘
       │              │              │                 │
       ▼              ▼              ▼                 ▼
┌──────────────────────────────────────────────────────────────┐
│                    AWS Lambda Functions                       │
├─────────────────────┬────────────────────┬───────────────────┤
│ dashboard-*         │ content-*          │ prompts-api       │
│ (monitoring, costs, │ (theme, narrative, │                   │
│  content)           │  query, etc.)      │                   │
└─────────┬───────────┴──────────┬─────────┴───────────────────┘
          │                      │
          ▼                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   AWS Services                               │
├──────────────┬──────────────┬──────────────┬────────────────┤
│  DynamoDB    │ Step Functions│ CloudWatch  │ Cost Explorer │
│  (4 tables)  │               │   Logs      │               │
└──────────────┴──────────────┴──────────────┴────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│              Secrets Manager + OpenAI API                    │
└─────────────────────────────────────────────────────────────┘
```

---

## ✨ Функціональність

### 🎨 Web Dashboard (6 сторінок)

| Сторінка | URL | Опис |
|----------|-----|------|
| **Home** | `/index.html` | Головна навігація, статистика системи |
| **AI Prompts** | `/prompts-editor.html` | Редагування system instructions для AI агентів |
| **Channels** | `/channel-configs.html` | Управління конфігами YouTube каналів |
| **Dashboard** | `/dashboard.html` | Моніторинг Step Functions та CloudWatch логів |
| **Costs** | `/costs.html` | Аналітика витрат AWS (Cost Explorer) |
| **Content** | `/content.html` | Браузер згенерованого контенту з фільтрами |

### 🤖 AI Агенти

1. **Theme Agent** (`asst_LU5uAd9wl80iRcgIKEOhvRcUy`)
   - Генерація тем для відео
   - Враховує genre, tone, content_focus
   - Уникає повторень (avoid_list)

2. **Narrative Architect** (`asst_fPFoVgntXOcQSIVJSMyGKlR8`)
   - Створення повних нарративів
   - Структура сцен з timing
   - TTS та image generation параметри

---

## 📊 AWS Dashboard

### 1. **Process Monitoring** (`dashboard.html`)
- 📈 Step Functions executions статус
- 📜 CloudWatch логи (real-time)
- ⏱️ Статистика виконання (Running/Succeeded/Failed)
- 🔄 Auto-refresh кожні 30 секунд

### 2. **Cost Analytics** (`costs.html`)
- 💰 Витрати по AWS сервісам
- 📊 Графіки розподілу (Chart.js)
- 🔮 Прогноз місячних витрат
- 🤖 OpenAI API usage tracking
- 📈 30-денний тренд

### 3. **Content Browser** (`content.html`)
- 📚 Перегляд з DynamoDB GeneratedContent
- 🔍 Фільтри: тип, канал, дата, пошук
- 👁️ Модальні вікна з повними деталями
- 📥 Експорт у JSON
- 📊 Статистика контенту

---

## 🚀 Встановлення

### Вимоги:
- Node.js 18+
- AWS CLI configured
- AWS Account з правами на Lambda, DynamoDB, API Gateway
- OpenAI API Key
- Notion API Key (для task management)

### Швидкий старт:

```bash
# 1. Clone репозиторій
git clone https://github.com/Aizekhan/youtube-content-automation.git
cd youtube-content-automation

# 2. Встановити залежності
npm install

# 3. Налаштувати .env
cp .env.example .env
# Відредагувати .env з вашими ключами

# 4. Deploy Lambda functions
cd aws/lambda/content-theme-agent
# ... zip and upload

# 5. Налаштувати API Gateway
# Див. розділ "API Endpoints"

# 6. Deploy website
# Автоматично через GitHub Actions
```

---

## ⚙️ Конфігурація

### AWS Region
```
eu-central-1
```

### AWS Secrets Manager

| Secret Name | Опис |
|-------------|------|
| `openai/api-key` | OpenAI API ключ |
| `openai/assistant-ids` | Theme + Narrative Assistant IDs |
| `notion/api-key` | Notion Integration Token |
| `notion/database-id` | Notion Tasks Database ID |

### Environment Variables (`.env`)

```bash
# AWS
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_DEFAULT_REGION=eu-central-1

# OpenAI
OPENAI_API_KEY=sk-proj-...
OPENAI_ASSISTANT_THEME=asst_LU5uAd9wl80iRcgIKEOhvRcUy
OPENAI_ASSISTANT_NARRATIVE=asst_fPFoVgntXOcQSIVJSMyGKlR8

# Notion
NOTION_API_KEY=ntn_...
NOTION_DB_TASKS=29fc7cc7fa97...
```

---

## 🌐 Deployment

### GitHub Actions (Auto-deploy)

Файл: `.github/workflows/deploy-website.yml`

**Trigger:**
- Push до `master` branch
- Зміни в `*.html` файлах
- Manual trigger (`workflow_dispatch`)

**Deploy target:**
- Server: `n8n-creator.space`
- Protocol: SCP via SSH
- Files: 6 HTML files

**Secrets потрібні:**
```
SSH_HOST
SSH_USER
SSH_KEY
SSH_PORT
SSH_WEB_PATH
```

### Manual Deploy

```bash
# Deploy Lambda function
cd aws/lambda/dashboard-monitoring
zip -r dashboard-monitoring.zip .
aws lambda update-function-code \
  --function-name dashboard-monitoring \
  --zip-file fileb://dashboard-monitoring.zip \
  --region eu-central-1

# Deploy API Gateway changes
aws apigateway create-deployment \
  --rest-api-id e2c5y2h1qj \
  --stage-name prod \
  --region eu-central-1
```

---

## 🔌 API Endpoints

**Base URL:** `https://e2c5y2h1qj.execute-api.eu-central-1.amazonaws.com/prod`

### Monitoring

```http
GET /monitoring/executions
Response: {
  executions: [...],
  stats: { running, succeeded, failed, avgDuration }
}

GET /monitoring/logs?limit=50
Response: {
  logs: [{ timestamp, message }, ...]
}
```

### Costs

```http
GET /costs/summary
Response: {
  summary: { monthToDate, yesterday, forecast, lastMonth },
  services: [{ name, cost }, ...],
  daily: [{ date, cost }, ...],
  openai: { totalCost, requests, tokens, avgCost }
}
```

### Content

```http
GET /content/list?limit=100
Response: {
  content: [{ channel_id, created_at, type, ... }, ...],
  stats: { total, themes, narratives, today }
}
```

---

## ⚡ Lambda Functions

### Content Generation

| Function | Опис | Runtime |
|----------|------|---------|
| `content-theme-agent` | Генерація тем через OpenAI | Python 3.11 |
| `content-narrative` | Створення нарративів | Python 3.11 |
| `content-query-titles` | YouTube API запити | Python 3.11 |
| `content-save-result` | Збереження в DynamoDB | Python 3.11 |
| `content-get-channels` | Отримання активних каналів | Python 3.11 |
| `content-select-topic` | Вибір теми для narrative | Python 3.11 |

### Dashboard

| Function | Опис | Runtime |
|----------|------|---------|
| `dashboard-monitoring` | Step Functions + CloudWatch | Python 3.11 |
| `dashboard-costs` | Cost Explorer API | Python 3.11 |
| `dashboard-content` | DynamoDB queries | Python 3.11 |

### Admin

| Function | Опис | Runtime |
|----------|------|---------|
| `prompts-api` | CRUD для AI prompts | Python 3.11 |
| `n8n-dynamodb-proxy` | DynamoDB proxy для n8n | Python 3.11 |

---

## 🗄️ DynamoDB Tables

### 1. **ChannelConfigs**
```
PK: config_id (UUID)
GSI: channel_id-index
Fields: channel_name, genre, tone, narration_style,
        visual_keywords, is_active, ...
```

### 2. **AIPromptConfigs**
```
PK: agent_id (String)
Fields: system_instructions, model, temperature,
        max_tokens, version, ...
```

### 3. **GeneratedContent**
```
PK: channel_id (String)
SK: created_at (ISO timestamp)
Fields: type, story_title, narrative_text,
        generated_titles, scenes, character_count, ...
```

### 4. **DailyPublishingStats**
```
PK: channel_id
SK: date
Fields: videos_published, views, ...
```

---

## 🛠 Розробка

### Локальне тестування Lambda

```bash
# Тест dashboard-monitoring
cd aws/lambda/dashboard-monitoring
python lambda_function.py

# З mock event
echo '{"httpMethod":"GET","path":"/monitoring/executions"}' | \
  python -c "import lambda_function, sys, json; \
  print(json.dumps(lambda_function.lambda_handler(json.load(sys.stdin), {})))"
```

### Notion Integration

```javascript
// Оновлення статусу завдання
const { updateTaskStatus } = require('./notion-tasks-helper');
await updateTaskStatus('task-id', '🟢 Done');

// Створення sub-task
await createSubTask('Task name', parentId, '🔴 Todo', '🔥 High');
```

### Тестування API

```bash
# Test monitoring endpoint
curl https://e2c5y2h1qj.execute-api.eu-central-1.amazonaws.com/prod/monitoring/executions

# Test costs endpoint
curl https://e2c5y2h1qj.execute-api.eu-central-1.amazonaws.com/prod/costs/summary

# Test content endpoint
curl https://e2c5y2h1qj.execute-api.eu-central-1.amazonaws.com/prod/content/list?limit=10
```

---

## 📁 Структура проекту

```
youtube-content-automation/
├── .github/
│   └── workflows/
│       ├── deploy-lambda.yml
│       └── deploy-website.yml
├── aws/
│   └── lambda/
│       ├── content-theme-agent/
│       ├── content-narrative/
│       ├── content-query-titles/
│       ├── content-save-result/
│       ├── content-get-channels/
│       ├── content-select-topic/
│       ├── dashboard-monitoring/
│       ├── dashboard-costs/
│       ├── dashboard-content/
│       ├── prompts-api/
│       └── n8n-dynamodb-proxy/
├── terraform/              # Infrastructure as Code (optional)
│   ├── main.tf
│   ├── variables.tf
│   ├── dynamodb.tf
│   ├── lambda.tf
│   ├── iam.tf
│   └── stepfunctions.tf
├── index.html              # Dashboard home
├── dashboard.html          # Process monitoring
├── costs.html              # Cost analytics
├── content.html            # Content browser
├── prompts-editor.html     # AI prompts editor
├── channel-configs.html    # Channel management
├── notion-tasks-helper.js  # Notion API helper
├── package.json
├── .env.example
└── README.md
```

---

## 📝 Changelog

### [Unreleased]

### [1.1.0] - 2025-11-03
**Added:**
- AWS Dashboard (index, dashboard, costs, content pages)
- 3 нові Lambda functions для Dashboard
- API Gateway endpoints для моніторингу
- IAM policies для Cost Explorer, Step Functions, CloudWatch
- Navigation menu на всіх сторінках
- GitHub Actions auto-deploy для всіх HTML

**Changed:**
- API Gateway renamed: `n8n-dynamodb-api` → `youtube-content-api`
- Updated prompts-editor.html та channel-configs.html з навігацією

**Fixed:**
- MCP config - hardcoded Notion token замінено на env variable

### [1.0.0] - 2025-10-XX
**Initial Release:**
- Content generation workflow
- Theme Agent + Narrative Architect
- DynamoDB tables setup
- Basic Lambda functions
- prompts-editor.html та channel-configs.html

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📄 License

This project is private and proprietary.

---

## 👥 Authors

- **Aizekhan** - [GitHub](https://github.com/Aizekhan)

---

## 🙏 Acknowledgments

- OpenAI for GPT-4 and Assistants API
- AWS for Lambda, DynamoDB, and other services
- Notion for task management integration
- Bootstrap & Chart.js for UI components

---

## 📧 Support

Для питань та підтримки:
- GitHub Issues: [Create an issue](https://github.com/Aizekhan/youtube-content-automation/issues)
- Email: [your-email]

---

**🚀 Made with Claude Code**
