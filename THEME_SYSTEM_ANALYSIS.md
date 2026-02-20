# 🔍 Current Theme Generation System - Analysis & Cleanup Plan

**Date:** 2026-02-20
**Backup Commit:** `b93081e`
**Purpose:** Analyze current theme generation before implementing Topics Queue Manager

---

## 📊 ПОТОЧНА СИСТЕМА - ПОВНИЙ АНАЛІЗ

### **1. Lambda Functions**

#### **1.1 content-query-titles**
📁 **Path:** `aws/lambda/content-query-titles/lambda_function.py`

**Призначення:** Stub функція для генерації базових тем

**Код:**
```python
def lambda_handler(event, context):
    channel_id = event.get('channel_id')
    genre = event.get('genre', 'General')

    base_titles = [
        f"Історія про {genre} #1",
        f"Таємниця {genre} #2",
        f"Загадка {genre} #3"
    ]

    return {
        'channel_id': channel_id,
        'titles': base_titles,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
```

**Проблеми:**
- ❌ Hardcoded українські шаблони
- ❌ Не використовує DynamoDB
- ❌ Генерує одні й ті самі теми
- ❌ Не перевіряє дублікати

**Використання в Step Functions:**
```
Phase1ContentGeneration → QueryTitles → ThemeAgent → ...
```

**Висновок:** ⚠️ **МОЖНА ВИДАЛИТИ** - застаріла логіка, замінюється на Topics Queue

---

#### **1.2 content-theme-agent**
📁 **Path:** `aws/lambda/content-theme-agent/lambda_function.py`

**Призначення:** Генерує теми через OpenAI (GPT-4o)

**Що робить:**
1. Отримує OpenAI API key з Secrets Manager
2. Читає prompt config з `AIPromptConfigs` (agent_id='theme_agent')
3. Читає channel config з `ChannelConfigs`
4. Викликає OpenAI з system instructions + channel data
5. Парсить JSON відповідь (new_topics)
6. Зберігає результат в `GeneratedContent` (type='theme_generation')
7. Повертає generated_titles для Step Functions

**Конфігурація:**
- Model: `gpt-4o`
- Temperature: `0.9`
- Max tokens: `500`
- Response format: `json_object`

**Вхідні дані:**
```json
{
  "channel_id": "UCxxx",
  "channel_name": "Channel Name",
  "titles": ["Old title 1", "Old title 2"],
  "topics_to_generate": 4,
  "avoid_list": [],
  "factual_mode": "fictional"
}
```

**Вихідні дані:**
```json
{
  "channel_id": "UCxxx",
  "channel_name": "Channel Name",
  "genre": "Horror",
  "generated_titles": [
    "The Haunted Lighthouse",
    "Whispers from the Forest",
    "The Cursed Mirror",
    "Shadows of the Past"
  ],
  "timestamp": "2026-02-20T14:30:00Z"
}
```

**Використання в Step Functions:**
```
ThemeAgent → CheckFactualMode → MegaNarrativeGenerator
```

**Проблеми:**
- ❌ Не зберігає теми для повторного використання
- ❌ Кожен раз генерує нові теми (витрачає API calls)
- ❌ Немає черги тем
- ❌ Немає UI для перегляду згенерованих тем

**Висновок:** 🔄 **ПЕРЕРОБЛЮЄМО** - залишаємо як AI generator для Topics Queue

---

### **2. DynamoDB Tables**

#### **2.1 ThemeTemplates**
**Призначення:** Зберігає промпт конфігурацію для ThemeAgent (аналогічно NarrativeTemplates)

**Schema:**
- PK: `template_id` (String)

**Записів:** 1 (`theme_agent_v2`)

**Структура:**
```json
{
  "template_id": "theme_agent_v2",
  "template_name": "Theme Agent",
  "template_type": "theme",
  "is_default": true,
  "is_active": 1,
  "version": "5.1",
  "ai_config": {
    "model": "gpt-4o",
    "temperature": 0.9,
    "sections": {
      "role_definition": "You are ThemeAgent...",
      "core_rules": [
        "RELEVANCE: ...",
        "UNIQUENESS: ...",
        "HOOK POTENTIAL: ...",
        ...
      ]
    }
  },
  "topic_generation": {
    "topics_per_request": 5,
    "check_last_n_topics": 50,
    "similarity_threshold": 0.5,
    "max_attempts": 3
  }
}
```

**Висновок:** ✅ **ЗАЛИШАЄМО** - це промпт template, не дані тем

---

#### **2.2 GeneratedContent (type='theme_generation')**
**Призначення:** Лог всіх згенерованих тем

**Schema:**
- PK: `channel_id` (String)
- SK: `created_at` (String - ISO timestamp)

**Записів:** **340 theme_generation** (з 708 total scanned)

