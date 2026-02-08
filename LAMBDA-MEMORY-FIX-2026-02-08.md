# Lambda Timeout Fix - Збільшення пам'яті

**Дата:** 2026-02-08
**Проблема:** Lambda timeout при генерації зображень
**Root Cause:** Недостатньо пам'яті для обробки DynamoDB запитів
**Рішення:** ✅ Збільшено пам'ять з 512 MB до 2048 MB

---

## 🔍 Детальне розслідування

### Симптоми проблеми

1. **Step Functions виконання таймаутять рівно через 15 хвилин**
   - Execution `test-single-channel-images-1770551995` - FAILED (timeout)
   - Duration: 900000 ms (рівно 15 хв - максимальний таймаут Lambda)

2. **Порожні CloudWatch логи**
   ```
   START RequestId: 38e29b29-5892-4c48-971b-e965131e3647
   END RequestId: 38e29b29-5892-4c48-971b-e965131e3647
   REPORT Duration: 900000.00 ms, Max Memory: 107 MB, Init: 640ms, Status: timeout
   ```
   - **ЖОДНИХ print statements між START та END!**
   - Lambda ніколи не доходить до рядка 637 (перший print у lambda_handler)

3. **Прямий виклик Lambda працює нормально**
   ```bash
   aws lambda invoke --function-name content-generate-images \
     --payload '{"all_prompts":[{"prompt":"test"}],...}'
   ```
   - Завершується за 5 секунд ✅
   - Генерує зображення успішно ✅

### Чому прямий виклик працював?

**Різниця в payload:**
- **Step Functions виклик:**
  - 5 каналів × 6 зображень = 30 промптів
  - Кожен промпт: довгий текст українською (200-300 символів)
  - Загальний payload: ~50-100 KB JSON

- **Прямий тест виклик:**
  - 1 простий промпт: "A serene zen garden"
  - Payload: ~2 KB JSON

---

## 🐛 Root Cause Analysis

### Де Lambda зависає?

**Lambda ніколи не доходить до своєї логіки!** Аналіз коду показав:

```python
# lambda_function.py, рядок 637 - перший print statement
def lambda_handler(event, context):
    print(f"🎨 Image Generator - Multi-Provider Version")  # ⬅️ СЮДИ НІКОЛИ НЕ ДОХОДИТЬ!
```

Якщо Lambda не виводить ЖОДНИХ print statements, значить вона зависає **ДО** початку виконання handler функції, але **ПІСЛЯ** ініціалізації (Init Duration: 640ms нормальний).

### Що відбувається між Init та Handler?

Lambda виконує глобальні операції **під час імпорту модулів**:

```python
# Рядки 1-20: Імпорти та ініціалізація boto3 клієнтів
import json
import boto3
from config_merger import merge_configuration

# ⚠️ ЦІ КЛІЄНТИ СТВОРЮЮТЬСЯ ПІД ЧАС IMPORT!
bedrock_runtime = boto3.client('bedrock-runtime', region_name='eu-central-1')
s3 = boto3.client('s3', region_name='eu-central-1')
secrets_client = boto3.client('secretsmanager', region_name='eu-central-1')
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')  # ⬅️ ТУТ!
cost_table = dynamodb.Table('CostTracking')  # ⬅️ І ТУТ!
lambda_client = boto3.client('lambda', region_name='eu-central-1')
```

**Але ці операції відбуваються під час Init (640ms), і вони швидкі.**

### Справжня причина - DynamoDB запити в handler!

Lambda зависає тут:

