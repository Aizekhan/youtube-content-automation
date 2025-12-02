# 🎨 SD3.5 Medium - Система Генерації Зображень

**Версія:** 1.0
**Дата:** 2025-11-18
**Статус:** ✅ Production Ready
**Регіон:** eu-central-1

---

## 📋 Зміст

1. [Огляд](#огляд)
2. [Технічні характеристики](#технічні-характеристики)
3. [EC2 Старт/Стоп система](#ec2-стартстоп-система)
4. [API Endpoints](#api-endpoints)
5. [Інтеграція з Workflow](#інтеграція-з-workflow)
6. [Вартість та оптимізація](#вартість-та-оптимізація)
7. [Моніторинг](#моніторинг)

---

## Огляд

### Що це?

**SD3.5 Medium** - це система генерації високоякісних зображень на базі Stable Diffusion 3.5 Medium, що працює на виділеному EC2 інстансі з GPU.

### Чому SD3.5 замість Flux/SDXL?

| Критерій | SD3.5 Medium | Flux | SDXL (Bedrock) |
|----------|--------------|------|----------------|
| **Якість** | ⭐⭐⭐⭐⭐ Відмінна | ⭐⭐⭐⭐⭐ Відмінна | ⭐⭐⭐⭐ Добра |
| **Швидкість** | ~5.5 сек/зобр | ~20 сек/зобр | ~15 сек/зобр |
| **Вартість** | $0.09/зобр | $0.30/зобр | $0.40/зобр |
| **Контроль** | Повний | Повний | Обмежений (AWS) |
| **Масштабування** | On-demand EC2 | On-demand EC2 | API лімітований |

**Переваги SD3.5:**
- ✅ **Найшвидша генерація**: ~5.5 секунд на 1024x1024 зображення
- ✅ **Дешевша за Bedrock**: Економія 50-60% на великих об'ємах
- ✅ **Кращий промпт-слідування**: Точніше інтерпретує складні промпти
- ✅ **Автоматичний старт/стоп**: Економія на простої (лише EBS $8/місяць)
- ✅ **Повний контроль**: Налаштування параметрів, моделі, версій

---

## Технічні характеристики

### EC2 Instance

```
Instance ID:    i-0a71aa2e72e9b9f75
Instance Type:  g5.xlarge
GPU:            NVIDIA A10G (24GB VRAM)
Region:         eu-central-1
OS:             Ubuntu 22.04 LTS
Storage:        100GB gp3 EBS
```

### Встановлене ПЗ

```yaml
NVIDIA Driver: 580.105.08
CUDA:          12.1
Python:        3.10 (venv)
PyTorch:       2.x with CUDA support
Model:         Stable Diffusion 3.5 Medium (~12GB)
API Server:    Flask (systemd service, автостарт)
```

### Продуктивність

| Параметр | Значення |
|----------|----------|
| **Час генерації** (1024x1024, 28 steps) | ~5.5 секунд |
| **Паралельна обробка** | 6 зображень одночасно |
| **Batch 18 зображень** | ~90 секунд (3 батчі × 30 сек) |
| **VRAM використання** | ~13GB/24GB (54%) |
| **Storage використання** | ~48GB/100GB (48%) |

---

## EC2 Старт/Стоп система

### Автоматизація через Lambda

**Lambda Function:** `ec2-sd35-control`
**Призначення:** Керування EC2 інстансом (START/STOP/STATUS)

### Команди

#### START Instance
```json
{
  "action": "start"
}
```
**Результат:**
```json
{
  "state": "running",
  "endpoint": "http://63.178.196.66:5000",
  "ip": "63.178.196.66",
  "wait_time": "~90 секунд"
}
```

#### STOP Instance
```json
{
  "action": "stop"
}
```
**Результат:**
```json
{
  "state": "stopping"
}
```

#### CHECK Status
```json
{
  "action": "status"
}
```
**Результат:**
```json
{
  "state": "running|stopped|stopping|pending",
  "endpoint": "http://...:5000" // якщо running
}
```

### Workflow інтеграція

**Step Functions автоматично керує EC2:**

```
1. CollectAllImagePrompts
   ↓
2. CheckIfAnyImages (чи є зображення для генерації?)
   ↓
3. StartEC2ForAllImages ← Lambda викликає ec2-sd35-control
   │  • Запускає EC2
   │  • Чекає до running (~90 сек)
   │  • Перевіряє API health
   │  • Повертає endpoint
   ↓
4. GenerateAllImagesBatched (Map, 3 паралельні батчі)
   ↓
5. StopEC2AfterImages ← Lambda викликає ec2-sd35-control
   │  • Зупиняє EC2
   │  • Економія: платимо лише за час генерації
```

### Retry механізм

**Проблема:** AWS іноді не має вільних g5.xlarge інстансів (InsufficientInstanceCapacity)

**Рішення:** [SQS Retry System](SQS-RETRY-SYSTEM.md)

- **Швидкі спроби:** 3 спроби за 70 секунд
- **Довгострокові спроби:** До 20 спроб протягом 1 години (SQS + EventBridge)
- **Автоматичне відновлення:** Workflow продовжується після успішного старту

---

## API Endpoints

### Base URL

```
http://<EC2_IP>:5000
```

**ВАЖЛИВО:** IP змінюється після кожного STOP/START. Використовуйте IP з Lambda відповіді.

### Health Check

**Endpoint:** `GET /health`

**Request:**
```bash
curl http://63.178.196.66:5000/health
```

**Response:**
```json
{
  "status": "healthy",
  "model": "sd-3.5-medium",
  "model_loaded": true,
  "gpu": "NVIDIA A10G",
  "storage": {
    "ebs_100gb": {
      "total_gb": 96.73,
      "used_gb": 48.63,
      "free_gb": 48.08,
      "usage_percent": 50.3
    }
  }
}
```

### Generate Image

**Endpoint:** `POST /generate`

**Request:**
```bash
curl -X POST http://63.178.196.66:5000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A mystical ancient temple in a misty forest",
    "height": 1024,
    "width": 1024,
    "steps": 28,
    "guidance_scale": 3.5
  }' \
  --output image.png
```

**Параметри:**

| Параметр | Тип | Default | Опис |
|----------|-----|---------|------|
| `prompt` | string | **required** | Текстовий опис зображення |
| `height` | int | 1024 | Висота в пікселях (512-2048) |
| `width` | int | 1024 | Ширина в пікселях (512-2048) |
| `steps` | int | 28 | Кроки inference (20-50) |
| `guidance_scale` | float | 3.5 | Наскільки слідувати промпту (1.0-10.0) |

**Response:**
- Content-Type: `image/png`
- Binary PNG дані

**Час виконання:** ~5.5 секунд (1024x1024, 28 steps)

---

## Інтеграція з Workflow

### Фаза генерації зображень

**Повний процес:**

```
Phase 1: Content Generation (Parallel Map для кожного каналу)
  ├─ QueryTitles
  ├─ ThemeAgent
  └─ MegaNarrativeGenerator
       └─ Генерує image_data.prompts[] для кожної сцени

       ↓

Phase 2: Централізована генерація зображень

  ├─ CollectAllImagePrompts
  │   Збирає ВСІ промпти з усіх каналів
  │   Input:  phase1_results[] (кожен містить image_data)
  │   Output: collected_prompts {
  │             all_image_prompts: [...],  // всі промпти
  │             total_images: 54            // загальна кількість
  │           }
  │
  ├─ CheckIfAnyImages
  │   if total_images > 0 → продовжити
  │   if total_images = 0 → пропустити генерацію
  │
  ├─ StartEC2ForAllImages (Task)
  │   └─ Lambda: ec2-sd35-control
  │       ├─ Запускає EC2 instance
  │       ├─ Чекає до running (~90s)
  │       ├─ Перевіряє API health
  │       └─ Повертає endpoint URL
  │
  ├─ GenerateAllImagesBatched (Map, MaxConcurrency=3)
  │   └─ content-generate-images Lambda
  │       ├─ Отримує batch зображень (6 промптів)
  │       ├─ Викликає SD3.5 API паралельно
  │       ├─ Завантажує в S3
  │       └─ Час: ~30 секунд на батч
  │
  ├─ DistributeImagesToChannels (Task)
  │   └─ Розподіляє згенеровані зображення назад по каналам
  │
  └─ StopEC2AfterImages (Task)
      └─ Lambda: ec2-sd35-control
          └─ Зупиняє EC2 (економія коштів)

       ↓

Phase 3: Audio & Save (Parallel Map для кожного каналу)
  ├─ GenerateAudio (AWS Polly TTS)
  ├─ SaveFinalContent (DynamoDB)
  └─ Video Assembly
```

### Батчинг систем<br>
**Чому батчі?**
- SD3.5 на g5.xlarge може обробляти 6 зображень паралельно
- Оптимальне використання GPU VRAM (13GB/24GB)
- 3 батчі паралельно через Step Functions Map

**Приклад:**
```
Канал 1: 18 зображень
Канал 2: 18 зображень
Канал 3: 18 зображень
────────────────────────
Total:   54 зображення

Розподіл:
Batch 1: scenes 1-6   (3 канали × 2 сцени)
Batch 2: scenes 7-12  (3 канали × 2 сцени)
Batch 3: scenes 13-18 (3 канали × 2 сцени)
... і так далі для 9 батчів

Час: 9 батчів × 30 сек = ~4.5 хвилини
```

---

## Вартість та оптимізація

### Breakdown витрат

#### EC2 Running (під час генерації)
```
Instance Type: g5.xlarge
Cost:          $1.006/година
Typical run:   ~10 хвилин на генерацію
Per run:       $0.168
```

#### EC2 Stopped (більшість часу)
```
EC2 instance:  $0 (не платимо за stopped instance)
EBS Storage:   $8/місяць (100GB gp3)
```

#### Порівняння з альтернативами

**18 зображень (1 канал):**

| Сервіс | Вартість | Час |
|--------|----------|-----|
| **SD3.5 на EC2** | **$0.168** | **90 секунд** |
| Bedrock SDXL | $7.20 | ~4.5 хвилини |
| Replicate Flux | $5.40 | ~6 хвилин |

**Економія:**
- vs Bedrock: **97.7%** дешевше
- vs Flux: **96.9%** дешевше

### Оптимізація

✅ **Автоматичний STOP після генерації** - платимо лише за час роботи
✅ **Батчинг** - максимальне використання GPU
✅ **SQS Retry** - не втрачаємо гроші на failed runs
✅ **Паралельні запити** - 6 зображень одночасно
✅ **On-demand** - немає обов'язкових платежів, масштабуємо при потребі

---

## Моніторинг

### CloudWatch Logs

**Log Group:** `/aws/lambda/ec2-sd35-control`

**Що логуємо:**
- ✅ EC2 start/stop команди
- ✅ Час запуску інстансу
- ✅ Health check результати
- ✅ IP адреси та endpoints
- ✅ Помилки (InsufficientInstanceCapacity, timeouts)

### Dashboard метрики

**Перегляд через Dashboard:**
```
https://<your-domain>/dashboard.html
→ Flux Health Panel (показує SD3.5 статус)
```

**Метрики:**
- 🟢 Instance State (running/stopped)
- 📊 CPU/GPU використання
- 💾 Storage використання
- ⏱️ API response time
- 📈 Generations count

### Ручна перевірка

**SSH доступ:**
```bash
ssh -i /path/to/key.pem ubuntu@<EC2_IP>
```

**Перевірка сервісу:**
```bash
# Статус Flask API
sudo systemctl status sd-api.service

# Логи API
sudo journalctl -u sd-api.service -f

# GPU статус
nvidia-smi

# Storage
df -h
```

### Автоматичне Очищення Кешу

**Статус:** ✅ АКТИВНО (запускається кожної неділі о 3:00 AM UTC)

**Що очищається:**
- 🗑️ System logs (journalctl, /var/log) - старше 7 днів
- 🗑️ API логи (Flask) - старше 7 днів
- 🗑️ Тимчасові файли (/tmp, /var/tmp)

**Що НЕ очищається:**
- ✅ SD3.5 модель (~12GB)
- ✅ Python venv (~8GB)
- ✅ CUDA/System libraries
- ✅ Поточні логи (останні 7 днів)

**Результат:**
- Звільняє 200MB-2GB залежно від накопичення
- Підтримує disk usage на стабільному рівні (~48GB/100GB)
- Економить ~20-24GB диску за рік
- Не впливає на швидкість старту (залишається ~90 секунд)

**Моніторинг cleanup:**
```bash
# SSH на інстанс
ssh -i /tmp/aws-key.pem ubuntu@<INSTANCE_IP>

# Перевірити історію cleanup
tail -50 ~/logs-cleanup.log

# Перевірити розмір логів
sudo journalctl --disk-usage
sudo du -sh /var/log
```

**Документація:** [EC2-SD35-CACHE-MANAGEMENT.md](EC2-SD35-CACHE-MANAGEMENT.md)

---

## Швидкий старт

### 1. Запустити генерацію через Dashboard
```
1. Відкрити Dashboard → Content Generator
2. Вибрати канал(и)
3. Натиснути "Generate Content"
4. Система автоматично:
   - Запустить EC2
   - Згенерує зображення
   - Зупинить EC2
```

### 2. Ручний запуск EC2 (для тестування)

**Через AWS CLI:**
```bash
aws lambda invoke \
  --function-name ec2-sd35-control \
  --payload '{"action":"start"}' \
  --region eu-central-1 \
  response.json

cat response.json
```

### 3. Тестова генерація

**Після старту EC2:**
```bash
# Отримати IP з Lambda response
EC2_IP="63.178.196.66"

# Health check
curl http://$EC2_IP:5000/health

# Test generation
curl -X POST http://$EC2_IP:5000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A beautiful sunset over mountains",
    "steps": 28
  }' \
  --output test.png

# Перевірити результат
ls -lh test.png
```

---

## Troubleshooting

### EC2 не стартує (InsufficientInstanceCapacity)

**Симптом:** Lambda повертає помилку "No available capacity"

**Рішення:** Система автоматично використовує [SQS Retry System](SQS-RETRY-SYSTEM.md)
- Чекає 3 хвилини
- Пробує знову (до 20 разів протягом години)
- Workflow автоматично відновлюється після успішного старту

### API не відповідає після старту

**Симптом:** EC2 в стані "running", але `/health` повертає timeout

**Можливі причини:**
1. **Flask сервіс не стартував** - чекайте 30-60 секунд після instance start
2. **Security Group блокує** - перевірте що порт 5000 відкритий
3. **Service crashed** - SSH до instance, перевірте `sudo systemctl status sd-api.service`

**Fix:**
```bash
# SSH до instance
ssh -i key.pem ubuntu@<IP>

# Перезапустити сервіс
sudo systemctl restart sd-api.service

# Перевірити логи
sudo journalctl -u sd-api.service -f
```

### Зображення генеруються повільно

**Симптом:** Час генерації >10 секунд на зображення

**Можливі причини:**
1. **GPU не використовується** - модель на CPU
2. **Занадто високі параметри** - steps >40
3. **Недостатньо VRAM** - resolution >1024x1024

**Перевірка:**
```bash
# Перевірити GPU utilization
nvidia-smi

# Має показати:
# GPU 0: NVIDIA A10G
# Memory-Usage: ~13GB / 24GB
# GPU-Util: ~90-100% (під час генерації)
```

### Instance зупинився сам

**Це нормально!** Step Functions автоматично зупиняє EC2 після генерації для економії коштів.

Перевірте CloudWatch Logs → `/aws/lambda/ec2-sd35-control` для деталей.

---

## Корисні посилання

- [SQS Retry System](SQS-RETRY-SYSTEM.md) - Автоматичні повторні спроби
- [Image Batching System](IMAGE-BATCHING-SYSTEM.md) - Паралельна обробка
- [Video Assembly](VIDEO-ASSEMBLY-SYSTEM.md) - Монтаж відео з зображень
- [MEGA Generation Guide](MEGA-GENERATION-GUIDE.md) - Повний workflow

---

**Статус системи:** ✅ Production Ready (2025-11-18)
**Підтримка:** Автоматична через SQS Retry + CloudWatch Monitoring
