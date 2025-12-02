# Комплексний Архітектурний Аналіз Системи
**Дата:** 2 грудня 2025
**Версія:** 1.0

---

## Зміст

1. [Поточна Архітектура](#1-поточна-архітектура)
2. [Ідеальна Архітектура](#2-ідеальна-архітектура)
3. [Порівняльний Аналіз](#3-порівняльний-аналіз)
4. [Рекомендації](#4-рекомендації)

---

# 1. ПОТОЧНА АРХІТЕКТУРА

## 1.1 Загальний Огляд Системи

### Призначення
Повністю автоматизована платформа для генерації YouTube контенту з використанням AI:
- **Вхід:** Назва каналу + мінімальні налаштування
- **Вихід:** Готове відео (MP4) з нарративом, AI-зображеннями, озвученням, ефектами

### Основні Компоненти
```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Web Admin)                         │
│  - Cognito Auth (cookie-based, 5 cookies)                       │
│  - Dashboard, Channels, Content, Costs, Prompts Editor          │
│  - CSP Security Headers + HTTPS                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              AWS STEP FUNCTIONS (Orchestration)                 │
│  ContentGenerator State Machine (3-Phase Architecture)          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   35+ AWS LAMBDA FUNCTIONS                      │
│  - Content Generation (GPT-4o)                                  │
│  - Image Batching & Generation (SD 3.5)                         │
│  - TTS (Polly/ElevenLabs)                                       │
│  - Video Assembly (Hybrid Lambda/ECS)                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  DATA STORAGE & SERVICES                        │
│  - DynamoDB (10 tables, multi-tenant)                           │
│  - S3 (4 buckets: audio, images, videos, data)                 │
│  - EC2 GPU (SD 3.5 Large inference)                             │
│  - SQS (retry queue system)                                     │
│  - EventBridge (scheduled triggers)                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 1.2 Автентифікація і Мультитенантність

### 1.2.1 AWS Cognito Authentication

**Архітектурне Рішення:**
```
User Login → Cognito User Pool → JWT Token (>4KB)
  ↓
Split into 5 cookies (bypass browser 4KB limit):
  - auth_token_0 (1024 bytes)
  - auth_token_1 (1024 bytes)
  - auth_token_2 (1024 bytes)
  - auth_token_3 (1024 bytes)
  - auth_token_4 (remaining bytes)
```

**Логічний Вузол:** `js/auth.js`
- Відповідальність: Управління сесією, розділення токенів
- З'єднання: Cognito User Pool ↔ Frontend ↔ API Gateway

**Потік Даних:**
1. Користувач вводить credentials
2. Cognito повертає `IdToken` + `AccessToken` + `RefreshToken`
3. Frontend зберігає у 5 cookies (для обходу ліміту браузера)
4. Кожен API запит надсилає всі 5 cookies
5. Backend об'єднує cookies → валідує через Cognito

**Критичні Точки:**
- ✅ **Правильно:** Cookie splitting вирішує проблему великих JWT
- ⚠️ **Ризик:** Якщо один cookie втратиться → сесія інвалідується
- ⚠️ **Ризик:** HTTPS-only cookies (не працює на localhost без налаштувань)

### 1.2.2 Multi-Tenant Data Isolation

**Архітектурне Рішення:**
```
user_id (Cognito Sub) → Partition Key для всіх даних
```

**DynamoDB Schema Pattern:**
```
ChannelConfigs:
  PK: user_id + channel_id
  GSI: user_id-is_active-index (для фільтрації активних каналів)

GeneratedContent:
  PK: content_id (timestamp-based)
  GSI: user_id-created_at-index (мультитенант запити)
  GSI: channel_id-created_at-index (контент конкретного каналу)
  GSI: content_id-created_at-index (для video assembly)

CostTracking:
  PK: user_id + date + timestamp
  Aggregation: По user_id + date для денних сум
```

**Логічні Вузли:**
- **content-get-channels** - Фільтрація каналів: `user_id = :user_id AND is_active = true`
- **content-save-result** - Зберігання: завжди додає `user_id` до запису
- **dashboard-content** - Запити: завжди фільтрує по `user_id`

**Потік Даних:**
```
Step Functions Trigger (user_id: "abc123")
  ↓
GetActiveChannels → Query DynamoDB WHERE user_id="abc123" AND is_active=true
  ↓
Phase 1 Map (5 parallel) → Кожна ітерація отримує channel конкретного user_id
  ↓
SaveResult → Записує у GeneratedContent з user_id="abc123"
  ↓
Dashboard → Показує лише контент WHERE user_id="abc123"
```

**Критичні Точки:**
- ✅ **Правильно:** Повна ізоляція даних на рівні DynamoDB
- ✅ **Правильно:** GSI індекси дозволяють ефективні запити
- ⚠️ **Потенційна проблема:** Якщо забути додати `user_id` у Lambda → витік даних
- ⚠️ **Потенційна проблема:** Немає row-level security - ізоляція лише на рівні коду

---

## 1.3 Трифазний Workflow (Основна Логіка)

### Архітектурна Концепція

**3 Фази Обробки:**
```
PHASE 1: Parallel Content Generation (MaxConcurrency: 5)
  - Для кожного каналу незалежно
  - GPT-4o генерує: theme → narrative → image prompts
  - Результати зберігаються у S3

PHASE 2: Centralized Batched Image Generation (Single EC2)
  - Збирає ВСІ image prompts з усіх каналів
  - Розділяє на батчі по 6 зображень
  - 3 батчі паралельно (MaxConcurrency: 3)
  - Розподіляє готові зображення назад по каналам

PHASE 3: Parallel Audio & Save (MaxConcurrency: 5)
  - Для кожного каналу незалежно
  - Генерація аудіо (Polly/ElevenLabs)
  - Збереження у DynamoDB
  - Тригер Video Assembly
```

### 1.3.1 PHASE 1: Content Generation

**Логічний Потік:**
```
ValidateInput
  ↓
GetActiveChannels → Query DynamoDB (user_id + is_active=true)
  ↓
SavePhase1ToS3 → Зберігає список каналів у S3 (обхід 256KB ліміту Step Functions)
  ↓
Phase1ContentGeneration (Map State, MaxConcurrency: 5)
  ├─ Iterator для кожного каналу:
  │   ├─ QueryTitles → OpenAI пошук схожих назв (антиплагіат)
  │   ├─ ThemeAgent → GPT-4o: theme, opening_hook, key_moments, climax_reveal
  │   ├─ Narrative → GPT-4o: 5 scenes з діалогами + image prompts
  │   └─ SavePhase1Result → S3 (phase1_results/user_id/channel_id.json)
  └─ Results: Масив результатів для кожного каналу
```

**Ключові Lambda Functions:**

**validate-step-functions-input** (`aws/lambda/validate-step-functions-input/`)
- **Призначення:** Валідація вхідних даних на початку workflow
- **Вхід:** `{ user_id, requested_channels }` (опціонально: test_mode)
- **Вихід:** `{ valid: true/false, errors: [...] }`
- **Логіка:** Контекстно-залежна валідація (різні поля на різних етапах)
- **Критична Точка:** V2.0 виправлено - перевіряє лише поля які існують на даному етапі

**content-get-channels** (`aws/lambda/content-get-channels/`)
- **Призначення:** Отримання активних каналів користувача
- **Вхід:** `{ user_id, requested_channels?: string[] }`
- **Запит DynamoDB:**
  ```python
  response = table.query(
      IndexName='user_id-is_active-index',
      KeyConditionExpression='user_id = :user_id AND is_active = :true',
      FilterExpression='channel_id IN (:channels)' if requested_channels else None
  )
  ```
- **Вихід:** `{ channels: [...], count: N }`
- **Критична Точка:** Використовує GSI для ефективності (не scan всієї таблиці)

**content-select-topic** (`aws/lambda/content-select-topic/`)
- **Призначення:** Пошук схожих назв через OpenAI для антиплагіату
- **API:** OpenAI Embeddings + similarity search
- **Вихід:** Список схожих назв з YouTube
- **Критична Точка:** Допомагає уникати дублювання контенту

**content-theme-agent** (`aws/lambda/content-theme-agent/`)
- **Призначення:** Генерація теми та структури оповідання
- **AI Model:** GPT-4o (через OpenAI API)
- **Промпт Engineering:**
  - Базовий системний промпт (з ThemeTemplates DynamoDB)
  - Mega config merger (об'єднує channel config + template + user preferences)
  - Структурований вивід: `{ theme, opening_hook, key_moments, climax_reveal }`
- **Критична Точка:** Використовує `response_format: json_object` для structured output

**content-narrative** (`aws/lambda/content-narrative/`)
- **Призначення:** Генерація повного нарративу з 5 сцен
- **AI Model:** GPT-4o-mini (дешевше для довгих текстів)
- **Вхід:** Theme з попереднього кроку
- **Вихід:**
  ```json
  {
    "title": "...",
    "scenes": [
      {
        "scene_id": "scene_1",
        "narrative_text": "Plain text without SSML",
        "image_prompt": "Detailed Stable Diffusion prompt"
      },
      // ... 4 more scenes
    ]
  }
  ```
- **Критична Точка:** TTS v2.0 - LLM генерує ЛИШЕ plain text (без SSML)
- **Архітектурне Рішення:** Розділення content від markup (flexibility для різних TTS)

**save-phase1-to-s3** (`aws/lambda/save-phase1-to-s3/`)
- **Призначення:** Зберігання проміжних результатів Phase 1 у S3
- **S3 Path:** `s3://youtube-automation-data-grucia/phase1_results/{user_id}/{channel_id}.json`
- **Причина:** Обхід 256KB ліміту Step Functions (великі payloads)
- **Критична Точка:** State offloading pattern - зберігаємо великі дані у S3, передаємо лише S3 URI

**Критичні Архітектурні Рішення Phase 1:**

1. ✅ **MaxConcurrency: 5** - Баланс між швидкістю та OpenAI rate limits
2. ✅ **S3 State Offloading** - Уникаємо 256KB ліміту Step Functions
3. ✅ **Structured JSON Output** - `response_format: json_object` для надійного парсингу
4. ✅ **TTS v2.0 Separation** - LLM генерує plain text, SSML додається пізніше
5. ⚠️ **Потенційна проблема:** OpenAI rate limits при 5+ каналах одночасно
6. ⚠️ **Потенційна проблема:** Якщо GPT-4o поверне невалідний JSON → workflow fails

---

### 1.3.2 PHASE 2: Image Batching System

**Архітектурна Інновація:** Централізована обробка замість per-channel sequential

**Старий Підхід (до батчінгу):**
```
Для кожного каналу (послідовно):
  - Генерувати 6 зображень
  - Час: 18 секунд * 9 каналів = 162 секунди
```

**Новий Підхід (батчінг):**
```
Зібрати всі промпти → Розділити на батчі → 3 батчі паралельно
  - Час: 54 зображення за 90 секунд
  - Прискорення: 3.3x
```

**Логічний Потік:**
```
LoadPhase1FromS3 → Завантажує всі результати Phase 1 з S3
  ↓
CollectAllImagePrompts → Збирає ВСІ image prompts з усіх каналів
  ↓
PrepareImageBatches → Розділяє на батчі по 6 промптів
  ↓
StartEC2ForAllImages → Запускає EC2 GPU instance (з retry logic)
  ↓
GenerateAllImagesBatched (Map State, MaxConcurrency: 3)
  ├─ Iterator для кожного батчу:
  │   └─ GenerateBatch → POST до EC2 API (batch з 6 промптів)
  └─ Results: 3 батчі з 18 зображеннями кожен
  ↓
MergeImageBatches → Об'єднує результати всіх батчів
  ↓
DistributeImagesToChannels → Розподіляє зображення назад по каналам
  ↓
StopEC2AfterImages → Зупиняє EC2 instance (економія коштів)
```

**Ключові Lambda Functions:**

**collect-all-image-prompts** (`aws/lambda/collect-all-image-prompts/`)
- **Призначення:** Агрегація всіх image prompts з Phase 1
- **Вхід:** `{ phase1_results: [...] }` (з S3)
- **Логіка:**
  ```python
  all_prompts = []
  for channel in phase1_results:
      for scene in channel['narrative']['scenes']:
          all_prompts.append({
              'channel_id': channel['channel_id'],
              'scene_id': scene['scene_id'],
              'prompt': scene['image_prompt']
          })
  return {'all_image_prompts': all_prompts, 'total_images': len(all_prompts)}
  ```
- **Вихід:** Плоский список всіх промптів з метаданими (channel_id, scene_id)

**prepare-image-batches** (`aws/lambda/prepare-image-batches/`)
- **Призначення:** Розділення промптів на батчі по 6
- **Логіка:**
  ```python
  BATCH_SIZE = 6
  batches = []
  for i in range(0, len(all_prompts), BATCH_SIZE):
      batches.append({
          'batch_id': f'batch_{i//BATCH_SIZE}',
          'prompts': all_prompts[i:i+BATCH_SIZE]
      })
  return {'batches': batches, 'total_batches': len(batches)}
  ```
- **Критична Точка:** Розмір батчу 6 оптимізовано для SD 3.5 Large (GPU memory)

**ec2-sd35-control** (`aws/lambda/ec2-sd35-control/`)
- **Призначення:** Управління EC2 GPU instance (start/stop/status)
- **Instance:** i-0a71aa2e72e9b9f75 (g6.2xlarge з NVIDIA L4 24GB)
- **Actions:**
  - `start` → Запуск instance + очікування API ready
  - `stop` → Зупинка instance + очікування повної зупинки
  - `status` → Перевірка стану
- **Архітектурне Рішення:** DynamoDB Optimistic Locking (EC2InstanceLocks table)
  ```python
  # Acquire lock before start
  table.update_item(
      Key={'instance_id': INSTANCE_ID},
      UpdateExpression='SET instance_state = :starting',
      ConditionExpression='instance_state = :stopped OR attribute_not_exists(instance_state)'
  )
  ```
- **WEEK 5.4 FIX:** Додано waiter для повної зупинки перед оновленням DynamoDB
  ```python
  waiter = ec2.get_waiter('instance_stopped')
  waiter.wait(InstanceIds=[INSTANCE_ID], WaiterConfig={'Delay': 15, 'MaxAttempts': 16})
  update_instance_state(INSTANCE_ID, 'stopped')
  ```
- **Критична Точка:** Race condition prevention - лише одна Lambda може стартувати EC2

**content-generate-images** (`aws/lambda/content-generate-images/`)
- **Призначення:** Генерація батчу зображень через EC2 API
- **API Endpoint:** `http://{ec2_ip}:5000/generate-batch`
- **Request:**
  ```json
  {
    "prompts": [
      {"id": "scene_1", "prompt": "A dark forest...", "channel_id": "UCabc"},
      // ... 5 more prompts
    ],
    "batch_size": 6,
    "steps": 28,
    "cfg_scale": 3.5
  }
  ```
- **Response:**
  ```json
  {
    "images": [
      {"id": "scene_1", "image_url": "s3://...", "generation_time": 3.2},
      // ... 5 more images
    ]
  }
  ```
- **Критична Точка:** SD 3.5 Large генерує 1024x1024 за ~3 секунди на L4 GPU

**distribute-images-to-channels** (`aws/lambda/distribute-images-to-channels/`)
- **Призначення:** Розподіл згенерованих зображень назад по каналам
- **Вхід:** `{ merged_images: [...], phase1_results: [...] }`
- **Логіка:**
  ```python
  # Створюємо мапінг image_id → S3 URL
  image_map = {img['id']: img['s3_url'] for img in merged_images}

  # Додаємо URLs до кожної сцени
  for channel in phase1_results:
      for scene in channel['narrative']['scenes']:
          scene['image_url'] = image_map.get(scene['scene_id'])

  return {'phase1_results_with_images': phase1_results}
  ```
- **Критична Точка:** Зберігає зв'язок між scene_id та згенерованим зображенням

**Критичні Архітектурні Рішення Phase 2:**

1. ✅ **Централізований батчінг** - 3.3x прискорення (90s vs 297s)
2. ✅ **MaxConcurrency: 3** - Оптимально для одного EC2 instance
3. ✅ **Batch size: 6** - Баланс між GPU memory та throughput
4. ✅ **Optimistic Locking** - Запобігає race conditions при старті EC2
5. ✅ **WEEK 5.4 FIX** - Waiter для повної зупинки EC2 (фікс bug lock state)
6. ✅ **S3 State Offloading** - Phase 1 results завантажуються з S3
7. ⚠️ **Single Point of Failure:** Один EC2 instance для всіх зображень
8. ⚠️ **Потенційна проблема:** InsufficientInstanceCapacity → потрібен SQS retry

---

### 1.3.3 SQS Retry System (Обробка EC2 Failures)

**Проблема:** AWS може повернути `InsufficientInstanceCapacity` при старті EC2

**Архітектурне Рішення:** Дворівнева стратегія retry

**Level 1: Fast Retries (Step Functions)**
```
StartEC2 fails
  ↓
Wait 10 seconds → Retry #1
  ↓ (failed)
Wait 20 seconds → Retry #2
  ↓ (failed)
Wait 40 seconds → Retry #3
  ↓ (failed)
→ Queue to SQS
```

**Level 2: Extended Retries (SQS + EventBridge)**
```
QueueForRetry → Додає повідомлення до SQS
  ↓
EventBridge (кожні 3 хвилини)
  ↓
retry-ec2-queue Lambda → Обробляє SQS повідомлення
  ↓ (якщо успішно)
Invoke Step Functions continuation (продовжує з Phase 2)
  ↓ (якщо failed після 20 спроб)
→ Dead Letter Queue (DLQ)
```

**Компоненти Системи:**

**SQS Queue: PendingImageGeneration**
- **URL:** `https://sqs.eu-central-1.amazonaws.com/599297130956/PendingImageGeneration`
- **Налаштування:**
  - VisibilityTimeout: 180 секунд (3 хвилини)
  - MessageRetentionPeriod: 3600 секунд (1 година)
  - MaxReceiveCount: 20 (після цього → DLQ)
- **Message Format:**
  ```json
  {
    "execution_arn": "arn:aws:states:...",
    "collected_prompts": { "all_image_prompts": [...] },
    "phase1_results": [...],
    "queued_at": "2025-12-02T00:30:00Z",
    "retry_count": 0
  }
  ```

**SQS DLQ: PendingImageGeneration-DLQ**
- **Призначення:** Збереження повідомлень після 20 невдалих спроб
- **MessageRetentionPeriod:** 1209600 секунд (14 днів)
- **Критична Точка:** Потребує моніторингу - повідомлення у DLQ = критичний failure

**EventBridge Rule: retry-ec2-every-3min**
- **Schedule:** `rate(3 minutes)`
- **Target:** Lambda `retry-ec2-queue`
- **Status:** ENABLED
- **Критична Точка:** Постійно працює - перевіряє SQS кожні 3 хвилини

**Lambda: queue-failed-ec2** (`aws/lambda/queue-failed-ec2/`)
- **Призначення:** Додає failed execution до SQS queue
- **Вхід:** `{ execution_arn, collected_prompts, phase1_results }`
- **Логіка:**
  ```python
  sqs.send_message(
      QueueUrl=QUEUE_URL,
      MessageBody=json.dumps({
          'execution_arn': execution_arn,
          'collected_prompts': collected_prompts,
          'phase1_results': phase1_results,
          'queued_at': datetime.utcnow().isoformat() + 'Z',
          'retry_count': 0
      })
  )
  ```

**Lambda: retry-ec2-queue** (`aws/lambda/retry-ec2-queue/`)
- **Призначення:** Обробка SQS queue кожні 3 хвилини
- **Trigger:** EventBridge (rate: 3 minutes)
- **Логіка:**
  ```python
  # Отримати повідомлення з SQS
  messages = sqs.receive_message(QueueUrl=QUEUE_URL, MaxNumberOfMessages=10)

  for message in messages:
      data = json.loads(message['Body'])

      # Спробувати запустити EC2
      try:
          ec2_control.start_instance()

          # Якщо успішно - продовжити Step Functions execution
          stepfunctions.start_execution(
              stateMachineArn=STATE_MACHINE_ARN,
              input=json.dumps({
                  'resume_from': 'GenerateAllImagesBatched',
                  'collected_prompts': data['collected_prompts'],
                  'phase1_results': data['phase1_results']
              })
          )

          # Видалити з queue
          sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=message['ReceiptHandle'])

      except InsufficientInstanceCapacity:
          # Залишити у queue - спробуємо через 3 хвилини
          pass
  ```
- **Критична Точка:** Автоматично продовжує workflow після успішного старту EC2

**Step Functions Integration:**

**CheckEC2Result (Choice State):**
```json
{
  "Type": "Choice",
  "Choices": [
    {
      "Variable": "$.ec2_result.state",
      "StringEquals": "running",
      "Next": "GenerateAllImagesBatched"
    },
    {
      "Variable": "$.ec2_result.state",
      "StringEquals": "queued_for_retry",
      "Next": "QueueForRetry"
    }
  ],
  "Default": "FailedEC2Start"
}
```

**QueueForRetry (Task State):**
```json
{
  "Type": "Task",
  "Resource": "arn:aws:lambda:eu-central-1:599297130956:function:queue-failed-ec2",
  "Parameters": {
    "execution_arn.$": "$$.Execution.Name",
    "collected_prompts.$": "$.collected_prompts",
    "phase1_results.$": "$.phase1_results"
  },
  "Next": "WaitForRetrySystem"
}
```

**WaitForRetrySystem (Succeed State):**
```json
{
  "Type": "Succeed",
  "Comment": "Execution queued - SQS retry system will resume workflow"
}
```

**Критичні Архітектурні Рішення SQS Retry:**

1. ✅ **Дворівнева стратегія** - Швидкі retry у Step Functions + довгі у SQS
2. ✅ **Automatic Resume** - Workflow продовжується автоматично після успіху
3. ✅ **Max 20 retries** - 1 година спроб (20 × 3 min)
4. ✅ **DLQ для моніторингу** - Зберігає критичні failures 14 днів
5. ✅ **EventBridge trigger** - Надійний scheduled retry (кожні 3 хв)
6. ⚠️ **Execution Status Confusion:** SUCCEEDED може означати "queued" (не фактичний success)
7. ⚠️ **Немає CloudWatch Alarms:** DLQ повідомлення не тригерять alerts
8. ⚠️ **Potential duplicate processing:** Якщо Lambda timeout - повідомлення може оброблятися двічі

---

### 1.3.4 PHASE 3: Audio & Save

**Логічний Потік:**
```
Phase3AudioAndSave (Map State, MaxConcurrency: 5)
  ├─ Iterator для кожного каналу:
  │   ├─ GenerateSSML → Програмна генерація SSML з plain text
  │   ├─ RouteTTSProvider (Choice) → Вибір Polly або ElevenLabs
  │   │   ├─ AudioPolly → AWS Polly Neural/Standard
  │   │   └─ AudioElevenLabs → ElevenLabs API
  │   ├─ SaveResult → DynamoDB GeneratedContent + S3 metadata
  │   └─ TriggerVideoAssembly → Async запуск збірки відео
  └─ Results: Масив збережених content_id
```

**Ключові Lambda Functions:**

**ssml-generator** (`aws/lambda/ssml-generator/`)
- **Призначення:** Програмна генерація SSML markup з plain text
- **TTS v2.0 Architecture:** Розділення content (LLM) від markup (code)
- **Вхід:**
  ```json
  {
    "narrative_text": "This is the opening scene...",
    "tts_provider": "polly",
    "voice_profile": "neural-standard",
    "channel_config": {
      "speaking_rate": "medium",
      "pitch": "medium",
      "pauses": {
        "sentence_end": 0.5,
        "paragraph_end": 1.0
      }
    }
  }
  ```
- **Логіка:**
  ```python
  # Додати prosody tags
  ssml = f'<speak><prosody rate="{rate}" pitch="{pitch}">'

  # Додати паузи між реченнями
  sentences = narrative_text.split('. ')
  for sentence in sentences:
      ssml += f'{sentence}.<break time="{pause_duration}s"/>'

  # Додати emphasis для важливих слів
  ssml = add_emphasis(ssml, emphasis_words)

  ssml += '</prosody></speak>'
  return {'ssml': ssml}
  ```
- **Вихід:** SSML-розмічений текст готовий для TTS
- **Критична Точка:** Використовує `ssml_validator.py` для перевірки валідності

**content-audio-polly** (`aws/lambda/content-audio-polly/`)
- **Призначення:** Генерація аудіо через AWS Polly
- **Підтримувані Engine:**
  - `neural` → Neural TTS (висока якість, дорожче)
  - `standard` → Standard TTS (нижча якість, дешевше)
- **API Call:**
  ```python
  response = polly.synthesize_speech(
      Text=ssml_text,
      TextType='ssml',
      OutputFormat='mp3',
      VoiceId=voice_id,
      Engine=engine,
      SampleRate='24000'
  )

  # Завантажити аудіо у S3
  s3.upload_fileobj(
      response['AudioStream'],
      'youtube-automation-audio-files',
      f'{user_id}/{channel_id}/{scene_id}.mp3'
  )
  ```
- **Cost Tracking:**
  ```python
  character_count = len(ssml_text)
  cost = calculate_polly_cost(character_count, engine)

  save_cost_record(
      user_id=user_id,
      service='polly',
      operation='synthesize_speech',
      cost=cost,
      metadata={'characters': character_count, 'engine': engine}
  )
  ```
- **Критична Точка:** Neural engine ~4x дорожче за Standard

**content-audio-elevenlabs** (`aws/lambda/content-audio-elevenlabs/`)
- **Призначення:** Генерація аудіо через ElevenLabs API
- **API Endpoint:** `https://api.elevenlabs.io/v1/text-to-speech/{voice_id}`
- **Переваги:**
  - Вища якість голосу (більш природній)
  - Емоційна виразність
- **Недоліки:**
  - Дорожче (~10x vs Polly Standard)
  - Залежність від зовнішнього API
- **Request:**
  ```python
  response = requests.post(
      f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}',
      headers={'xi-api-key': ELEVENLABS_API_KEY},
      json={
          'text': plain_text,  # ElevenLabs не підтримує SSML
          'model_id': 'eleven_monolingual_v1',
          'voice_settings': {
              'stability': 0.5,
              'similarity_boost': 0.75
          }
      }
  )
  ```
- **Критична Точка:** Не підтримує SSML - використовує plain text

**RouteTTSProvider (Choice State):**
```json
{
  "Type": "Choice",
  "Choices": [
    {
      "Variable": "$.channel_config.tts_provider",
      "StringEquals": "elevenlabs",
      "Next": "AudioElevenLabs"
    },
    {
      "Variable": "$.channel_config.tts_provider",
      "StringEquals": "polly",
      "Next": "AudioPolly"
    }
  ],
  "Default": "AudioPolly"
}
```

**content-save-result** (`aws/lambda/content-save-result/`)
- **Призначення:** Збереження готового контенту у DynamoDB
- **DynamoDB Table:** GeneratedContent
- **Item Structure:**
  ```python
  {
      'content_id': f'{timestamp}_{random_suffix}',  # PK
      'user_id': user_id,
      'channel_id': channel_id,
      'created_at': datetime.utcnow().isoformat() + 'Z',
      'title': narrative['title'],
      'narrative': {
          'scenes': [
              {
                  'scene_id': 'scene_1',
                  'narrative_text': '...',
                  'image_url': 's3://...',
                  'audio_url': 's3://...'
              },
              # ... 4 more scenes
          ]
      },
      'metadata': {
          'total_duration': 180,  # seconds
          'tts_provider': 'polly',
          'voice_id': 'Joanna',
          'image_count': 5
      },
      'status': 'generated',  # generated → video_assembly_pending → completed
      'costs': {
          'narrative_generation': 0.002,
          'image_generation': 0.15,
          'audio_generation': 0.008,
          'total': 0.16
      }
  }
  ```
- **Також зберігає у S3:** `s3://youtube-automation-data-grucia/content/{user_id}/{content_id}.json`
- **Критична Точка:** Додає записи у 3 GSI indices для швидких запитів

**Критичні Архітектурні Рішення Phase 3:**

1. ✅ **TTS v2.0** - Розділення content (LLM) від markup (code) = 15-20% економія
2. ✅ **Multi-Provider Support** - Polly або ElevenLabs (flexibility + cost optimization)
3. ✅ **SSML Validation** - Перевірка перед відправкою до Polly (менше errors)
4. ✅ **Cost Tracking** - Кожна операція записує вартість у CostTracking table
5. ✅ **MaxConcurrency: 5** - Баланс між швидкістю та API rate limits
6. ⚠️ **ElevenLabs не підтримує SSML:** Plain text тільки (менше контролю)
7. ⚠️ **Polly Character Limits:** 3000 chars для Standard, 1500 для Neural
8. ⚠️ **Немає retry logic:** Якщо Polly/ElevenLabs API fails → весь workflow fails

---

## 1.4 Video Assembly System (Hybrid Lambda/ECS)

### Архітектурна Проблема

**Lambda Timeout:** 15 хвилин максимум
**Проблема:** Відео >15 хвилин не можна зібрати у Lambda

**Рішення:** Гібридна архітектура з автоматичним вибором

### Логіка Вибору

```python
def select_compute_platform(total_duration_seconds):
    if total_duration_seconds <= 900:  # 15 minutes
        return 'lambda'  # Fast, cheap ($0.002)
    else:
        return 'ecs'     # Slow, expensive ($0.40)
```

### Lambda Path (≤15 minutes)

**Lambda: content-video-assembly** (`aws/lambda/content-video-assembly/`)
- **Runtime:** Python 3.12
- **Memory:** 3008 MB (1.77 vCPU)
- **Timeout:** 900 seconds (15 min)
- **Layers:**
  - FFmpeg layer (бінарний)
  - MoviePy layer (Python library)

**Процес:**
```python
# 1. Завантажити контент з DynamoDB
content = dynamodb.get_item(
    TableName='GeneratedContent',
    Key={'content_id': content_id}
)

# 2. Завантажити всі assets з S3 (images + audio)
for scene in content['narrative']['scenes']:
    download_from_s3(scene['image_url'], f'/tmp/{scene["scene_id"]}.png')
    download_from_s3(scene['audio_url'], f'/tmp/{scene["scene_id"]}.mp3')

# 3. Створити відеокліпи з Ken Burns zoom effect
clips = []
for i, scene in enumerate(content['narrative']['scenes']):
    # Ken Burns zoom
    image_clip = ImageClip(f'/tmp/{scene["scene_id"]}.png', duration=scene_duration)
    zoomed = image_clip.fx(zoom_in_out, zoom_ratio=1.1)

    # Додати аудіо
    audio_clip = AudioFileClip(f'/tmp/{scene["scene_id"]}.mp3')
    video_clip = zoomed.set_audio(audio_clip)

    # Transition між сценами
    if i > 0:
        video_clip = video_clip.crossfadein(0.5)

    clips.append(video_clip)

# 4. Конкатенація всіх кліпів
final_video = concatenate_videoclips(clips, method='compose')

# 5. Рендеринг
final_video.write_videofile(
    '/tmp/final_video.mp4',
    fps=24,
    codec='libx264',
    audio_codec='aac',
    preset='medium',
    threads=2
)

# 6. Завантажити у S3
s3.upload_file(
    '/tmp/final_video.mp4',
    'youtube-automation-final-videos',
    f'{user_id}/{content_id}.mp4'
)

# 7. Оновити DynamoDB
dynamodb.update_item(
    TableName='GeneratedContent',
    Key={'content_id': content_id},
    UpdateExpression='SET #status = :completed, video_url = :url',
    ExpressionAttributeNames={'#status': 'status'},
    ExpressionAttributeValues={
        ':completed': 'completed',
        ':url': f's3://youtube-automation-final-videos/{user_id}/{content_id}.mp4'
    }
)
```

**Переваги:**
- Швидко: 2-5 хвилин для 10-хвилинного відео
- Дешево: ~$0.002 за відео
- Просто: Один Lambda invoke

**Недоліки:**
- 15-хвилинний hard limit
- 512MB /tmp storage limit
- Обмежені CPU ресурси

### ECS Fargate Path (>15 minutes)

**ECS Task Definition:** `video-assembly-task`
- **CPU:** 4096 (4 vCPU)
- **Memory:** 8192 MB (8 GB)
- **Image:** Custom Docker image з FFmpeg + MoviePy + Python
- **Task Role:** Доступ до S3 + DynamoDB

**Trigger Lambda: start-ecs-video-assembly** (`aws/lambda/start-ecs-video-assembly/`)
```python
# Запустити ECS task
ecs.run_task(
    cluster='video-assembly-cluster',
    taskDefinition='video-assembly-task',
    launchType='FARGATE',
    networkConfiguration={
        'awsvpcConfiguration': {
            'subnets': ['subnet-abc123'],
            'securityGroups': ['sg-xyz789'],
            'assignPublicIp': 'ENABLED'
        }
    },
    overrides={
        'containerOverrides': [{
            'name': 'video-assembly-container',
            'environment': [
                {'name': 'CONTENT_ID', 'value': content_id},
                {'name': 'USER_ID', 'value': user_id}
            ]
        }]
    }
)
```

**ECS Container Script:**
```python
#!/usr/bin/env python3
import os
import boto3
from moviepy.editor import *

content_id = os.environ['CONTENT_ID']
user_id = os.environ['USER_ID']

# Той самий код що у Lambda, але без timeout обмежень
# Може працювати годинами якщо потрібно
```

**Переваги:**
- Немає timeout (може працювати годинами)
- Більше CPU/RAM (4 vCPU, 8 GB)
- Більше storage (20 GB ephemeral)

**Недоліки:**
- Повільний старт: 2-3 хвилини на запуск task
- Дорого: ~$0.40 за task (навіть якщо відео 16 хвилин)
- Складніше: ECS cluster + networking + monitoring

### Auto-Selection Logic

**Lambda: trigger-video-assembly** (`aws/lambda/trigger-video-assembly/`)
```python
def lambda_handler(event, context):
    content_id = event['content_id']

    # Отримати контент з DynamoDB
    content = get_content(content_id)

    # Підрахувати загальну тривалість
    total_duration = sum(scene['audio_duration'] for scene in content['narrative']['scenes'])

    # Вибрати платформу
    if total_duration <= 900:  # 15 minutes
        # Invoke Lambda
        lambda_client.invoke(
            FunctionName='content-video-assembly',
            InvocationType='Event',  # Async
            Payload=json.dumps({'content_id': content_id})
        )
        return {'platform': 'lambda', 'estimated_cost': 0.002}
    else:
        # Start ECS task
        ecs.run_task(...)
        return {'platform': 'ecs', 'estimated_cost': 0.40}
```

**Критичні Архітектурні Рішення Video Assembly:**

1. ✅ **Hybrid approach** - Автоматичний вибір найкращої платформи
2. ✅ **Cost optimization** - Lambda для 95% випадків (дешевше)
3. ✅ **Ken Burns effect** - Професійний вигляд статичних зображень
4. ✅ **Transitions** - Плавні переходи між сценами
5. ✅ **Async invocation** - Не блокує основний workflow
6. ⚠️ **Немає progress tracking:** Користувач не бачить % готовності
7. ⚠️ **Немає retry logic:** Якщо FFmpeg fails → manual re-trigger
8. ⚠️ **512MB /tmp limit у Lambda:** Може бути проблема для 4K зображень

---

## 1.5 Database Architecture (DynamoDB)

### 10 Tables Schema

**1. ChannelConfigs** (Конфігурація каналів)
```
Partition Key: user_id + channel_id (composite)
Attributes:
  - channel_name (String)
  - is_active (Boolean)
  - genre (String): "horror", "history", "science", etc.
  - tts_provider (String): "polly" або "elevenlabs"
  - voice_id (String): Polly voice або ElevenLabs voice
  - voice_profile (String): "neural" або "standard"
  - target_duration (Number): Бажана тривалість відео (секунди)
  - upload_schedule (Map): Час публікації
  - created_at (String): ISO timestamp
  - updated_at (String): ISO timestamp

GSI: user_id-is_active-index
  - PK: user_id
  - SK: is_active
  - Призначення: Швидко отримати всі активні канали користувача
```

**2. GeneratedContent** (Згенерований контент)
```
Partition Key: content_id (timestamp-based unique ID)
Attributes:
  - user_id (String)
  - channel_id (String)
  - created_at (String): ISO timestamp
  - title (String)
  - narrative (Map):
      - scenes (List):
          - scene_id (String)
          - narrative_text (String)
          - image_url (String): S3 URL
          - audio_url (String): S3 URL
          - audio_duration (Number)
  - video_url (String): S3 URL (після assembly)
  - status (String): "generated" → "video_assembly_pending" → "completed"
  - metadata (Map):
      - total_duration (Number)
      - tts_provider (String)
      - voice_id (String)
      - image_count (Number)
  - costs (Map):
      - narrative_generation (Number)
      - image_generation (Number)
      - audio_generation (Number)
      - video_assembly (Number)
      - total (Number)

GSI #1: user_id-created_at-index
  - PK: user_id
  - SK: created_at
  - Призначення: Мультитенант запити - весь контент користувача

GSI #2: channel_id-created_at-index
  - PK: channel_id
  - SK: created_at
  - Призначення: Контент конкретного каналу

GSI #3: content_id-created_at-index
  - PK: content_id
  - SK: created_at
  - Призначення: Video assembly lookup (WEEK 5.3 FIX)
```

**3. CostTracking** (Відстеження витрат)
```
Partition Key: user_id + date + timestamp (composite)
Attributes:
  - user_id (String)
  - date (String): "2025-12-02"
  - timestamp (String): ISO timestamp
  - service (String): "openai", "polly", "elevenlabs", "ec2", "lambda", etc.
  - operation (String): "gpt-4o", "synthesize_speech", "run_instance", etc.
  - cost (Number): Decimal вартість у USD
  - metadata (Map):
      - content_id (String)
      - channel_id (String)
      - details (Map): Специфічні деталі операції

GSI: user_id-date-index
  - PK: user_id
  - SK: date
  - Призначення: Агрегація витрат по дням
```

**4. EC2InstanceLocks** (Блокування EC2)
```
Partition Key: instance_id
Attributes:
  - instance_id (String): "i-0a71aa2e72e9b9f75"
  - instance_state (String): "stopped", "starting", "running", "stopping"
  - updated_at (String): ISO timestamp
  - locked_by (String): Lambda execution ARN (опціонально)

Призначення: Optimistic locking для запобігання race conditions
```

**5-10. Template Tables** (Промпти для AI)
```
ThemeTemplates:
  - template_id (PK)
  - user_id (GSI)
  - genre (String)
  - system_prompt (String)
  - examples (List)

NarrativeTemplates:
  - template_id (PK)
  - user_id (GSI)
  - narrative_structure (Map)
  - tone (String)

[Аналогічно для TTSTemplates, ImageGenerationTemplates,
 CTATemplates, DescriptionTemplates, VideoEditingTemplates]
```

### Multi-Tenant Strategy

**Ізоляція даних:**
1. ✅ Всі таблиці включають `user_id`
2. ✅ GSI індекси дозволяють ефективні запити по `user_id`
3. ✅ Composite keys запобігають колізіям (user_id + channel_id)

**Query Patterns:**
```python
# Отримати активні канали користувача
response = table.query(
    IndexName='user_id-is_active-index',
    KeyConditionExpression='user_id = :user_id AND is_active = :true'
)

# Отримати весь контент користувача за останній місяць
response = table.query(
    IndexName='user_id-created_at-index',
    KeyConditionExpression='user_id = :user_id AND created_at > :last_month'
)

# Отримати денні витрати
response = table.query(
    IndexName='user_id-date-index',
    KeyConditionExpression='user_id = :user_id AND #date = :today',
    ExpressionAttributeNames={'#date': 'date'}
)
```

**Критичні Точки DynamoDB:**
1. ✅ **GSI індекси** - Швидкі запити без scan (економія RCU)
2. ✅ **Composite keys** - Уникнення колізій між користувачами
3. ✅ **ISO timestamps** - Лексикографічне сортування
4. ✅ **Optimistic locking** - ConditionalUpdate для EC2InstanceLocks
5. ⚠️ **Немає TTL:** Старі дані ніколи не видаляються (зростання коштів)
6. ⚠️ **Немає DynamoDB Streams:** Немає реакції на зміни даних
7. ⚠️ **On-Demand pricing:** Може бути дорого при high throughput

---

## 1.6 S3 Storage Architecture

### 4 Buckets Strategy

**1. youtube-automation-audio-files**
```
Призначення: Аудіо файли (MP3)
Structure:
  {user_id}/
    {channel_id}/
      {scene_id}.mp3

Lifecycle Policy:
  - Transition to Glacier after 90 days
  - Delete after 365 days

CORS Configuration:
  - Allowed Origins: https://n8n-creator.space
  - Allowed Methods: GET, HEAD
  - Allowed Headers: *

Security:
  - Presigned URLs (15-minute expiration)
  - Private bucket (no public access)
```

**2. youtube-automation-images**
```
Призначення: AI-згенеровані зображення (PNG)
Structure:
  {user_id}/
    {channel_id}/
      {scene_id}.png

Metadata:
  - x-amz-meta-prompt: Оригінальний SD prompt
  - x-amz-meta-model: "stable-diffusion-3.5-large"
  - x-amz-meta-generation-time: Час генерації (секунди)

Lifecycle Policy:
  - Transition to IA after 30 days
  - Delete after 180 days
```

**3. youtube-automation-final-videos**
```
Призначення: Готові відео (MP4)
Structure:
  {user_id}/
    {content_id}.mp4

Storage Class: Standard (часті reads)

Lifecycle Policy:
  - Transition to IA after 60 days
  - Transition to Glacier after 180 days
  - Never delete (permanent storage)

Presigned URLs:
  - 24-hour expiration (для YouTube upload)
```

**4. youtube-automation-data-grucia**
```
Призначення: Метадані та state offloading
Structure:
  phase1_results/
    {user_id}/
      {channel_id}.json

  content/
    {user_id}/
      {content_id}.json

  step_functions_state/
    {execution_id}/
      phase1.json
      phase2.json
      phase3.json

Lifecycle Policy:
  - Transition to IA after 7 days
  - Delete after 30 days (тимчасові дані)
```

### S3 State Offloading Pattern

**Проблема:** Step Functions payload limit = 256KB

**Рішення:**
```python
# Замість:
return {'phase1_results': [huge_array]}  # ❌ Може перевищити 256KB

# Робимо:
s3.put_object(
    Bucket='youtube-automation-data-grucia',
    Key=f'phase1_results/{user_id}/execution_{timestamp}.json',
    Body=json.dumps(phase1_results)
)
return {'phase1_results_s3_uri': f's3://youtube-automation-data-grucia/...'}  # ✅ Лише URI
```

**Переваги:**
- ✅ Обходить 256KB limit
- ✅ Зберігає повну історію executions
- ✅ Можна дебажити failures (дані у S3)

**Недоліки:**
- ⚠️ Додаткові S3 API calls (вартість + латентність)
- ⚠️ Потрібно очищення старих даних (lifecycle policy)

### CSP Security для S3

**Проблема:** Presigned URLs використовують `s3.amazonaws.com` (глобальний) та `s3.eu-central-1.amazonaws.com` (регіональний)

**Рішення:** Дозволити обидва формати у CSP
```nginx
Content-Security-Policy: "
  media-src 'self'
    https://youtube-automation-audio-files.s3.amazonaws.com
    https://youtube-automation-audio-files.s3.eu-central-1.amazonaws.com
    https://youtube-automation-images.s3.amazonaws.com
    https://youtube-automation-images.s3.eu-central-1.amazonaws.com
    https://youtube-automation-final-videos.s3.amazonaws.com
    https://youtube-automation-final-videos.s3.eu-central-1.amazonaws.com
    https://s3.amazonaws.com
    https://s3.eu-central-1.amazonaws.com
    blob:;
"
```

**Критичні Точки S3:**
1. ✅ **Lifecycle policies** - Автоматичне очищення старих даних
2. ✅ **Presigned URLs** - Безпечний тимчасовий доступ
3. ✅ **CORS configuration** - Frontend може завантажувати media
4. ✅ **CSP both formats** - WEEK 5.1 FIX (підтримка обох URL форматів)
5. ⚠️ **Немає versioning:** Перезапис файлів без історії
6. ⚠️ **Немає encryption at rest:** Дані не зашифровані (можна додати SSE)

---

## 1.7 Frontend Architecture (Web Admin)

### Tech Stack

**Static HTML/CSS/JS** (без фреймворків)
```
index.html          - Landing page + login
dashboard.html      - Monitoring & executions
channels.html       - Channel management
content.html        - Generated content browser
costs.html          - Cost analytics
prompts-editor.html - AI prompts configuration
documentation.html  - System docs
```

**Unified Navigation** (`css/unified-navigation.css` + `js/navigation.js`)
- Consistent header across all pages
- Active page highlighting
- Responsive design

**Authentication** (`js/auth.js`)
- Cognito SDK integration
- Cookie-based session (5-cookie split)
- Auto-refresh tokens
- Protected routes (redirect to login)

### Security Architecture

**HTTPS Only**
```
Nginx configuration:
  - Redirect HTTP → HTTPS
  - Force TLS 1.2+
  - Strong ciphers only
```

**Content Security Policy (CSP)**
```nginx
add_header Content-Security-Policy "
  default-src 'self';
  script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com;
  style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
  font-src 'self' https://fonts.gstatic.com;
  img-src 'self' data: https://*.s3.amazonaws.com https://*.s3.eu-central-1.amazonaws.com;
  media-src 'self' https://*.s3.amazonaws.com https://*.s3.eu-central-1.amazonaws.com blob:;
  connect-src 'self' https://cognito-idp.eu-central-1.amazonaws.com;
  frame-ancestors 'none';
  base-uri 'self';
  form-action 'self';
" always;
```

**Other Security Headers**
```nginx
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
```

**Cookie Security**
```javascript
// Set cookies with security flags
document.cookie = `auth_token_${i}=${chunk}; Secure; HttpOnly; SameSite=Strict; Max-Age=3600`;
```

### Dashboard Monitoring System

**Real-time Execution Monitoring** (`dashboard.html`)
```javascript
// Poll Step Functions every 30 seconds
setInterval(async () => {
    const executions = await listExecutions();
    updateExecutionTable(executions);
}, 30000);

// Show execution details
async function showExecutionDetails(executionArn) {
    const history = await getExecutionHistory(executionArn);
    visualizeWorkflow(history);
}
```

**Features:**
- ✅ Execution status (RUNNING, SUCCEEDED, FAILED)
- ✅ Duration tracking
- ✅ Error messages
- ✅ Output preview
- ✅ Execution history visualization

**Cost Analytics** (`costs.html`)
```javascript
// Aggregate costs by service
const costsByService = aggregateCosts(costRecords, 'service');
renderPieChart(costsByService);

// Daily cost trend
const dailyCosts = aggregateCosts(costRecords, 'date');
renderLineChart(dailyCosts);
```

**Features:**
- ✅ Total costs по сервісах (OpenAI, Polly, EC2, Lambda)
- ✅ Денні тренди
- ✅ Per-channel breakdown
- ✅ Cost forecasting

**Content Browser** (`content.html`)
```javascript
// Load user's content
const content = await loadContent(userId);

// Filter by channel, date, status
const filtered = filterContent(content, {
    channel_id: selectedChannel,
    created_at_from: startDate,
    status: 'completed'
});

// Preview video/audio
function previewContent(contentId) {
    const videoUrl = generatePresignedUrl(content.video_url);
    videoPlayer.src = videoUrl;
}
```

**Features:**
- ✅ Фільтрація по каналу, даті, статусу
- ✅ Preview audio/video
- ✅ Download links
- ✅ Metadata display (duration, costs, TTS provider)

**Критичні Точки Frontend:**
1. ✅ **Static files** - Швидкий CDN delivery
2. ✅ **Security headers** - CSP + XSS protection
3. ✅ **Cookie-based auth** - Workaround для великих JWT
4. ✅ **Real-time monitoring** - 30s polling
5. ⚠️ **unsafe-inline CSP:** Потенційна XSS вразливість (потребує refactoring)
6. ⚠️ **No SRI (Subresource Integrity):** CDN dependencies не верифіковані
7. ⚠️ **Client-side filtering:** Може бути повільно для великих datasets

---

## 1.8 Cost Tracking System

### Architecture

**Two-level Tracking:**
1. **Real-time tracking** - Кожна Lambda записує витрати після операції
2. **Dashboard aggregation** - Frontend запитує та візуалізує

### Cost Calculation Logic

**OpenAI (GPT-4o / GPT-4o-mini)**
```python
# Pricing (per 1M tokens)
GPT_4O_INPUT = 2.50      # $2.50 per 1M input tokens
GPT_4O_OUTPUT = 10.00    # $10.00 per 1M output tokens
GPT_4O_MINI_INPUT = 0.15 # $0.15 per 1M input tokens
GPT_4O_MINI_OUTPUT = 0.60 # $0.60 per 1M output tokens

def calculate_openai_cost(model, input_tokens, output_tokens):
    if model == 'gpt-4o':
        input_cost = (input_tokens / 1_000_000) * GPT_4O_INPUT
        output_cost = (output_tokens / 1_000_000) * GPT_4O_OUTPUT
    elif model == 'gpt-4o-mini':
        input_cost = (input_tokens / 1_000_000) * GPT_4O_MINI_INPUT
        output_cost = (output_tokens / 1_000_000) * GPT_4O_MINI_OUTPUT

    return input_cost + output_cost
```

**AWS Polly**
```python
# Pricing (per 1M characters)
POLLY_NEURAL = 16.00   # $16 per 1M chars
POLLY_STANDARD = 4.00  # $4 per 1M chars

def calculate_polly_cost(character_count, engine):
    if engine == 'neural':
        return (character_count / 1_000_000) * POLLY_NEURAL
    else:
        return (character_count / 1_000_000) * POLLY_STANDARD
```

**ElevenLabs**
```python
# Pricing (per 1K characters)
ELEVENLABS_RATE = 0.30  # $0.30 per 1K chars

def calculate_elevenlabs_cost(character_count):
    return (character_count / 1_000) * ELEVENLABS_RATE
```

**EC2 GPU (g6.2xlarge)**
```python
# Pricing
EC2_HOURLY = 1.006  # $1.006 per hour

def calculate_ec2_cost(runtime_seconds):
    runtime_hours = runtime_seconds / 3600
    return runtime_hours * EC2_HOURLY
```

**Lambda**
```python
# Pricing
LAMBDA_REQUESTS = 0.20 / 1_000_000  # $0.20 per 1M requests
LAMBDA_DURATION = 0.0000166667      # $0.0000166667 per GB-second

def calculate_lambda_cost(invocations, memory_mb, duration_ms):
    request_cost = invocations * LAMBDA_REQUESTS

    gb_seconds = (memory_mb / 1024) * (duration_ms / 1000)
    duration_cost = gb_seconds * LAMBDA_DURATION

    return request_cost + duration_cost
```

### Cost Recording Pattern

**Example: content-narrative Lambda**
```python
# 1. Виклик OpenAI API
response = openai.ChatCompletion.create(
    model='gpt-4o-mini',
    messages=[...],
    response_format={'type': 'json_object'}
)

# 2. Обчислити вартість
input_tokens = response.usage.prompt_tokens
output_tokens = response.usage.completion_tokens
cost = calculate_openai_cost('gpt-4o-mini', input_tokens, output_tokens)

# 3. Записати у DynamoDB
dynamodb.put_item(
    TableName='CostTracking',
    Item={
        'user_id': user_id,
        'date': datetime.utcnow().strftime('%Y-%m-%d'),
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'service': 'openai',
        'operation': 'gpt-4o-mini',
        'cost': Decimal(str(cost)),
        'metadata': {
            'content_id': content_id,
            'channel_id': channel_id,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens
        }
    }
)
```

### Dashboard Aggregation

**Lambda: dashboard-costs** (`aws/lambda/dashboard-costs/`)
```python
def lambda_handler(event, context):
    user_id = event['user_id']
    date_from = event.get('date_from', '2025-12-01')
    date_to = event.get('date_to', '2025-12-31')

    # Query CostTracking table
    response = table.query(
        IndexName='user_id-date-index',
        KeyConditionExpression='user_id = :user_id AND #date BETWEEN :from AND :to',
        ExpressionAttributeNames={'#date': 'date'},
        ExpressionAttributeValues={
            ':user_id': user_id,
            ':from': date_from,
            ':to': date_to
        }
    )

    # Aggregate by service
    costs_by_service = {}
    for item in response['Items']:
        service = item['service']
        cost = float(item['cost'])
        costs_by_service[service] = costs_by_service.get(service, 0) + cost

    # Aggregate by day
    costs_by_day = {}
    for item in response['Items']:
        date = item['date']
        cost = float(item['cost'])
        costs_by_day[date] = costs_by_day.get(date, 0) + cost

    return {
        'total_cost': sum(costs_by_service.values()),
        'costs_by_service': costs_by_service,
        'costs_by_day': costs_by_day
    }
```

**Критичні Точки Cost Tracking:**
1. ✅ **Real-time recording** - Точність на рівні кожної операції
2. ✅ **Multi-service tracking** - OpenAI, Polly, ElevenLabs, EC2, Lambda
3. ✅ **GSI для агрегації** - Швидкі запити по user_id + date
4. ✅ **Decimal precision** - DynamoDB Decimal type для точності
5. ⚠️ **Немає billing alarms:** Користувач не отримує alerts при high costs
6. ⚠️ **Немає budget enforcement:** Система не зупиняє генерацію при перевищенні ліміту
7. ⚠️ **Manual price updates:** Якщо AWS/OpenAI змінять ціни → код треба оновити

---

# 2. ІДЕАЛЬНА АРХІТЕКТУРА

## 2.1 Принципи Ідеальної Архітектури

### 2.1.1 Cloud-Native Best Practices

**Serverless First**
- ✅ Використовувати managed services де можливо
- ✅ Lambda для stateless обробки
- ✅ Step Functions для orchestration
- ✅ Мінімізувати EC2 (лише для GPU workloads)

**Event-Driven Architecture**
- ✅ Асинхронна комунікація між компонентами
- ✅ EventBridge для scheduling та triggers
- ✅ SQS для decoupling та retry logic
- ✅ SNS для notifications

**Multi-Tenant Isolation**
- ✅ Повна ізоляція даних на рівні partition keys
- ✅ IAM policies per tenant (якщо потрібно)
- ✅ Rate limiting per tenant
- ✅ Cost allocation tags

**Observability**
- ✅ Structured logging (JSON format)
- ✅ Distributed tracing (X-Ray)
- ✅ CloudWatch metrics для всіх компонентів
- ✅ Alarms для критичних failures

**Security by Design**
- ✅ Least privilege IAM policies
- ✅ Encryption at rest (S3, DynamoDB)
- ✅ Encryption in transit (TLS 1.3)
- ✅ Secrets rotation (Secrets Manager)
- ✅ Security scanning (automated)

**Cost Optimization**
- ✅ Right-sizing resources
- ✅ Spot instances для non-critical workloads
- ✅ S3 lifecycle policies
- ✅ Reserved capacity для predictable loads
- ✅ Auto-scaling всіх компонентів

### 2.1.2 Ідеальна Workflow Architecture

**3-Phase Design (залишається)**
```
PHASE 1: Content Generation (parallel, per-channel)
PHASE 2: Resource Generation (batched, centralized)
PHASE 3: Assembly & Save (parallel, per-channel)
```

**Покращення:**
1. **Phase 1: Додати кешування**
   - Кеш схожих queries до OpenAI (DynamoDB TTL cache)
   - Уникнути дублювання тем/нарративів

2. **Phase 2: Multi-GPU Support**
   - Горизонтальне масштабування (2-3 EC2 instances)
   - Розподілення батчів між instances
   - Auto-scaling based on queue depth

3. **Phase 3: Async Video Assembly**
   - Не блокувати Phase 3 на video assembly
   - SQS queue для video jobs
   - Окремий worker pool (Lambda або ECS)

---

## 2.2 Ідеальна Data Architecture

### 2.2.1 DynamoDB Improvements

**Додати TTL (Time-To-Live)**
```
GeneratedContent:
  - ttl_expiration (Number): Unix timestamp
  - Автоматичне видалення після 90 днів (configurable)

CostTracking:
  - ttl_expiration: Автоматичне видалення після 365 днів
```

**Додати DynamoDB Streams**
```
GeneratedContent Stream → Lambda trigger
  - Автоматично тригерити video assembly
  - Відправляти notifications (SNS)
  - Оновлювати analytics tables

CostTracking Stream → Lambda trigger
  - Real-time cost alarms
  - Budget enforcement
  - Fraud detection
```

**Point-in-Time Recovery (PITR)**
```
Всі production tables:
  - Enable PITR (backup останніх 35 днів)
  - Restore до будь-якого моменту часу
  - Захист від accidental deletes
```

**Global Tables (для multi-region)**
```
Якщо потрібна низька латентність з EU + US:
  - GeneratedContent → Global table (eu-central-1 + us-east-1)
  - Автоматична реплікація
  - Multi-region availability
```

### 2.2.2 S3 Improvements

**Versioning**
```
Всі buckets:
  - Enable versioning
  - Захист від accidental overwrites
  - Можливість rollback
```

**Encryption at Rest**
```
Всі buckets:
  - SSE-S3 (мінімум) або SSE-KMS (краще)
  - Automatic encryption всіх об'єктів
```

**S3 Intelligent-Tiering**
```
Замість lifecycle policies:
  - Automatic transition між tiers
  - Економія без manual rules
```

**S3 Event Notifications**
```
youtube-automation-final-videos:
  - Event: s3:ObjectCreated:*
  - Target: SNS topic → Email/Telegram notification
  - "Your video is ready!"
```

**CloudFront CDN**
```
youtube-automation-final-videos:
  - CloudFront distribution
  - Edge caching (низька латентність)
  - Custom domain (videos.yoursite.com)
```

---

## 2.3 Ідеальна Security Architecture

### 2.3.1 Enhanced Authentication

**Cognito Advanced Security**
```
User Pool:
  - Enable Advanced Security Features
  - Risk-based adaptive authentication
  - Compromised credentials detection
  - Account takeover protection
```

**MFA (Multi-Factor Authentication)**
```
Required для production:
  - SMS MFA або TOTP
  - Обов'язково для admin users
  - Опціонально для regular users
```

**Session Management**
```
Замість cookie splitting:
  - Server-side sessions (DynamoDB)
  - Short-lived access tokens (15 min)
  - Refresh tokens (30 днів)
  - Token rotation on refresh
```

### 2.3.2 IAM Best Practices

**Least Privilege Policies**
```json
// Замість:
{
  "Effect": "Allow",
  "Action": "dynamodb:*",
  "Resource": "*"
}

// Використовувати:
{
  "Effect": "Allow",
  "Action": [
    "dynamodb:GetItem",
    "dynamodb:PutItem",
    "dynamodb:Query"
  ],
  "Resource": [
    "arn:aws:dynamodb:eu-central-1:599297130956:table/GeneratedContent",
    "arn:aws:dynamodb:eu-central-1:599297130956:table/GeneratedContent/index/*"
  ],
  "Condition": {
    "ForAllValues:StringEquals": {
      "dynamodb:LeadingKeys": ["${aws:PrincipalTag/user_id}"]
    }
  }
}
```

**Resource-based Policies**
```
S3 Buckets:
  - Deny public access (enforced)
  - Allow only specific IAM roles
  - Require encryption in transit
```

**Secrets Rotation**
```
AWS Secrets Manager:
  - OpenAI API key → Automatic rotation (30 днів)
  - ElevenLabs API key → Automatic rotation
  - Database credentials → Automatic rotation
```

### 2.3.3 Network Security

**VPC для EC2**
```
EC2 GPU instances:
  - Private subnet (no public IP)
  - NAT Gateway для outbound traffic
  - Security group: Тільки Lambda SG → EC2
```

**API Gateway для Lambda**
```
Замість Function URLs:
  - API Gateway REST API
  - Request validation
  - Rate limiting (per user_id)
  - WAF (Web Application Firewall)
```

**WAF Rules**
```
AWS WAF:
  - Rate limiting (1000 req/5min per IP)
  - SQL injection protection
  - XSS protection
  - Geo-blocking (якщо потрібно)
```

---

## 2.4 Ідеальна Monitoring & Observability

### 2.4.1 CloudWatch Enhancements

**Custom Metrics**
```python
# Приклад: content-narrative Lambda
cloudwatch.put_metric_data(
    Namespace='YouTubeAutomation/ContentGeneration',
    MetricData=[
        {
            'MetricName': 'NarrativeGenerationDuration',
            'Value': duration_ms,
            'Unit': 'Milliseconds',
            'Dimensions': [
                {'Name': 'ChannelId', 'Value': channel_id},
                {'Name': 'Genre', 'Value': genre}
            ]
        },
        {
            'MetricName': 'OpenAICost',
            'Value': cost,
            'Unit': 'None',
            'Dimensions': [
                {'Name': 'Model', 'Value': 'gpt-4o-mini'}
            ]
        }
    ]
)
```

**CloudWatch Alarms**
```
Critical Alarms:
  1. DLQ Messages > 0 → SNS → Telegram/Email
  2. Lambda Errors > 5% → SNS
  3. Step Functions Failures > 3/hour → SNS
  4. Daily Cost > $50 → SNS
  5. EC2 GPU Utilization < 20% → SNS (underutilization)

Warning Alarms:
  1. Lambda Duration > 80% of timeout
  2. DynamoDB Throttles > 10/hour
  3. S3 4xx Errors > 1%
```

**CloudWatch Dashboards**
```
Production Dashboard:
  - Step Functions execution rate (success/fail)
  - Lambda invocations & errors by function
  - DynamoDB consumed capacity (RCU/WCU)
  - S3 bandwidth usage
  - Daily cost trend
  - Queue depths (SQS)
  - EC2 GPU utilization
```

### 2.4.2 AWS X-Ray (Distributed Tracing)

**Enable X-Ray для всіх Lambda**
```python
# Додати X-Ray SDK
import aws_xray_sdk
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

patch_all()

@xray_recorder.capture('generate_narrative')
def generate_narrative(theme):
    # X-Ray автоматично trace:
    # - OpenAI API calls
    # - DynamoDB operations
    # - S3 uploads
    # - Child Lambda invocations
    ...
```

**Переваги:**
- ✅ End-to-end visibility (від trigger до video upload)
- ✅ Автоматичне виявлення bottlenecks
- ✅ Latency breakdown по компонентах
- ✅ Error root cause analysis

### 2.4.3 Structured Logging

**Замість print() використовувати structured logs:**
```python
import logging
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Замість:
print(f"Generated narrative for {channel_id}")

# Використовувати:
logger.info(json.dumps({
    'event': 'narrative_generated',
    'channel_id': channel_id,
    'user_id': user_id,
    'duration_ms': duration,
    'cost': cost,
    'model': 'gpt-4o-mini',
    'input_tokens': input_tokens,
    'output_tokens': output_tokens
}))
```

**Переваги:**
- ✅ CloudWatch Insights queries (швидкі фільтри)
- ✅ Automated alerting на patterns
- ✅ Easy export до analytics tools

**CloudWatch Insights Query Example:**
```sql
fields @timestamp, channel_id, cost, duration_ms
| filter event = "narrative_generated"
| stats avg(duration_ms) as avg_duration, sum(cost) as total_cost by channel_id
| sort total_cost desc
```

---

## 2.5 Ідеальна Reliability & Disaster Recovery

### 2.5.1 Failure Handling

**Lambda Dead Letter Queues (DLQ)**
```
Кожна Lambda:
  - OnFailure: SQS DLQ
  - Max retry: 2
  - DLQ message включає:
      - Original event
      - Error message
      - Stack trace
```

**Step Functions Error Handling**
```json
{
  "Type": "Task",
  "Resource": "arn:aws:lambda:...:function:content-narrative",
  "Retry": [
    {
      "ErrorEquals": ["States.Timeout"],
      "IntervalSeconds": 10,
      "MaxAttempts": 2,
      "BackoffRate": 2.0
    },
    {
      "ErrorEquals": ["OpenAIRateLimitError"],
      "IntervalSeconds": 60,
      "MaxAttempts": 3,
      "BackoffRate": 2.0
    }
  ],
  "Catch": [
    {
      "ErrorEquals": ["States.ALL"],
      "ResultPath": "$.error",
      "Next": "HandleError"
    }
  ]
}
```

**Circuit Breaker Pattern**
```python
# Для external APIs (OpenAI, ElevenLabs)
from pybreaker import CircuitBreaker

openai_breaker = CircuitBreaker(
    fail_max=5,           # Open після 5 failures
    timeout_duration=60   # Reset після 60 seconds
)

@openai_breaker
def call_openai(prompt):
    response = openai.ChatCompletion.create(...)
    return response
```

### 2.5.2 Disaster Recovery

**RTO/RPO Targets**
```
Recovery Time Objective (RTO): 4 години
Recovery Point Objective (RPO): 24 години

Означає:
  - Система має відновитися за 4 години після disaster
  - Максимальна втрата даних: останні 24 години
```

**Backup Strategy**
```
DynamoDB:
  - Point-in-Time Recovery (PITR): Enabled
  - Daily automated backups → S3
  - Cross-region backup replication

S3:
  - Versioning: Enabled
  - Cross-region replication (CRR):
      eu-central-1 → us-east-1
  - MFA Delete: Enabled (захист від accidental delete)

Lambda Code:
  - Version control: Git
  - Automated deployment from CI/CD
  - Rollback capability
```

**Disaster Recovery Plan**
```
Scenario: eu-central-1 region failure

1. DNS Failover (Route 53)
   - Switch to us-east-1 replica
   - TTL: 60 seconds

2. DynamoDB Global Tables
   - Automatic failover до us-east-1
   - Zero data loss (active-active replication)

3. Lambda Deployment
   - Deploy з Git до us-east-1
   - Automated via CI/CD

4. S3 Data
   - Cross-region replication (вже є копії)
   - CloudFront автоматично failover до другого origin

Recovery Time: ~2 години (в межах RTO 4 години)
```

---

## 2.6 Ідеальна CI/CD Pipeline

### 2.6.1 Infrastructure as Code

**Terraform (замість manual AWS Console)**
```hcl
# Приклад: DynamoDB table
resource "aws_dynamodb_table" "generated_content" {
  name           = "GeneratedContent"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "content_id"

  attribute {
    name = "content_id"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  global_secondary_index {
    name            = "user_id-created_at-index"
    hash_key        = "user_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  ttl {
    enabled        = true
    attribute_name = "ttl_expiration"
  }
}
```

**Переваги Terraform:**
- ✅ Version control для infrastructure
- ✅ Reproducible deployments
- ✅ Easy rollback
- ✅ Multi-environment (dev/staging/prod)

### 2.6.2 Automated Testing

**Unit Tests**
```python
# tests/test_content_narrative.py
import pytest
from lambda_function import lambda_handler

def test_narrative_generation():
    event = {
        'theme': {
            'theme': 'Haunted mansion',
            'opening_hook': '...',
            'key_moments': [...],
            'climax_reveal': '...'
        },
        'channel_config': {...}
    }

    result = lambda_handler(event, None)

    assert result['statusCode'] == 200
    assert 'narrative' in result
    assert len(result['narrative']['scenes']) == 5
```

**Integration Tests**
```python
# tests/integration/test_full_workflow.py
import boto3

def test_full_content_generation():
    # Trigger Step Functions
    sf = boto3.client('stepfunctions')
    response = sf.start_execution(
        stateMachineArn='arn:aws:states:...',
        input=json.dumps({
            'user_id': 'test-user',
            'requested_channels': ['test-channel']
        })
    )

    # Poll до completion
    execution_arn = response['executionArn']
    status = wait_for_completion(execution_arn, timeout=600)

    assert status == 'SUCCEEDED'

    # Verify content saved
    content = get_generated_content('test-user')
    assert len(content) > 0
```

**End-to-End Tests**
```python
# tests/e2e/test_video_playback.py
import requests

def test_video_accessible():
    # Generate content
    content_id = trigger_content_generation()

    # Wait for video assembly
    wait_for_video_assembly(content_id, timeout=900)

    # Get presigned URL
    video_url = get_presigned_url(content_id)

    # Verify video downloadable
    response = requests.head(video_url)
    assert response.status_code == 200
    assert 'video/mp4' in response.headers['Content-Type']
```

### 2.6.3 CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/deploy.yml
name: Deploy to AWS

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt

      - name: Run unit tests
        run: pytest tests/unit/

      - name: Run integration tests
        run: pytest tests/integration/
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
      - uses: actions/checkout@v3

      - name: Deploy Lambda functions
        run: |
          for func in aws/lambda/*/; do
            cd $func
            zip -r function.zip .
            aws lambda update-function-code \
              --function-name $(basename $func) \
              --zip-file fileb://function.zip
            cd -
          done
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}

      - name: Deploy Step Functions
        run: |
          aws stepfunctions update-state-machine \
            --state-machine-arn arn:aws:states:... \
            --definition file://aws/step-functions/content-generator.json

      - name: Run E2E tests
        run: pytest tests/e2e/
```

---

## 2.7 Ідеальна Scalability Architecture

### 2.7.1 Horizontal Scaling

**Multi-GPU Image Generation**
```
Current: 1 EC2 instance (g6.2xlarge)
  - MaxConcurrency: 3 batches
  - Throughput: ~54 images / 90 seconds

Ideal: 2-3 EC2 instances
  - Auto-scaling based on SQS queue depth
  - Load balancer між instances
  - Throughput: ~162 images / 90 seconds (3x)
```

**Architecture:**
```
SQS Queue: ImageGenerationQueue
  ↓
Lambda: batch-dispatcher
  - Reads queue depth
  - Starts N EC2 instances (1-3)
  - Distributes batches
  ↓
EC2 Auto Scaling Group
  - Min: 0 (cost optimization)
  - Max: 3 (capacity limit)
  - Scale up: QueueDepth > 10
  - Scale down: QueueDepth = 0
  ↓
Each EC2: Process batches in parallel
  ↓
Results → S3
```

### 2.7.2 Caching Layer

**DynamoDB DAX (DynamoDB Accelerator)**
```
Use case: ChannelConfigs queries
  - Frequently accessed (кожна execution)
  - Rarely updated
  - DAX cache TTL: 5 minutes

Performance:
  - Without DAX: 10-20ms latency
  - With DAX: <1ms latency (10-20x speedup)

Cost:
  - DAX t3.small: ~$50/month
  - Savings: Reduced DynamoDB RCU consumption
```

**ElastiCache Redis (для application cache)**
```
Use case: OpenAI response caching
  - Cache схожі prompts (theme generation)
  - TTL: 7 днів
  - Key: hash(prompt + model + temperature)

Example:
  Prompt: "Generate horror theme about mansion"
  → Check Redis cache
  → If hit: Return cached response (0 cost, <1ms)
  → If miss: Call OpenAI → Cache response

Estimated savings:
  - Cache hit rate: ~30%
  - Cost reduction: $150/month → $105/month (30% savings)
```

**CloudFront CDN**
```
Use case: Static assets & videos
  - Edge caching (низька латентність globally)
  - S3 as origin
  - TTL: 24 години для videos, 7 днів для images

Performance:
  - Without CDN: 200-500ms latency (EU → S3 eu-central-1)
  - With CDN: 20-50ms latency (global edge locations)
```

### 2.7.3 Database Partitioning

**Поточна проблема:**
```
GeneratedContent table:
  - Single table для всіх користувачів
  - Потенційний hot partition (якщо 1 user генерує багато контенту)
```

**Рішення: Composite Partition Key**
```
Замість:
  PK: content_id

Використовувати:
  PK: user_id + shard_id (e.g., "user123#shard0")
  SK: content_id

Sharding logic:
  shard_id = hash(content_id) % 10  # 10 shards per user

Переваги:
  - Рівномірне розподілення write capacity
  - Уникнення hot partitions
  - Краща throughput для high-volume users
```

---

# 3. ПОРІВНЯЛЬНИЙ АНАЛІЗ

## 3.1 Authentication & Multi-Tenancy

### Поточна Система
**Cognito Auth + Cookie Splitting**
- ✅ **Правильно:** Використання AWS Cognito (managed service)
- ✅ **Правильно:** Multi-tenant isolation через user_id
- ✅ **Правильно:** GSI індекси для ефективних запитів
- ⚠️ **Проблема:** Cookie splitting (5 cookies) - fragile solution
- ⚠️ **Проблема:** Немає MFA
- ⚠️ **Проблема:** Немає session management (server-side)
- ❌ **Недолік:** Client-side token storage (XSS vulnerability)

**Оцінка: 7/10**
- Функціонально працює
- Має security gaps
- Cookie splitting - workaround, не best practice

### Ідеальна Система
- ✅ Server-side sessions (DynamoDB)
- ✅ Short-lived tokens (15 min) + refresh tokens
- ✅ MFA enabled
- ✅ Cognito Advanced Security Features
- ✅ Token rotation

**Рекомендації:**
1. **High Priority:** Замінити cookie splitting на server-side sessions
2. **High Priority:** Enable MFA для admin users
3. **Medium Priority:** Implement token rotation
4. **Low Priority:** Advanced Security Features (nice to have)

---

## 3.2 Workflow Orchestration (Step Functions)

### Поточна Система
**3-Phase Architecture**
- ✅ **Відмінно:** Трифазний підхід (parallel → batched → parallel)
- ✅ **Відмінно:** S3 State Offloading (256KB limit workaround)
- ✅ **Відмінно:** Image Batching System (3.3x speedup)
- ✅ **Відмінно:** SQS Retry System (WEEK 5.2 deployment)
- ✅ **Правильно:** MaxConcurrency налаштування
- ⚠️ **Проблема:** Execution status confusion (SUCCEEDED може означати "queued")
- ⚠️ **Проблема:** Немає detailed error handling для OpenAI rate limits
- ❌ **Недолік:** Немає circuit breaker для external APIs

**Оцінка: 9/10**
- Дуже добре спроектовано
- Innovative batching approach
- Потребує minor improvements у error handling

### Ідеальна Система
- ✅ Той самий 3-phase approach
- ✅ Circuit breaker для OpenAI/ElevenLabs
- ✅ Explicit execution status (completed vs queued vs failed)
- ✅ Per-API retry strategies

**Рекомендації:**
1. **High Priority:** Додати circuit breaker для external APIs
2. **High Priority:** Improve execution status clarity
3. **Medium Priority:** Custom retry strategies per error type
4. **Low Priority:** Workflow versioning (для A/B testing)

---

## 3.3 Image Generation (EC2 + Batching)

### Поточна Система
**Centralized Batching + Single EC2**
- ✅ **Відмінно:** Централізований батчінг (3.3x speedup)
- ✅ **Відмінно:** Optimistic locking (race condition prevention)
- ✅ **Відмінно:** WEEK 5.4 FIX (waiter для повної зупинки EC2)
- ✅ **Правильно:** Batch size 6 (оптимізовано для GPU memory)
- ✅ **Правильно:** MaxConcurrency 3
- ⚠️ **Проблема:** Single point of failure (1 EC2 instance)
- ⚠️ **Проблема:** InsufficientInstanceCapacity потребує SQS retry (delay 3+ min)
- ❌ **Недолік:** Немає auto-scaling (manual capacity)

**Оцінка: 8/10**
- Excellent batching innovation
- Single EC2 = bottleneck
- Потребує horizontal scaling

### Ідеальна Система
- ✅ Той самий batching algorithm
- ✅ Auto-scaling EC2 group (2-3 instances)
- ✅ Load balancer між instances
- ✅ Fallback на Bedrock/Replicate якщо EC2 недоступний

**Рекомендації:**
1. **High Priority:** Multi-GPU auto-scaling (2-3 EC2 instances)
2. **High Priority:** Fallback на Bedrock Titan Image Generator
3. **Medium Priority:** Pre-warming EC2 (keep 1 instance warm)
4. **Low Priority:** Spot instances для cost savings

---

## 3.4 TTS Pipeline

### Поточна Система
**TTS v2.0 (Content/Markup Separation)**
- ✅ **Відмінно:** Розділення content (LLM) від markup (code)
- ✅ **Відмінно:** 15-20% cost savings (менше output tokens)
- ✅ **Відмінно:** Multi-provider support (Polly + ElevenLabs)
- ✅ **Відмінно:** SSML validation перед TTS
- ✅ **Правильно:** Provider routing (Choice state)
- ⚠️ **Проблема:** Polly character limits (3000 standard, 1500 neural)
- ⚠️ **Проблема:** Немає retry logic для TTS failures
- ❌ **Недолік:** ElevenLabs не підтримує SSML (plain text only)

**Оцінка: 8.5/10**
- Excellent architecture (v2.0 redesign)
- Cost-optimized
- Потребує retry logic

### Ідеальна Система
- ✅ Той самий v2.0 approach
- ✅ Retry logic з exponential backoff
- ✅ Fallback provider (Polly → ElevenLabs → Kokoro)
- ✅ Character splitting для довгих texts

**Рекомендації:**
1. **High Priority:** Додати retry logic для TTS API failures
2. **Medium Priority:** Automatic text splitting (для > 3000 chars)
3. **Medium Priority:** Fallback provider chain
4. **Low Priority:** Додати Kokoro TTS (open-source alternative)

---

## 3.5 Video Assembly

### Поточна Система
**Hybrid Lambda/ECS**
- ✅ **Відмінно:** Автоматичний вибір платформи (duration-based)
- ✅ **Відмінно:** Cost optimization (Lambda для 95% cases)
- ✅ **Правильно:** Ken Burns effect + transitions
- ✅ **Правильно:** MoviePy для editing
- ⚠️ **Проблема:** Немає progress tracking
- ⚠️ **Проблема:** Немає retry logic
- ⚠️ **Проблема:** 512MB /tmp limit у Lambda
- ❌ **Недолік:** Повільний старт ECS (2-3 хвилини)

**Оцінка: 7.5/10**
- Smart hybrid approach
- Працює, але fragile
- Потребує кращого error handling

### Ідеальна Система
- ✅ Той самий hybrid approach
- ✅ SQS queue для video jobs (async processing)
- ✅ Progress tracking (websockets або polling)
- ✅ Retry logic з DLQ
- ✅ Pre-warmed ECS tasks (для швидкого старту)

**Рекомендації:**
1. **High Priority:** SQS queue для async video assembly
2. **High Priority:** Retry logic з DLQ
3. **Medium Priority:** Progress tracking (10%, 50%, 90% done)
4. **Low Priority:** Pre-warmed ECS (1 task завжди running)

---

## 3.6 Database Design

### Поточна Система
**DynamoDB Multi-Tenant**
- ✅ **Відмінно:** GSI індекси для мультитенант запитів
- ✅ **Відмінно:** Composite keys (user_id + channel_id)
- ✅ **Відмінно:** WEEK 5.3 FIX (content_id-created_at-index для video assembly)
- ✅ **Правильно:** On-demand billing mode
- ⚠️ **Проблема:** Немає TTL (старі дані не видаляються)
- ⚠️ **Проблема:** Немає DynamoDB Streams (no reactive patterns)
- ⚠️ **Проблема:** Немає PITR (Point-in-Time Recovery)
- ❌ **Недолік:** Немає encryption at rest (SSE)

**Оцінка: 7/10**
- Функціонально правильно
- Має operational gaps
- Потребує production-grade features

### Ідеальна Система
- ✅ Той самий schema design
- ✅ TTL enabled (auto-cleanup)
- ✅ DynamoDB Streams (для reactive patterns)
- ✅ PITR enabled (disaster recovery)
- ✅ Encryption at rest (SSE-KMS)

**Рекомендації:**
1. **High Priority:** Enable PITR (backup safety)
2. **High Priority:** Enable TTL (cost optimization)
3. **High Priority:** Enable encryption at rest
4. **Medium Priority:** DynamoDB Streams (для notifications)

---

## 3.7 S3 Storage

### Поточна Система
**4 Buckets + Lifecycle Policies**
- ✅ **Відмінно:** Lifecycle policies (auto-transition)
- ✅ **Відмінно:** WEEK 5.1 FIX (CSP для обох S3 URL форматів)
- ✅ **Відмінно:** Presigned URLs (secure access)
- ✅ **Правильно:** CORS configuration
- ⚠️ **Проблема:** Немає versioning (accidental overwrites)
- ⚠️ **Проблема:** Немає encryption at rest
- ⚠️ **Проблема:** Немає event notifications
- ❌ **Недолік:** Немає CDN (CloudFront) для videos

**Оцінка: 7/10**
- Lifecycle policies добре налаштовані
- Має security gaps
- Потребує CDN для performance

### Ідеальна Система
- ✅ Той самий bucket structure
- ✅ Versioning enabled
- ✅ SSE-S3 encryption
- ✅ CloudFront для final videos
- ✅ Event notifications (S3 → SNS)

**Рекомендації:**
1. **High Priority:** Enable versioning (захист від overwrites)
2. **High Priority:** Enable encryption at rest
3. **Medium Priority:** CloudFront CDN для videos
4. **Low Priority:** S3 Intelligent-Tiering (замість lifecycle)

---

## 3.8 Security

### Поточна Система
**CSP + HTTPS + Cookie Security**
- ✅ **Відмінно:** WEEK 5.1 FIX (CSP media-src для обох URL форматів)
- ✅ **Правильно:** HTTPS enforced
- ✅ **Правильно:** Security headers (X-Frame-Options, X-XSS-Protection)
- ✅ **Правильно:** Cookie security flags (Secure, HttpOnly, SameSite)
- ⚠️ **Проблема:** unsafe-inline у CSP script-src
- ⚠️ **Проблема:** Немає WAF (Web Application Firewall)
- ⚠️ **Проблема:** Немає rate limiting
- ❌ **Недолік:** Немає Subresource Integrity (SRI) для CDN resources

**Оцінка: 6.5/10**
- Basic security працює
- Має vulnerabilities (unsafe-inline)
- Потребує hardening для production

### Ідеальна Система
- ✅ CSP без unsafe-inline
- ✅ WAF з rate limiting
- ✅ SRI для всіх CDN scripts
- ✅ API Gateway замість Function URLs

**Рекомендації:**
1. **High Priority:** Remove unsafe-inline з CSP (refactor inline scripts)
2. **High Priority:** Додати WAF з rate limiting
3. **Medium Priority:** API Gateway замість Lambda Function URLs
4. **Low Priority:** Subresource Integrity для CDN

---

## 3.9 Monitoring & Observability

### Поточна Система
**CloudWatch Logs + Dashboard**
- ✅ **Правильно:** CloudWatch logs для всіх Lambda
- ✅ **Правильно:** Dashboard monitoring (frontend)
- ✅ **Правильно:** Cost tracking у DynamoDB
- ⚠️ **Проблема:** Немає CloudWatch Alarms
- ⚠️ **Проблема:** Немає custom metrics
- ⚠️ **Проблема:** Немає X-Ray tracing
- ❌ **Недолік:** print() замість structured logging

**Оцінка: 5/10**
- Basic logging працює
- Немає proactive alerting
- Потребує structured observability

### Ідеальна Система
- ✅ Structured logging (JSON)
- ✅ X-Ray tracing (distributed)
- ✅ CloudWatch Alarms (DLQ, errors, costs)
- ✅ Custom metrics (duration, costs, throughput)

**Рекомендації:**
1. **High Priority:** Додати CloudWatch Alarms (DLQ, errors, daily cost)
2. **High Priority:** Structured logging замість print()
3. **Medium Priority:** Enable X-Ray tracing
4. **Medium Priority:** Custom CloudWatch metrics

---

## 3.10 Cost Tracking

### Поточна Система
**Real-time DynamoDB Tracking**
- ✅ **Відмінно:** Real-time cost recording
- ✅ **Відмінно:** Per-service breakdown
- ✅ **Відмінно:** Dashboard visualization
- ✅ **Правильно:** Decimal precision
- ⚠️ **Проблема:** Немає billing alarms
- ⚠️ **Проблема:** Немає budget enforcement
- ⚠️ **Проблема:** Manual price updates
- ❌ **Недолік:** Немає cost forecasting

**Оцінка: 7.5/10**
- Excellent tracking granularity
- Reactive (не proactive)
- Потребує automated alerts

### Ідеальна Система
- ✅ Той самий tracking approach
- ✅ CloudWatch Alarms для daily cost
- ✅ Budget enforcement (auto-pause at limit)
- ✅ Cost forecasting (ML-based)
- ✅ AWS Cost Explorer integration

**Рекомендації:**
1. **High Priority:** CloudWatch Alarm для daily cost > $50
2. **High Priority:** Budget enforcement (pause generation at limit)
3. **Medium Priority:** Cost forecasting (trend analysis)
4. **Low Priority:** AWS Cost Explorer API integration

---

## 3.11 Reliability & Disaster Recovery

### Поточна Система
**SQS Retry + DLQ**
- ✅ **Відмінно:** WEEK 5.2 FIX (SQS retry system deployed)
- ✅ **Відмінно:** Дворівнева retry стратегія
- ✅ **Відмінно:** WEEK 5.4 FIX (EC2 lock state waiter)
- ✅ **Правільно:** DLQ для failed messages
- ⚠️ **Проблема:** DLQ не має alarms
- ⚠️ **Проблема:** Немає disaster recovery plan
- ⚠️ **Проблема:** Немає cross-region replication
- ❌ **Недолік:** RTO/RPO не визначені

**Оцінка: 6/10**
- Good retry logic
- Немає DR strategy
- Single region = single point of failure

### Ідеальна Система
- ✅ Той самий retry approach
- ✅ CloudWatch Alarms для DLQ
- ✅ Cross-region replication (DynamoDB Global Tables)
- ✅ Disaster Recovery Plan (RTO: 4h, RPO: 24h)
- ✅ Automated failover

**Рекомендації:**
1. **High Priority:** CloudWatch Alarm для DLQ messages > 0
2. **High Priority:** Define RTO/RPO targets
3. **Medium Priority:** Cross-region backup (S3 CRR)
4. **Low Priority:** DynamoDB Global Tables (multi-region)

---

## 3.12 CI/CD & DevOps

### Поточна Система
**Manual Deployment**
- ✅ **Правільно:** Git version control
- ✅ **Правільно:** Backups перед deployment
- ⚠️ **Проблема:** Manual Lambda packaging
- ⚠️ **Проблема:** Manual AWS CLI deployment
- ❌ **Недолік:** Немає automated testing
- ❌ **Недолік:** Немає CI/CD pipeline
- ❌ **Недолік:** Немає Infrastructure as Code (Terraform)

**Оцінка: 3/10**
- Works but error-prone
- Manual process = slow + risky
- Критично потребує automation

### Ідеальна Система
- ✅ GitHub Actions CI/CD
- ✅ Automated unit/integration/E2E tests
- ✅ Terraform для всієї infrastructure
- ✅ Blue/green deployment
- ✅ Automated rollback

**Рекомендації:**
1. **High Priority:** Terraform для infrastructure (highest ROI)
2. **High Priority:** GitHub Actions для automated deployment
3. **Medium Priority:** Unit tests для критичних Lambda
4. **Low Priority:** E2E tests для full workflow

---

# 4. РЕКОМЕНДАЦІЇ

## 4.1 Critical (Must Fix - Production Blockers)

### 1. Infrastructure as Code (Terraform)
**Проблема:** Вся infrastructure створена вручну
**Ризик:** Неможливо відтворити систему після disaster
**Рішення:** Terraform для всієї infrastructure
**Effort:** 2 тижні
**Impact:** Критичний (reproducibility + version control)

### 2. CloudWatch Alarms
**Проблема:** Немає проактивних alerts
**Ризик:** Failures можуть залишатися unpoticed
**Рішення:**
- DLQ messages > 0 → Telegram notification
- Daily cost > $50 → Email alert
- Step Functions failures > 3/hour → Pager
**Effort:** 1 день
**Impact:** Високий (operational visibility)

### 3. Database Backups (PITR)
**Проблема:** Немає point-in-time recovery
**Ризик:** Accidental delete = permanent data loss
**Рішення:** Enable PITR для всіх DynamoDB tables
**Effort:** 1 година
**Impact:** Критичний (disaster recovery)

### 4. S3 Encryption & Versioning
**Проблема:** Дані не зашифровані, overwrites без історії
**Ризик:** Security compliance + accidental data loss
**Рішення:**
- Enable SSE-S3 encryption
- Enable versioning
**Effort:** 2 години
**Impact:** Високий (security + data safety)

---

## 4.2 High Priority (Should Fix - Week 1-2)

### 5. Multi-GPU Auto-Scaling
**Проблема:** Single EC2 = bottleneck + single point of failure
**Ризик:** InsufficientInstanceCapacity delays (3+ min)
**Рішення:** Auto-scaling group (2-3 g6.2xlarge instances)
**Effort:** 1 тиждень
**Impact:** Високий (3x throughput + reliability)

### 6. Structured Logging
**Проблема:** print() statements - важко аналізувати
**Ризик:** Debugging складний, немає metrics
**Рішення:** JSON structured logging для всіх Lambda
**Effort:** 3 дні
**Impact:** Середній (observability)

### 7. TTS Retry Logic
**Проблема:** Polly/ElevenLabs API failures → workflow fails
**Ризик:** ~5% failure rate (API rate limits)
**Рішення:** Retry з exponential backoff + circuit breaker
**Effort:** 2 дні
**Impact:** Середній (reliability)

### 8. Video Assembly SQS Queue
**Проблема:** Video assembly блокує Phase 3
**Ризик:** Slow completions (особливо ECS)
**Рішення:** Async SQS queue для video jobs
**Effort:** 3 дні
**Impact:** Середній (user experience)

---

## 4.3 Medium Priority (Should Fix - Month 1)

### 9. CI/CD Pipeline (GitHub Actions)
**Проблема:** Manual deployment = slow + error-prone
**Рішення:** Automated testing + deployment
**Effort:** 1 тиждень
**Impact:** Середній (developer productivity)

### 10. X-Ray Tracing
**Проблема:** Немає end-to-end visibility
**Рішення:** Enable X-Ray для всіх Lambda
**Effort:** 2 дні
**Impact:** Середній (debugging)

### 11. CloudFront CDN
**Проблема:** High latency для global users
**Рішення:** CloudFront distribution для videos
**Effort:** 1 день
**Impact:** Середній (user experience)

### 12. WAF + Rate Limiting
**Проблема:** Немає захисту від abuse
**Рішення:** AWS WAF з rate limiting rules
**Effort:** 2 дні
**Impact:** Середній (security)

---

## 4.4 Low Priority (Nice to Have - Month 2-3)

### 13. DynamoDB Streams
**Проблема:** Немає reactive patterns
**Рішення:** Streams → Lambda triggers (notifications, analytics)
**Effort:** 1 тиждень
**Impact:** Низький (additional features)

### 14. ElastiCache Redis
**Проблема:** Повторні OpenAI calls для схожих prompts
**Рішення:** Redis cache для OpenAI responses
**Effort:** 1 тиждень
**Impact:** Низький (cost optimization ~30%)

### 15. Global Tables
**Проблема:** Single region = latency для global users
**Рішення:** DynamoDB Global Tables (multi-region)
**Effort:** 1 тиждень
**Impact:** Низький (якщо немає global users)

### 16. Blue/Green Deployment
**Проблема:** Deployments можуть ламати production
**Рішення:** Blue/green deployment strategy
**Effort:** 1 тиждень
**Impact:** Низький (zero-downtime deploys)

---

## 4.5 Підсумкова Оцінка Системи

### Загальна Архітектурна Оцінка: **7.5/10**

**Сильні Сторони:**
- ✅ Відмінна трифазна архітектура
- ✅ Innovative image batching (3.3x speedup)
- ✅ TTS v2.0 (cost-optimized)
- ✅ Hybrid Lambda/ECS (smart platform selection)
- ✅ Multi-tenant isolation (DynamoDB GSI)
- ✅ SQS retry system (WEEK 5.2)
- ✅ Recent fixes (EC2 lock, CSP, validation)

**Слабкі Сторони:**
- ❌ Немає Infrastructure as Code
- ❌ Немає CI/CD pipeline
- ❌ Немає automated testing
- ❌ Немає CloudWatch Alarms
- ❌ Немає disaster recovery plan
- ❌ Manual deployment процес
- ❌ Single EC2 bottleneck

**Висновок:**
Система має **відмінну core архітектуру** (workflow design, batching, cost optimization), але **не має production-grade operational practices** (IaC, CI/CD, monitoring, DR). Критично потрібно інвестувати у DevOps automation та operational excellence.

**Пріоритети на наступні 3 місяці:**
1. **Month 1:** Terraform + CloudWatch Alarms + Backups (foundational)
2. **Month 2:** Multi-GPU scaling + CI/CD + Structured logging (reliability)
3. **Month 3:** X-Ray + WAF + CDN (optimization)

---

**Кінець документу**