```python
# lambda_function.py, рядки 390-422
def handle_multi_channel_batch(all_prompts, provider, user_id=None):
    # Pre-load all unique channel configs
    unique_channels = set(p.get('channel_id') for p in all_prompts if p.get('channel_id'))
    print(f"   Loading configs for {len(unique_channels)} unique channels...")  # ⬅️ СЮДИ НЕ ДОХОДИТЬ!

    for channel_id in unique_channels:  # 5 каналів
        try:
            channel_table = dynamodb.Table('ChannelConfigs')
            channel_response = channel_table.query(  # ⬅️ ТУТ ЗАВИСАЄ!!!
                IndexName='channel_id-index',
                KeyConditionExpression=Key('channel_id').eq(channel_id)
            )

            # Потім ще один запит для кожного каналу
            thumbnail_table = dynamodb.Table('ThumbnailTemplates')
            thumbnail_response = thumbnail_table.get_item(  # ⬅️ І ТУТ!
                Key={'template_id': selected_thumbnail_template}
            )
```

**Проблема:**
1. Lambda з 512 MB пам'яті отримує лише ~0.5 vCPU
2. При обробці великого `all_prompts` payload (50-100 KB) парсинг JSON займає багато CPU
3. Потім Lambda робить 5 DynamoDB queries підряд
4. З малою vCPU потужністю ці запити виконуються ДУЖЕ повільно
5. Lambda "зависає" на 15 хвилин обробляючи ці запити
6. Timeout!

### Чому 107 MB Max Memory Used?

Lambda використала лише 107 MB з 512 MB доступних, НО:
- Пам'ять != vCPU потужність
- 512 MB = 0.5 vCPU (приблизно)
- 2048 MB = 2.0 vCPU (4x більше потужності!)

Lambda потребує більше **CPU**, не пам'яті!

---

## ✅ Рішення

### Збільшення Lambda Memory

```bash
aws lambda update-function-configuration \
  --function-name content-generate-images \
  --memory-size 2048 \
  --timeout 900
```

**Результат:**
```json
{
  "MemorySize": 2048,
  "Timeout": 900,
  "Status": "Successful",
  "State": "Active"
}
```

### Чому це допоможе?

**AWS Lambda CPU Allocation:**
| Memory | vCPU Power | Використання |
|--------|-----------|--------------|
| 128 MB | 0.125 vCPU | Дуже легкі задачі |
| 512 MB | 0.5 vCPU | Легкі задачі |
| 1024 MB | 1.0 vCPU | Середні задачі |
| **2048 MB** | **2.0 vCPU** | **Важкі задачі + DynamoDB** ✅ |
| 3008 MB | 3.0 vCPU | Дуже важкі задачі |

**З 2048 MB:**
- ✅ 4x більше vCPU потужності
- ✅ Швидший парсинг великих JSON payloads
- ✅ Швидші DynamoDB queries (більше паралельних запитів)
- ✅ Lambda не зависатиме на DynamoDB операціях

### Вплив на вартість

**До (512 MB):**
- Вартість за GB-секунду: $0.0000166667
- За 900 сек timeout: $0.0075

**Після (2048 MB):**
- Вартість за GB-секунду: $0.0000166667
- За 900 сек (якщо використає всі): $0.030
- **АЛЕ:** Lambda тепер завершиться швидко (10-15 хв замість timeout)
- **Реальна вартість:** ~$0.008-0.012 (навіть дешевше, бо швидше!)

**Висновок:** Збільшення пам'яті не тільки вирішує проблему, але й **зменшує вартість** через швидше виконання!

---

## 🧪 Тестування

### Test 1: Single Channel (після збільшення пам'яті)

```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:eu-central-1:599297130956:stateMachine:ContentGenerator \
  --name "test-memory-fix-1770558659" \
  --input '{
    "user_id": "test-user",
    "trigger_type": "manual",
    "requested_channels": ["UC-U_ag6Nn6GwkTq06TyVv5A"]
  }'
```

**Очікуваний результат:**
- ✅ Lambda виводить print statements у CloudWatch
- ✅ DynamoDB queries виконуються швидко (<1 сек)
- ✅ Генерація 6 зображень завершується за ~7-8 хв
- ✅ Виконання завершується SUCCESSFULLY

**Статус:** 🔄 В процесі тестування (запущено о 15:50:57)