**Структура:**
```json
{
  "channel_id": "UCElf48pne-8zWih8Ha5gzgQ",
  "created_at": "2025-11-28T21:53:22.785403Z",
  "type": "theme_generation",
  "channel_name": "",
  "genre": "Documentary / Mystery",
  "input_titles": ["Історія про Documentary / Mystery #1", ...],
  "generated_titles": [
    "Unveiling the Shadows: Political Secrets Revealed",
    "The Lost Files of a Forgotten Conspiracy",
    "Inside the Walls of Secret Societies",
    "Dark History: The Truth Behind the Forbidden Tales"
  ],
  "full_response": { ... },
  "model": "gpt-4o",
  "api_version": "responses_api",
  "prompt_version": "1.0",
  "status": "completed"
}
```

**Проблеми:**
- ❌ Теми НЕ використовуються повторно
- ❌ Просто лог (архів)
- ❌ Немає статусу (pending/used/completed)
- ❌ Немає пріоритетів
- ❌ Немає UI для перегляду

**Висновок:** 🔄 **ПЕРЕРОБЛЯЄМО** - можна використати цю таблицю для Topics Queue!

---

### **3. Step Functions Flow**

**Поточний Flow (Phase 1):**
```
GetActiveChannels
  ↓
Phase1ContentGeneration (Map - для кожного каналу)
  ↓
  QueryTitles (stub - повертає base_titles)
    ↓
  ThemeAgent (генерує нові теми через OpenAI)
    ↓
  CheckFactualMode
    ↓
  SearchWikipediaFacts / SetNoFacts
    ↓
  MegaNarrativeGenerator (бере generated_titles[0])
```

**Проблема:** Кожен раз генерується **1 тема** → викорис

товується → викидається. Немає черги.

---

## 🧹 ПЛАН CLEANUP

### **ЩО ВИДАЛЯЄМО:**

#### ❌ **1. content-query-titles Lambda**
- **Причина:** Застаріла stub функція, не використовується в новій логіці
- **Дія:**
  1. Видалити `aws/lambda/content-query-titles/`
  2. Видалити з Step Functions definition
  3. Видалити Lambda функцію в AWS

#### ❌ **2. QueryTitles state з Step Functions**
- **Причина:** Замінюється на `GetNextTopicFromQueue`
- **Дія:** Оновити `sfn_def.json`

#### ⚠️ **3. Очистити старі theme_generation записи з GeneratedContent**
- **Причина:** 340 старих записів займають місце
- **Дія:** Видалити всі записи де `type='theme_generation'` (це просто лог)
- **Script:**
  ```bash
  # Backup перед видаленням
  aws dynamodb scan --table-name GeneratedContent \
    --filter-expression "#t = :theme_gen" \
    --expression-attribute-names '{"#t":"type"}' \
    --expression-attribute-values '{":theme_gen":{"S":"theme_generation"}}' \
    > backup_theme_generation_$(date +%Y%m%d).json

  # Потім видалити через batch-write-item
  ```

---

### **ЩО ЗАЛИШАЄМО:**

#### ✅ **1. content-theme-agent Lambda**
- **Причина:** Переробляємо в `content-topics-generate` для AI генерації тем
- **Дія:** Рефакторинг:
  - Залишити логіку виклику OpenAI
  - Змінити output - додавати теми в Topics Queue замість повертати в Step Functions
  - Додати batch generation (1-100 тем)

#### ✅ **2. ThemeTemplates table**
- **Причина:** Це промпт template, потрібен для AI generation
- **Дія:** Залишити без змін

---

## 🔄 МІГРАЦІЯ GENERATEDCONTENT → TOPICS QUEUE

### **Опція 1: Переробити GeneratedContent (НЕ РЕКОМЕНДУЄТЬСЯ)**

**Проблеми:**
- Таблиця вже має складну структуру (narrative, theme_generation, audio, etc.)
- PK/SK: channel_id + created_at (не підходить для черги)
- Важко фільтрувати pending topics
- Конфлікт з існуючими даними

**Висновок:** ❌ **НЕ РОБИТИ** - краще створити нову таблицю

---

### **Опція 2: Створити нову таблицю ContentTopicsQueue (РЕКОМЕНДУЄТЬСЯ)**

**Переваги:**
- ✅ Чіста структура для черги
- ✅ Правильні PK/SK для сортування за пріоритетом
- ✅ GSI для фільтрації за статусом
- ✅ Немає конфлікту з існуючими даними

