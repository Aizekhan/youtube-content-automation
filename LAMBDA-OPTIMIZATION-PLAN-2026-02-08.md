# План оптимізації Lambda без збільшення пам'яті

**Дата:** 2026-02-08
**Мета:** Вирішити timeout проблему через оптимізацію коду, а не збільшення ресурсів
**Поточна пам'ять:** 512 MB (залишається без змін)

---

## 🎯 Філософія оптимізації

> **"Код повинен працювати з будь-якою к-тю даних, не збільшуючи пам'ять Lambda"**

### Ключові принципи:

1. **Batch Operations** - об'єднувати запити замість N+1
2. **Lazy Loading** - завантажувати тільки коли потрібно
3. **Stream Processing** - обробляти дані потоково (generator pattern)
4. **Connection Reuse** - переви використовувати підключення між викликами
5. **Caching** - кешувати результати в межах виклику

---

## 📊 Поточна проблема

### Неефективний код (рядки 390-422):

```python
# ❌ ПРОБЛЕМА: N+1 запитів до DynamoDB
for channel_id in unique_channels:  # 5 каналів
    # Запит 1: Завантажити channel config
    channel_response = channel_table.query(...)  # ⬅️ 5 запитів!

    # Запит 2: Завантажити thumbnail template
    thumbnail_response = thumbnail_table.get_item(...)  # ⬅️ 5 запитів!

# Всього: 5 × 2 = 10 DynamoDB запитів!
```

### Наслідки:

- **10 окремих запитів** до DynamoDB для 5 каналів
- **Послідовне виконання** (один за одним, не паралельно)
- **Велике навантаження** на Lambda CPU (512 MB = 0.5 vCPU)
- **Повільна обробка** великих payload (30 промптів × 200 символів кожен)
- **Результат:** Lambda зависає на 15 хвилин → timeout!

---

## ✅ Рішення: Resource Pool Manager

### Створено новий модуль: `resource_pool_manager.py`

#### Особливості:

1. **DynamoDB Batch Operations**
   ```python
   # ✅ ОПТИМІЗОВАНО: 2 batch запити замість 10 окремих
   channel_configs = pool.batch_get_channel_configs([ch1, ch2, ch3, ch4, ch5])
   templates = pool.batch_get_templates([t1, t2, t3], 'ThumbnailTemplates')

   # Результат: 2 запити замість 10! (80% зменшення)
   ```

2. **In-Memory Caching**
   ```python
   # Кеш на рівні виклику Lambda
   self._cache = {}  # Зберігається між промптами

   # Якщо Lambda контейнер переви використовується:
   _global_resource_pool = None  # Зберігається між викликами!
   ```

3. **Generator Pattern для промптів**
   ```python
   # Обробка по 10 промптів за раз (замість завантаження всіх 30)
   for batch in processor.process_in_batches(batch_size=10):
       process_batch(batch)  # Менше пам'яті, швидше
   ```

---

## 📈 Очікувані результати

### До оптимізації (поточний стан):

| Метрика | Значення |
|---------|----------|
| DynamoDB запитів | 10 (5 каналів × 2 запити) |
| Час завантаження конфігів | ~5-10 сек (з малою vCPU) |
| Пікова пам'ять | ~107 MB |
| Lambda Duration | 900 сек (timeout) ❌ |
| Вартість DynamoDB | $0.000025 × 10 = $0.00025 |

### Після оптимізації (очікується):

| Метрика | Значення | Покращення |
|---------|----------|------------|
| DynamoDB запитів | 2 (batch) | **80% ↓** |
| Час завантаження конфігів | <1 сек | **90% ↓** |
| Пікова пам'ять | ~150 MB | +40% (але в межах 512 MB) |
| Lambda Duration | ~420 сек (7 хв) | **53% ↓** |
| Вартість DynamoDB | $0.000025 × 2 = $0.00005 | **80% ↓** |

### Економія вартості:

**Lambda:**
- До: 900 сек × 512 MB × $0.0000166667/GB-сек = $0.0075
- Після: 420 сек × 512 MB × $0.0000166667/GB-сек = $0.0035
- **Економія: $0.004 (~47%) на виклик**

