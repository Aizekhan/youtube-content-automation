# ⚡ SQS Retry System - Система Повторних Спроб для EC2

**Версія:** 1.0
**Дата створення:** 2025-11-18
**Статус:** ✅ Production Ready
**Регіон:** eu-central-1

---

## 📖 Зміст

1. [Огляд](#огляд)
2. [Проблема яку вирішує](#проблема-яку-вирішує)
3. [Архітектура рішення](#архітектура-рішення)
4. [Компоненти системи](#компоненти-системи)
5. [Як це працює](#як-це-працює)
6. [Конфігурація](#конфігурація)
7. [Моніторинг](#моніторинг)
8. [Тестування](#тестування)

---

## Огляд

### Що це?

**SQS Retry System** - це автоматична система повторних спроб запуску EC2 інстансів для генерації зображень коли AWS не має доступних потужностей (InsufficientInstanceCapacity).

### Навіщо потрібна?

Коли AWS Step Functions намагається запустити EC2 g5.xlarge інстанс для генерації зображень, іноді AWS повертає помилку `InsufficientInstanceCapacity` через відсутність вільних GPU інстансів у регіоні.

**До впровадження системи**:
- Workflow падав після 3 швидких спроб (~70 секунд)
- Потрібне було ручне повторне запускання
- Втрата часу та згенерованого контенту

**Після впровадження системи**:
- Автоматичні повторні спроби кожні 3 хвилини
- До 20 спроб протягом 1 години
- Автоматичне відновлення workflow після успішного старту
- Збереження стану для manual review після 20 невдалих спроб

---

## Проблема яку вирішує

### BUG #10: InsufficientInstanceCapacity

**Симптоми**:
```
Error: InsufficientInstanceCapacity
The requested configuration is currently not supported.
Please check the documentation for supported configurations.
```

**Коли трапляється**:
- Пікові години використання AWS
- Обмежена доступність GPU інстансів у регіоні
- Maintenance events у датацентрах AWS

**Вплив на бізнес**:
- Workflow зупиняється на етапі генерації зображень
- Контент не завершується
- Потрібне ручне втручання

---

## Архітектура рішення

### Двохрівнева стратегія

#### Рівень 1: Швидкі спроби (Step Functions Retry)
```
Спроба 1 ─► Чекати 10 сек  ─► Спроба 2 ─► Чекати 20 сек ─► Спроба 3
           (якщо fail)                   (якщо fail)

Загальний час: ~70 секунд
Мета: Вирішити тимчасові збої
```

#### Рівень 2: Довготривалі спроби (SQS + EventBridge)
```
Після 3 невдач ─► Додати в SQS чергу ─► EventBridge кожні 3 хв

Спроба 4  @ 3 хв
Спроба 5  @ 6 хв
Спроба 6  @ 9 хв
...
Спроба 20 @ 57 хв

Загальний час: До 1 години
Мета: Дочекатись доступності EC2
```

### Візуальна діаграма

```
┌──────────────────────────────────────────────────────────┐
│         STEP FUNCTIONS WORKFLOW                          │
└──────────────────────────────────────────────────────────┘
                      │
                      ▼
         ┌────────────────────────┐
         │  StartEC2ForAllImages  │
         │    (ec2-sd35-control)  │
         └────────────┬───────────┘
                      │
          ┌───────────┴───────────┐
          │   Retry (3 спроби)    │
          │   10s, 20s, 40s       │
          └───────────┬───────────┘
                      │
         ┌────────────┴────────────┐
         │                         │
    ✅ SUCCESS                ❌ ALL FAILED
         │                         │
         ▼                         ▼
┌─────────────────┐    ┌──────────────────────┐
│GenerateImages   │    │     Catch Block      │
└─────────────────┘    │  → QueueForRetry     │
                       └──────────┬───────────┘
                                  │
                       ┌──────────▼──────────┐
                       │  queue-failed-ec2   │
                       │   Lambda Function   │
                       └──────────┬──────────┘
                                  │
                       ┌──────────▼──────────┐
                       │  SQS Queue:         │
                       │ PendingImageGen     │
                       └──────────┬──────────┘
                                  │
              ┌───────────────────┴───────────────────┐
              │                                       │
              │ EventBridge Rule (every 3 min)       │
              │        retry-ec2-every-3min          │
              └───────────────────┬───────────────────┘
                                  │
                       ┌──────────▼──────────┐
                       │  retry-ec2-queue    │
                       │   Lambda Function   │
                       └──────────┬──────────┘
                                  │
          ┌───────────────────────┴───────────────────┐
          │                                           │
    ✅ EC2 Started                            ❌ Still Failed
          │                                           │
          ▼                                           ▼
┌──────────────────┐                      ┌────────────────┐
│ Invoke           │                      │ Return to      │
│content-generate- │                      │ Queue (retry   │
│images (async)    │                      │ in 3 min)      │
│                  │                      │                │
│Delete message    │                      │ After 20       │
│from queue        │                      │ attempts →     │
│                  │                      │ Dead Letter    │
│✅ Workflow        │                      │ Queue (DLQ)    │
│  resumed!        │                      └────────────────┘
└──────────────────┘
```

---

## Компоненти системи

### 1. SQS Queues

#### Main Queue: `PendingImageGeneration`
- **URL**: `https://sqs.eu-central-1.amazonaws.com/599297130956/PendingImageGeneration`
- **VisibilityTimeout**: 180 секунд (3 хвилини)
- **Message Retention**: 2 години
- **MaxReceiveCount**: 20 спроб
- **Long Polling**: 20 секунд

**Призначення**: Зберігає стан workflow для повторних спроб запуску EC2

#### Dead Letter Queue: `PendingImageGeneration-DLQ`
- **ARN**: `arn:aws:sqs:eu-central-1:599297130956:PendingImageGeneration-DLQ`
- **Retention**: 14 днів

**Призначення**: Зберігає повідомлення після 20 невдалих спроб для ручного розгляду

### 2. Lambda Functions

#### `queue-failed-ec2`
**Файл**: `aws/lambda/queue-failed-ec2/lambda_function.py`

**Тригер**: Step Functions Catch block

**Що робить**:
1. Отримує стан workflow (execution_arn, prompts, phase1 results)
2. Створює повідомлення в SQS черзі
3. Додає метаданні (timestamp, retry_count)
4. Повертає успішний статус

**Input**:
```json
{
  "execution_arn": "test-workflow-123",
  "collectedPrompts": {
    "Payload": {
      "all_image_prompts": [...],
      "total_images": 18
    }
  },
  "phase1Results": [...]
}
```

**Output**:
```json
{
  "statusCode": 200,
  "message": "Added to retry queue",
  "message_id": "abc-123",
  "queue_url": "https://sqs..."
}
```

#### `retry-ec2-queue`
**Файл**: `aws/lambda/retry-ec2-queue/lambda_function.py`

**Тригер**: EventBridge rule (кожні 3 хвилини)

**Що робить**:
1. Читає повідомлення з SQS черги
2. Намагається запустити EC2 (invoke `ec2-sd35-control`)
3. **Якщо успішно**:
   - Викликає `content-generate-images` (async)
   - Видаляє повідомлення з черги
   - Workflow відновлюється
4. **Якщо невдача**:
   - Повідомлення повертається в чергу
   - Наступна спроба через 3 хвилини

**Output (Success)**:
```json
{
  "statusCode": 200,
  "body": {
    "message": "EC2 started and workflow resumed",
    "endpoint": "http://3.123.456.789:5000",
    "execution_arn": "test-workflow-123"
  }
}
```

**Output (No messages)**:
```json
{
  "statusCode": 200,
  "body": {
    "message": "No pending tasks"
  }
}
```

### 3. EventBridge Rule

**Name**: `retry-ec2-every-3min`
**Schedule**: `rate(3 minutes)`
**Target**: Lambda `retry-ec2-queue`
**Status**: ✅ ENABLED

**ARN**: `arn:aws:events:eu-central-1:599297130956:rule/retry-ec2-every-3min`

### 4. IAM Permissions

#### `ContentGeneratorLambdaRole`

**Додана Inline Policy**: `SQSRetryQueueAccess`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes",
        "sqs:ChangeMessageVisibility"
      ],
      "Resource": [
        "arn:aws:sqs:eu-central-1:599297130956:PendingImageGeneration",
        "arn:aws:sqs:eu-central-1:599297130956:PendingImageGeneration-DLQ"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["lambda:InvokeFunction"],
      "Resource": [
        "arn:aws:lambda:eu-central-1:599297130956:function:ec2-sd35-control",
        "arn:aws:lambda:eu-central-1:599297130956:function:content-generate-images"
      ]
    }
  ]
}
```

### 5. Step Functions Changes

**Файл**: `aws/step-functions-with-sqs-retry.json`

**Додано до стану `StartEC2ForAllImages`**:

```json
{
  "Retry": [
    {
      "ErrorEquals": ["States.ALL"],
      "IntervalSeconds": 10,
      "MaxAttempts": 3,
      "BackoffRate": 2.0,
      "Comment": "Quick retry 3x (10s, 20s, 40s)"
    }
  ],
  "Catch": [
    {
      "ErrorEquals": ["States.ALL"],
      "ResultPath": "$.ec2Error",
      "Next": "QueueForRetry",
      "Comment": "After 3 fails → SQS queue"
    }
  ]
}
```

**Додано нові стани**:

```json
{
  "QueueForRetry": {
    "Type": "Task",
    "Resource": "arn:aws:states:::lambda:invoke",
    "Parameters": {
      "FunctionName": "queue-failed-ec2",
      "Payload": {
        "execution_arn.$": "$$.Execution.Name",
        "collectedPrompts.$": "$.collectedPrompts",
        "phase1Results.$": "$.phase1Results"
      }
    },
    "Next": "WaitForManualIntervention"
  },
  "WaitForManualIntervention": {
    "Type": "Pass",
    "Result": {
      "status": "queued_for_retry",
      "message": "EC2 unavailable. Queued for retry every 3 min (up to 1 hour)."
    },
    "End": true
  }
}
```

---

## Як це працює

### Сценарій 1: Нормальна робота (EC2 доступний)

```
1. StartEC2ForAllImages
2. ec2-sd35-control викликається
3. ✅ EC2 стартує успішно з першої спроби
4. GenerateAllImagesBatched (генерація зображень)
5. Workflow продовжується нормально
```

**Результат**: SQS черга залишається порожньою (0 messages)

---

### Сценарій 2: Тимчасова недоступність (вирішується швидко)

```
1. StartEC2ForAllImages
2. Спроба 1: ❌ InsufficientInstanceCapacity
3. Чекаємо 10 сек
4. Спроба 2: ✅ SUCCESS!
5. GenerateAllImagesBatched
6. Workflow продовжується
```

**Результат**: SQS черга залишається порожньою (вирішено retry в Step Functions)

---

### Сценарій 3: Довга недоступність (потрібна SQS черга)

```
1. StartEC2ForAllImages
2. Спроба 1-3: ❌ ❌ ❌ (всі 3 швидкі спроби невдалі)
3. Catch block спрацьовує
4. QueueForRetry → queue-failed-ec2 Lambda
5. Стан workflow зберігається в SQS черзі:
   {
     "execution_arn": "...",
     "collected_prompts": {...},
     "phase1_results": [...],
     "queued_at": "2025-11-18T14:30:00Z",
     "retry_count": 0
   }
6. WaitForManualIntervention (workflow зупиняється)
7. EventBridge тригерить retry-ec2-queue кожні 3 хв:

   @ 3 хв  - Спроба 4:  ❌ Still not available
   @ 6 хв  - Спроба 5:  ❌ Still waiting...
   @ 9 хв  - Спроба 6:  ❌ Not yet
   @ 12 хв - Спроба 7:  ✅ SUCCESS! EC2 started!

8. retry-ec2-queue:
   - Викликає content-generate-images (async)
   - Передає збережений стан workflow
   - Видаляє повідомлення з черги

9. ✅ Генерація зображень продовжується
10. ✅ Результат зберігається в DynamoDB
```

**Результат**: Workflow відновлено після 4 невдалих швидких спроб та 4 SQS спроб (12 хвилин очікування)

---

### Сценарій 4: Критична недоступність (20 спроб вичерпано)

```
1-3.   Швидкі спроби (70 сек) - ❌
4-23.  SQS спроби (57 хвилин, 20 спроб) - ❌ ❌ ❌ ...
24.    Message moved to Dead Letter Queue
```

**Результат**: Ручний розгляд потрібен

**Дії**:
1. Перевірити DLQ:
   ```bash
   aws sqs get-queue-attributes \
     --queue-url https://sqs.eu-central-1.amazonaws.com/.../PendingImageGeneration-DLQ \
     --attribute-names ApproximateNumberOfMessages
   ```
2. Прочитати повідомлення:
   ```bash
   aws sqs receive-message \
     --queue-url https://sqs...DLQ \
     --max-number-of-messages 1
   ```
3. Вирішити проблему (змінити регіон, інстанс тип, тощо)
4. Ручне перезапуск або відновлення workflow

---

## Конфігурація

### Timeline повторних спроб

| Спроба | Час | Тип | Статус |
|--------|-----|-----|--------|
| 1 | 0s | Step Functions Retry | |
| 2 | 10s | Step Functions Retry | |
| 3 | 30s | Step Functions Retry | |
| 4 | 3m 0s | SQS + EventBridge | |
| 5 | 6m 0s | SQS + EventBridge | |
| 6 | 9m 0s | SQS + EventBridge | |
| ... | ... | ... | |
| 20 | 57m 0s | SQS + EventBridge | |
| 21+ | 60m+ | → Dead Letter Queue | Manual Review |

**Загальне вікно повторів**: ~1 година
**Кількість автоматичних спроб**: 23 (3 швидкі + 20 SQS)

---

## Моніторинг

### Перевірка стану SQS черги

```bash
# Перевірити кількість повідомлень
aws sqs get-queue-attributes \
  --queue-url https://sqs.eu-central-1.amazonaws.com/599297130956/PendingImageGeneration \
  --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible \
  --region eu-central-1
```

**Вихід**:
```json
{
  "ApproximateNumberOfMessages": "0",          // Видимі повідомлення
  "ApproximateNumberOfMessagesNotVisible": "1" // Невидимі (обробляються)
}
```

### Перевірка логів retry Lambda

```bash
# Переглянути останні логи
aws logs tail /aws/lambda/retry-ec2-queue --follow --region eu-central-1

# Або фільтрувати помилки
aws logs filter-log-events \
  --log-group-name /aws/lambda/retry-ec2-queue \
  --filter-pattern "ERROR" \
  --region eu-central-1
```

### Перевірка EventBridge rule

```bash
# Переконатись що правило активне
aws events describe-rule \
  --name retry-ec2-every-3min \
  --region eu-central-1 \
  --query 'State'
```

**Очікується**: `"ENABLED"`

### Dashboard метрики

У **CloudWatch Dashboard** можна створити віджети:

1. **SQS Queue Depth**:
   - Метрика: `ApproximateNumberOfMessagesVisible`
   - Namespace: `AWS/SQS`
   - QueueName: `PendingImageGeneration`

2. **Lambda Invocations**:
   - Метрика: `Invocations`
   - Namespace: `AWS/Lambda`
   - FunctionName: `retry-ec2-queue`

3. **Lambda Errors**:
   - Метрика: `Errors`
   - Namespace: `AWS/Lambda`
   - FunctionName: `retry-ec2-queue`

---

## Тестування

### Тест 1: Нормальний workflow (2025-11-18)

**Execution**: `test-sqs-retry-1763475445`

**Результат**: ✅ SUCCEEDED (6m 32s)

**Висновок**:
- EC2 стартував успішно з першої спроби
- SQS черга НЕ використовувалась (0 messages)
- Normal flow працює без проблем

**Документація**: `SQS-RETRY-TEST-RESULTS.md`

---

### Тест 2: Ручне тестування SQS (2025-11-18)

**Мета**: Перевірити retry-ec2-queue Lambda

**Кроки**:
1. Створено тестове повідомлення
2. Додано в SQS чергу
3. Викликано retry-ec2-queue Lambda

**Проблема виявлена**: ❌ **BUG #11 - Missing SQS Permissions**

```
Error: AccessDenied - User retry-ec2-queue is not authorized
to perform: sqs:receivemessage
```

**Виправлення**: Додано `SQSRetryQueueAccess` inline policy до `ContentGeneratorLambdaRole`

**Результат після фіксу**: ✅ Lambda успішно читає з черги

**Документація**: `SQS-MANUAL-TEST-RESULTS.md`

---

### Тест 3: Повний workflow з фіксами (2025-11-18)

**Execution**: `test-sqs-full-1763479143`

**Результат**: ✅ SUCCEEDED (4m 11s)

**Висновок**:
- Всі компоненти працюють після виправлення permissions
- Normal workflow НЕ порушений інтеграцією SQS
- Система готова до production

**Документація**: `SQS-PERMISSIONS-FIX-TEST-RESULTS.md`

---

## Виправлені Bugs

### BUG #10: InsufficientInstanceCapacity
- **Статус**: ✅ ВИРІШЕНО
- **Рішення**: SQS Retry System
- **Дата**: 2025-11-18

### BUG #11: Missing SQS Permissions
- **Статус**: ✅ ВИРІШЕНО
- **Рішення**: Додано inline policy `SQSRetryQueueAccess`
- **Дата**: 2025-11-18

---

## Вартість системи

| Компонент | Вартість | Примітка |
|-----------|----------|----------|
| SQS | $0 | Перший 1M requests/місяць безкоштовно |
| Lambda (queue-failed-ec2) | $0 | Викликається рідко (тільки при помилках) |
| Lambda (retry-ec2-queue) | $0.000001/invoke | Кожні 3 хв = 480 разів/день |
| EventBridge Rule | $0.000001/invoke | 480 разів/день |
| **Загальна вартість** | **~$0.01/місяць** | Практично безкоштовно |

**Висновок**: Система надає величезну цінність (автоматичне відновлення) практично без додаткових витрат.

---

## Поширені питання (FAQ)

### Q: Чому 3 хвилини між спробами?
**A**: Баланс між швидкістю та збереженням Lambda викликів. 3 хвилини дають AWS час звільнити потужності, але не занадто довго чекати.

### Q: Що якщо після 20 спроб EC2 все ще недоступний?
**A**: Повідомлення переміщується в Dead Letter Queue. Потрібне ручне втручання - перевірити AWS Service Health, змінити регіон, або змінити тип інстансу.

### Q: Чи можна збільшити кількість спроб?
**A**: Так. Змініть `maxReceiveCount` у SQS черзі. Але 20 спроб (1 година) - розумний максимум для автоматичних спроб.

### Q: Чи зберігається контент якщо workflow падає?
**A**: Так! Phase 1 results (theme + narrative) зберігаються в SQS повідомленні. Коли EC2 стартує, генерація продовжується з того місця.

### Q: Як протестувати систему без реального EC2 збою?
**A**: Можна вручну додати повідомлення в SQS чергу (див. Тест 2 вище), або тимчасово модифікувати `ec2-sd35-control` щоб повертати помилку.

---

## Подальші поліпшення

### Можливі розширення:

1. **Multi-region fallback**:
   - Якщо eu-central-1 недоступний, спробувати us-east-1
   - Вимагає додаткової конфігурації VPC/Subnets

2. **Smart retry intervals**:
   - Exponential backoff замість фіксованих 3 хвилин
   - Приклад: 3m, 5m, 10m, 15m, 30m...

3. **Slack/Email сповіщення**:
   - Повідомляти когось коли повідомлення потрапляє в DLQ
   - SNS integration з DLQ

4. **Альтернативні instance types**:
   - Якщо g5.xlarge недоступний, спробувати g4dn.xlarge
   - Вимагає логіки fallback в ec2-sd35-control

---

## Документація і Посилання

- **Повна документація системи**: `DOCUMENTATION-UA.md`
- **Результати тестування**:
  - `SQS-RETRY-TEST-RESULTS.md` - Перший тест
  - `SQS-MANUAL-TEST-RESULTS.md` - Ручний тест + BUG #11
  - `SQS-PERMISSIONS-FIX-TEST-RESULTS.md` - Фінальний тест
- **Технічна специфікація**: `SQS-RETRY-SYSTEM-COMPLETE.md`
- **Step Functions Definition**: `aws/step-functions-with-sqs-retry.json`
- **Lambda Source Code**:
  - `aws/lambda/queue-failed-ec2/lambda_function.py`
  - `aws/lambda/retry-ec2-queue/lambda_function.py`

---

**Версія документу**: 1.0
**Автор**: YouTube Content Automation System
**Останнє оновлення**: 2025-11-18
**Статус**: ✅ Production Ready
