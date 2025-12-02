# Batching & SQS Queue System - Status Report

**Date**: 2025-11-24
**Status**: ✅ **ACTIVE & WORKING**

---

## Overview

Система батчинга і SQS черг **існує і активна** в production. Вона використовується для:
1. Ефективної генерації зображень для кількох каналів одночасно
2. Retry механізму для failed EC2 starts
3. Запобігання timeout помилок при великій кількості сцен

---

## 🏗️ Architecture Components

### 1. SQS Queues

#### Main Queue: `PendingImageGeneration`
- **URL**: `https://sqs.eu-central-1.amazonaws.com/599297130956/PendingImageGeneration`
- **Status**: Active ✅
- **Current Messages**: 0
- **Delayed Messages**: 0
- **Not Visible**: 0
- **Max Retries**: 20
- **Purpose**: Зберігає workflow state коли EC2 instance не може стартувати

#### Dead Letter Queue (DLQ): `PendingImageGeneration-DLQ`
- **URL**: `https://sqs.eu-central-1.amazonaws.com/599297130956/PendingImageGeneration-DLQ`
- **Status**: Active ✅
- **Purpose**: Зберігає повідомлення після 20 невдалих спроб

---

## 🔧 Lambda Functions

### 1. Content Generate Images (Main Batching Logic)

**Function**: `content-generate-images`
**Status**: Active ✅

**Batching Features**:
- Підтримує `batch_mode=true` для обробки сцен по batch'ам
- Default batch size: 6 сцен за раз
- Зменшує timeout проблеми для великої кількості сцен

**Parameters**:
```json
{
  "batch_mode": true,
  "batch_size": 6,
  "batch_index": 0,
  "all_prompts": [...]
}
```

**Output**:
```json
{
  "scene_images": [...],
  "batch_info": {
    "batch_index": 0,
    "batch_size": 6,
    "total_batches": 3,
    "scenes_in_batch": 6
  }
}
```

### 2. Queue Failed EC2

**Function**: `queue-failed-ec2`
**Last Updated**: 2025-11-18 14:05:45 UTC
**Status**: Active ✅

**Purpose**:
- Викликається Step Functions Catch block коли EC2 start fails
- Додає workflow state до SQS queue для пізнішого retry

**SQS Message Structure**:
```json
{
  "execution_arn": "arn:aws:states:...",
  "collected_prompts": {...},
  "phase1_results": [...],
  "queued_at": "2025-11-24T08:00:00Z",
  "retry_count": 0
}
```

### 3. Retry EC2 Queue

**Function**: `retry-ec2-queue`
**Last Updated**: 2025-11-18 14:05:57 UTC
**Status**: Active ✅
**Trigger**: EventBridge rule `retry-ec2-every-3min` (ENABLED)

**Purpose**:
- Перевіряє SQS queue кожні 3 хвилини
- Робить retry EC2 start для pending tasks
- Long polling: 5 секунд
- Visibility timeout: 180 секунд (3 хвилини)

**Workflow**:
1. Отримує message з queue
2. Намагається стартувати EC2 instance
3. Якщо успішно - видаляє message з queue
4. Якщо fail - збільшує retry_count і повертає в queue

### 4. Additional Batching Functions

#### `prepare-image-batches`
- **Last Updated**: 2025-11-16 17:16:54 UTC
- **Purpose**: Розбиває великий список промптів на batch'і

#### `merge-image-batches`
- **Last Updated**: 2025-11-09 20:10:42 UTC
- **Purpose**: Об'єднує результати з кількох batch'ів

---

## 📊 Step Functions Integration

### Current State Machine: `ContentGenerator`

**Comment**: "Optimized Multi-Channel Content Generator with Global Batching + Video Assembly"

### Batching Step: `GenerateAllImagesBatched`

**Type**: Task
**Resource**: `arn:aws:states:::lambda:invoke`

**Configuration**:
```json
{
  "FunctionName": "content-generate-images",
  "Payload": {
    "all_prompts.$": "$.collectedPrompts.Payload.all_image_prompts",
    "provider.$": "$.collectedPrompts.Payload.provider",
    "batch_mode": true,
    "ec2_endpoint.$": "$.ec2Endpoint.Payload.endpoint"
  }
}
```

**Key Features**:
- ✅ `batch_mode: true` - увімкнено глобальний батчинг
- ✅ Обробляє промпти з усіх каналів одночасно
- ✅ Передає EC2 endpoint для прямого доступу

---