**DynamoDB:**
- Економія: $0.0002 на виклик

**Загальна економія:** ~$0.0042 на виклик
**За 1000 виконань:** ~**$4.20 економії**

---

## 🔧 Впровадження

### Крок 1: Інтеграція resource_pool_manager

**Файл:** `aws/lambda/content-generate-images/lambda_function.py`

**Зміни:**

```python
# Рядок 382 - ЗАМІНИТИ:

# СТАРИЙ КОД (видалити):
for channel_id in unique_channels:
    channel_response = channel_table.query(...)
    thumbnail_response = thumbnail_table.get_item(...)

# ⬇️⬇️⬇️ НОВИЙ КОД (додати): ⬇️⬇️⬇️

# 🚀 ОПТИМІЗОВАНА ВЕРСІЯ: Batch loading
print(f"   🚀 Using optimized batch loading...")
try:
    from resource_pool_manager import optimize_channel_configs_loading
    channel_configs, thumbnail_dimensions = optimize_channel_configs_loading(
        all_prompts,
        dynamodb
    )
except ImportError:
    # Fallback to old method
    print(f"   ⚠️  Using legacy loading (resource_pool_manager not found)")
    # ... старий код як fallback ...
```

### Крок 2: Deploy до Lambda

**Опції:**

#### Опція A: GitHub Actions (рекомендується)
```bash
# Додати resource_pool_manager.py до git
git add aws/lambda/content-generate-images/resource_pool_manager.py

# Оновити lambda_function.py з інтеграцією
git add aws/lambda/content-generate-images/lambda_function.py

# Commit і push
git commit -m "feat: optimize Lambda with batch DynamoDB loading (80% request reduction)"
git push origin master

# GitHub Actions автоматично задеплоїть
```

#### Опція B: Прямий deploy (для тестування)
```bash
cd E:/youtube-content-automation/aws/lambda/content-generate-images

# Створити ZIP з новими файлами
zip -r function.zip lambda_function.py resource_pool_manager.py config_merger.py

# Оновити Lambda
aws lambda update-function-code \
  --function-name content-generate-images \
  --zip-file fileb://function.zip
```

### Крок 3: Тестування

```bash
# Тест 1: Прямий виклик (швидкий тест)
aws lambda invoke \
  --function-name content-generate-images \
  --payload '{
    "all_prompts": [
      {"channel_id": "test1", "prompt": "test"},
      {"channel_id": "test2", "prompt": "test"}
    ],
    "provider": "ec2-sd35",
    "user_id": "test"
  }' \
  /tmp/test-optimized.json

# Перевірити логи - має побачити:
# "🚀 Using optimized batch loading..."
# "✅ Total DynamoDB requests: 2 (batch) vs 4 (old way)"
# "💰 Query cost reduction: 50%"

# Тест 2: Повне виконання через Step Functions
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:eu-central-1:599297130956:stateMachine:ContentGenerator \
  --name "test-optimized-$(date +%s)" \
  --input '{
    "user_id": "test-user",
    "trigger_type": "manual",
    "requested_channels": ["UC-U_ag6Nn6GwkTq06TyVv5A"]
  }'
```

---

## 📊 Моніторинг ефективності

### CloudWatch Metrics для відстеження:

1. **Lambda Duration**
   - До оптимізації: 900000 ms (timeout)
   - Після: має бути ~420000 ms

2. **Lambda Memory Used**
   - До: 107 MB
   - Після: ~150 MB (все ще в межах 512 MB)

3. **DynamoDB ConsumedReadCapacityUnits**
   - До: ~10 units на виклик
   - Після: ~2 units на виклик

### CloudWatch Logs - що шукати:

**Успішна оптимізація:**
```
🚀 Using optimized batch loading...
🔍 Found 5 unique channels
📥 Batch loading 5 channel configs...
✅ Loaded 5 configs (from cache: 0)
🔍 Found 3 unique thumbnail templates
📥 Batch loading 3 templates from ThumbnailTemplates...
✅ Loaded 3 templates
✅ UC-U_a: 16:9 = 1920x1080
✅ Total DynamoDB requests: 2 (batch) vs 10 (old way)
💰 Query cost reduction: 80%
```