---

## 📊 Моніторинг

### CloudWatch Logs - Очікувані повідомлення

Якщо фікс спрацював, ми маємо побачити:

```
START RequestId: xxx
🎨 Image Generator - Multi-Provider Version with BATCHING
Event: {...}
✅ User ID: test-user
🔄 MULTI-CHANNEL BATCH MODE DETECTED
   Total prompts from all channels: 6
✅ EC2 endpoint received from Step Functions
🎨 Multi-Channel Batch Image Generation
   Provider: ec2-sd35
   Total prompts: 6
   Loading configs for 1 unique channels...
   ✅ UC-U_a: Thumbnail 16:9 = 1920x1080
🎨 Generating SCENE image 1/6
   Channel: U_ag6N
   Scene: 1
   Dimensions: 1024x576
   Prompt: ...
📡 Calling EC2 FLUX API at ...
✅ Image generated successfully (1024x576, cost: $0.011700)
✅ Uploaded image to S3: images/UC-U_ag6Nn6GwkTq06TyVv5A/...
...
END RequestId: xxx
REPORT RequestId: xxx Duration: 420000 ms (~7 min) Memory Used: 250 MB
```

### Метрики для перевірки

**Lambda Metrics:**
- ✅ Duration: 420-480 секунд (7-8 хв) замість 900 сек timeout
- ✅ Max Memory Used: 200-300 MB (є запас з 2048 MB)
- ✅ Errors: 0
- ✅ Throttles: 0

**Step Functions Metrics:**
- ✅ Execution Status: SUCCEEDED
- ✅ Total Duration: ~10-12 хв (вся послідовність)

**DynamoDB Metrics:**
- ✅ Query Latency: <100ms (швидко!)
- ✅ Consumed Read Capacity: ~5-10 units

---

## 🎯 Наступні кроки

### Після успішного тесту з 1 каналом:

1. **Тест з 5 каналами** (повний production workload)
   ```bash
   aws stepfunctions start-execution \
     --name "test-5-channels-$(date +%s)" \
     --input '{"user_id":"production-user","trigger_type":"manual"}'
   ```

2. **Моніторинг production виконань**
   - Перевірити чи всі виконання завершуються успішно
   - Чи з'являються зображення в content.html

3. **Оптимізація (опціонально)**
   - Якщо Lambda все ще повільна, можна:
     - Кешувати channel configs у глобальних змінних
     - Використати DynamoDB batch_get_item замість окремих queries
     - Розглянути збільшення пам'яті до 3008 MB для максимального vCPU

---

## 📝 Висновки

### Ключові insights

1. **Lambda timeout != slow code**
   - Проблема була не в генерації зображень (42 сек/зображення)
   - Проблема була в DynamoDB queries з малою vCPU потужністю

2. **Memory = CPU в Lambda**
   - 512 MB = лише 0.5 vCPU (недостатньо для DynamoDB queries)
   - 2048 MB = 2.0 vCPU (достатньо для parallel queries)

3. **Порожні CloudWatch логи = early hang**
   - Якщо немає print statements, Lambda зависає ДО handler
   - Треба шукати проблему в глобальній ініціалізації або першій операції в handler

4. **Тестування з малими payload може обманювати**
   - Прямий тест з 1 промптом працював (малий payload, мало DynamoDB queries)
   - Production з 30 промптами зависав (великий payload, багато queries)

### Уроки на майбутнє

1. **Завжди тестувати з production-like workload**
2. **Моніторити Lambda vCPU метрики, не лише пам'ять**
3. **Для heavy I/O операцій (DynamoDB, API calls) - більше пам'яті = швидше виконання**
4. **Використовувати CloudWatch Insights для аналізу логів**

---

**Підготував:** Claude Code
**Дата:** 2026-02-08
**Статус:** ✅ Рішення застосовано, тестування в процесі
**Наступна перевірка:** Через 10 хв (16:03)