## 🔄 Error Handling & Retry Mechanism

### When EC2 Start Fails

```
Step Functions Execution
    ↓
[StartEC2 Task FAILS]
    ↓
[Catch Block] → queue-failed-ec2 Lambda
    ↓
SQS Queue (PendingImageGeneration)
    ↓
[Every 3 minutes]
    ↓
retry-ec2-queue Lambda
    ↓
Attempts EC2 Start Again
    ↓
Success? → Remove from queue
Fail?    → Back to queue (retry_count++)
```

### Retry Configuration

- **Max Retries**: 20 (in SQS)
- **Retry Interval**: 3 minutes (EventBridge rule)
- **Visibility Timeout**: 3 minutes
- **After 20 fails**: Message moves to DLQ

---

## 📈 Benefits

### 1. Timeout Prevention
- Обробка великої кількості сцен (>10) не призводить до timeout
- Batch size 6 - оптимальний баланс між швидкістю і надійністю

### 2. Multi-Channel Efficiency
- Генерація зображень для кількох каналів паралельно
- Одна EC2 instance обробляє всі запити

### 3. Resilience
- Автоматичний retry при EC2 failures
- Збереження workflow state в SQS
- Dead Letter Queue для критичних помилок

### 4. Cost Optimization
- EC2 instance стартує один раз для всіх каналів
- Batch processing зменшує overhead
- Retry system запобігає втраті already-processed data

---

## 🔍 How to Monitor

### Check SQS Queue Status

```bash
aws sqs get-queue-attributes \
  --queue-url "https://sqs.eu-central-1.amazonaws.com/599297130956/PendingImageGeneration" \
  --attribute-names All \
  --region eu-central-1
```

### Check Retry Lambda Logs

```bash
MSYS_NO_PATHCONV=1 aws logs tail /aws/lambda/retry-ec2-queue \
  --since 1h --format short --region eu-central-1
```

### Check Queue Lambda Logs

```bash
MSYS_NO_PATHCONV=1 aws logs tail /aws/lambda/queue-failed-ec2 \
  --since 1h --format short --region eu-central-1
```

### Check EventBridge Rule

```bash
aws events list-rules \
  --region eu-central-1 \
  --query 'Rules[?Name==`retry-ec2-every-3min`]'
```

---

## 📋 Testing Checklist

### ✅ Verify Batching Works

1. Запустити генерацію для каналу з >6 сценами
2. Перевірити в Step Functions що використовується `GenerateAllImagesBatched`
3. Перевірити логи `content-generate-images` для `batch_info`

### ✅ Verify SQS Retry Works

1. Вимкнути EC2 instance вручну
2. Запустити генерацію
3. Перевірити що повідомлення з'явилось в SQS queue
4. Зачекати 3 хвилини
5. Перевірити логи `retry-ec2-queue` для retry attempt

### ✅ Verify Dead Letter Queue

1. Якщо повідомлення не обробилось після 20 спроб
2. Перевірити DLQ:
```bash
aws sqs receive-message \
  --queue-url "https://sqs.eu-central-1.amazonaws.com/599297130956/PendingImageGeneration-DLQ" \
  --region eu-central-1
```

---

## 🚀 Future Improvements (Optional)

### 1. Dynamic Batch Size
- Адаптувати batch size залежно від load
- Більші batch'і коли EC2 instance warm

### 2. Priority Queue
- Додати priority для urgent generations
- Окрема queue для high-priority tasks

### 3. Batch Optimization
- Групувати промпти по similarity для кращого кешування
- Smart batching на основі prompt complexity

### 4. CloudWatch Alarms
- Alert коли DLQ не порожній
- Alert коли retry rate > 50%
- Alert коли queue age > 30 minutes

---

## 📚 Related Files

- `aws/lambda/content-generate-images/lambda_function.py` - Main batching logic
- `aws/lambda/queue-failed-ec2/lambda_function.py` - Queue failed attempts
- `aws/lambda/retry-ec2-queue/lambda_function.py` - Retry mechanism
- `aws/step-functions-mega-mode-with-batching.json` - Batching Step Functions definition
- `aws/step-functions-with-sqs-retry.json` - SQS retry Step Functions definition

---

**Conclusion**: Батчинг і SQS система **повністю функціональна і активна** ✅

Вона автоматично обробляє:
- ✅ Batch generation для великої кількості зображень
- ✅ EC2 retry при failures
- ✅ Dead letter queue для критичних помилок
- ✅ Автоматичний retry кожні 3 хвилини