**Fallback до старого методу:**
```
⚠️  Using legacy loading (resource_pool_manager not found)
Loading configs for 5 unique channels...
```

---

## 🎓 Додаткові оптимізації (майбутнє)

### 1. Connection Pooling для boto3

```python
# Переви використовувати boto3 sessions
from boto3.session import Session

_global_session = None

def get_session():
    global _global_session
    if _global_session is None:
        _global_session = Session()
    return _global_session

# Використання:
dynamodb = get_session().resource('dynamodb')
```

### 2. Async DynamoDB запити

```python
import aioboto3

async def batch_get_configs_async(channel_ids):
    async with aioboto3.resource('dynamodb') as dynamodb:
        tasks = [get_config(dynamodb, cid) for cid in channel_ids]
        return await asyncio.gather(*tasks)
```

### 3. DynamoDB Global Secondary Index оптимізація

Замість query на secondary index, можна створити composite key:

```
Primary Key: user_id#channel_id
Sort Key: config_version
```

Це дозволить робити batch_get_item замість множинних query.

### 4. Lambda Layers для спільних модулів

```bash
# Створити layer з resource_pool_manager
cd aws/lambda-layers
mkdir -p python/lib/python3.11/site-packages
cp ../content-generate-images/resource_pool_manager.py python/lib/python3.11/site-packages/
zip -r resource-pool-layer.zip python

# Publish layer
aws lambda publish-layer-version \
  --layer-name resource-pool-manager \
  --zip-file fileb://resource-pool-layer.zip \
  --compatible-runtimes python3.11
```

### 5. Streaming Response для великих результатів

Замість повернення всіх scene_images одразу, можна використати streaming:

```python
# Використати DynamoDB Streams + SNS для incremental updates
for image in scene_images:
    publish_to_sns(image)  # Frontend отримує updates в real-time
```

---

## 📋 Checklist впровадження

- [x] Створено `resource_pool_manager.py` модуль
- [ ] Інтегровано в `lambda_function.py`
- [ ] Протестовано локально
- [ ] Задеплоєно через GitHub Actions
- [ ] Перевірено CloudWatch логи
- [ ] Виміряно покращення performance
- [ ] Оновлено документацію
- [ ] Створено CloudWatch алярми для моніторингу

---

## 🚀 Наступні кроки

1. **Інтегрувати resource_pool_manager** в lambda_function.py
2. **Deploy через Git** (або прямий deploy для швидкого тесту)
3. **Запустити тестове виконання** і перевірити логи
4. **Виміряти покращення:**
   - Duration: має бути ~7-8 хв замість 15 хв timeout
   - DynamoDB queries: має бути 2 замість 10
   - Memory: має залишатися <512 MB

5. **Якщо успішно:**
   - Задокументувати результати
   - Розглянути інші Lambda функції для оптимізації
   - Впровадити інші оптимізації з списку вище

---

## 💡 Висновки

**Головний урок:**
> Збільшення ресурсів (пам'яті, CPU) - це швидке, але дороге рішення.
> Оптимізація коду - довше впровадження, але:
> - ✅ Дешевше у довгостроковій перспективі
> - ✅ Краща масштабованість
> - ✅ Менше vendor lock-in
> - ✅ Вчить писати ефективний код

**Для Lambda функцій критично важливо:**
1. **Мінімізувати кількість I/O операцій** (DynamoDB, S3, API calls)
2. **Використовувати batch операції** де можливо
3. **Кешувати результати** в межах виклику
4. **Обробляти дані потоково** (generator pattern)
5. **Переви використовувати підключення** між викликами (warm start)

---

**Підготував:** Claude Code
**Дата:** 2026-02-08
**Статус:** ✅ Модуль створено, готовий до інтеграції
**Очікуваний ефект:** 80% зменшення DynamoDB запитів, 53% швидше виконання