**Schema:**
```json
{
  "TableName": "ContentTopicsQueue",
  "KeySchema": [
    { "AttributeName": "channel_id", "KeyType": "HASH" },
    { "AttributeName": "topic_id", "KeyType": "RANGE" }
  ],
  "AttributeDefinitions": [
    { "AttributeName": "channel_id", "AttributeType": "S" },
    { "AttributeName": "topic_id", "AttributeType": "S" },
    { "AttributeName": "status", "AttributeType": "S" },
    { "AttributeName": "priority", "AttributeType": "N" }
  ],
  "GlobalSecondaryIndexes": [
    {
      "IndexName": "status-priority-index",
      "KeySchema": [
        { "AttributeName": "channel_id", "KeyType": "HASH" },
        { "AttributeName": "status", "KeyType": "RANGE" }
      ]
    }
  ]
}
```

**Висновок:** ✅ **РОБИМО ЦЕ**

---

### **Опція 3: Мігрувати старі теми в нову таблицю (ОПЦІОНАЛЬНО)**

Якщо хочете зберегти 340 старих згенерованих тем:

**Script:**
```python
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
old_table = dynamodb.Table('GeneratedContent')
new_table = dynamodb.Table('ContentTopicsQueue')

# Scan old theme_generation records
response = old_table.scan(
    FilterExpression='#t = :theme_gen',
    ExpressionAttributeNames={'#t': 'type'},
    ExpressionAttributeValues={':theme_gen': 'theme_generation'}
)

for item in response['Items']:
    channel_id = item['channel_id']
    generated_titles = item.get('generated_titles', [])

    # Add each title to new queue
    for idx, title in enumerate(generated_titles):
        topic_id = f"{item['created_at']}_{idx}"

        new_table.put_item(
            Item={
                'channel_id': channel_id,
                'topic_id': topic_id,
                'topic_text': title,
                'status': 'pending',  # Mark as pending
                'priority': 100,
                'created_at': item['created_at'],
                'source': 'migrated',
                'user_id': 'migration_script'
            }
        )

print(f"Migrated {len(response['Items'])} theme_generation records")
```

**Висновок:** ⚠️ **ОПЦІОНАЛЬНО** - якщо хочете переробити старі теми в чергу

---

## 📝 IMPLEMENTATION CHECKLIST

### **Phase 1: Cleanup (1 день)**
- [ ] Створити backup існуючих theme_generation записів
- [ ] Видалити 340 theme_generation записів з GeneratedContent
- [ ] Видалити `aws/lambda/content-query-titles/` folder
- [ ] Видалити QueryTitles state з Step Functions
- [ ] Deploy updated Step Functions definition

### **Phase 2: New Table (1 день)**
- [ ] Створити DynamoDB таблицю `ContentTopicsQueue`
- [ ] Додати GSI для status filtering
- [ ] Тестування таблиці

### **Phase 3: Refactor Lambdas (2 дні)**
- [ ] Перейменувати `content-theme-agent` → `content-topics-generate`
- [ ] Рефакторити логіку (batch generation, add to queue)
- [ ] Створити нові Lambda:
  - `content-topics-add`
  - `content-topics-list`
  - `content-topics-delete`
  - `content-topics-update-status`
  - `content-topics-get-next`

### **Phase 4: Step Functions Integration (1 день)**
- [ ] Додати `CheckAutoProcessQueue` state
- [ ] Додати `GetNextTopicFromQueue` state
- [ ] Додати `MarkTopicInProgress` / `MarkTopicCompleted` states
- [ ] Тестування flow

### **Phase 5: UI (2 дні)**
- [ ] Додати Topics Queue Manager секцію
- [ ] Додати comprehensive dropdowns для Story Engine
- [ ] Тестування UI

**Total:** ~1 тиждень

---

## 💡 RECOMMENDATIONS

### **1. Не мігрувати старі теми**
- Причина: 340 старих тем не мають контексту (channel_config міг змінитись)
- Краще почати з чистої черги і дати користувачу згенерувати нові

### **2. Видалити QueryTitles Lambda повністю**
- Вона не використовується в новій логіці
- Stub функція без цінності

### **3. Переробити ThemeAgent в Topics Generator**
- Залишити логіку OpenAI
- Змінити призначення: генерувати багато тем за раз
- Додавати в Topics Queue замість повертати в Step Functions

### **4. Очистити GeneratedContent від theme_generation**
- Створити backup перед видаленням
- Видалити 340 записів (вони не використовуються)
- Зменшити розмір таблиці

---

## ⚠️ ВАЖЛИВО

**Перед початком:**
1. ✅ Backup створено: commit `b93081e`
2. ✅ Backup в GitHub: pushed
3. ⏳ Backup DynamoDB theme_generation: TODO
4. ⏳ Тестування на dev environment: TODO

**Після cleanup:**
- Видалені Lambda не можна відновити (тільки через git)
- Видалені DynamoDB записи не можна відновити (тільки з backup)
- Step Functions зміни reversible (через git)

---

**READY TO CLEANUP! 🧹**

Чекаю підтвердження перед видаленням старих даних.
