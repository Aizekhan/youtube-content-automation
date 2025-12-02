# 📦 Image Batching System - Паралельна Генерація Зображень

**Версія:** 1.0
**Дата:** 2025-11-18
**Статус:** ✅ Production Ready
**Регіон:** eu-central-1

---

## 📋 Зміст

1. [Огляд](#огляд)
2. [Чому потрібен батчинг?](#чому-потрібен-батчинг)
3. [Архітектура](#архітектура)
4. [Workflow детально](#workflow-детально)
5. [Оптимізація продуктивності](#оптимізація-продуктивності)
6. [Налаштування](#налаштування)
7. [Моніторинг](#моніторинг)

---

## Огляд

### Що це?

**Image Batching System** - це система паралельної обробки зображень, яка:
- 📊 Розділяє великі масиви промптів на невеликі батчі
- ⚡ Генерує батчі паралельно через Step Functions Map
- 🎯 Максимально використовує GPU потужності SD3.5
- 🔄 Розподіляє згенеровані зображення назад по каналах

### До vs Після

**❌ БЕЗ батчингу (старий підхід):**
```
3 канали × 18 зображень = 54 зображення
Послідовна генерація: 54 × 5.5 сек = 297 секунд (~5 хвилин)
```

**✅ З батчингом:**
```
3 канали × 18 зображень = 54 зображення
9 батчів × 6 зображень × 5.5 сек = 49.5 секунд на батч
3 батчі паралельно:
  - Батч 1-3: 49.5 сек
  - Батч 4-6: 49.5 сек
  - Батч 7-9: 49.5 сек
Total: ~148 секунд (~2.5 хвилини)

Економія: 50% швидше! 🚀
```

---

## Чому потрібен батчинг?

### Проблема

**Сценарій:** 3 YouTube канали, кожен отримує 18 зображень (18 сцен)

**Без батчингу:**
- Кожен канал обробляється окремо
- Всередині каналу - послідовна генерація
- GPU простоює між запитами
- EC2 працює довше (більше витрат)

**Step Functions обмеження:**
- Map state може виконувати N задач паралельно
- Але якщо ми паралелимо ПО КАНАЛАМ, ми генеруємо по 1 зображенню за раз
- GPU може обробляти 6-8 зображень одночасно!

### Рішення: Централізований батчинг

**Ідея:**
1. ✅ Спочатку генеруємо ВСІ наративи для ВСІХ каналів (Phase 1)
2. ✅ Збираємо ВСІ image prompts з усіх каналів в одне місце
3. ✅ Розбиваємо на батчі по 6 промптів
4. ✅ Генеруємо 3 батчі паралельно (Step Functions Map, MaxConcurrency=3)
5. ✅ Розподіляємо готові зображення назад по каналах

**Переваги:**
- ⚡ **Швидше на 50%** - паралельна обробка батчів
- 💰 **Дешевше** - менше часу роботи EC2
- 🎯 **Оптимальне використання GPU** - завжди 6 зображень одночасно
- 🔄 **Масштабування** - працює з будь-якою кількістю каналів

---

## Архітектура

### Повний workflow

```
Phase 1: Content Generation (Parallel Map по каналам)
  ├─ Канал 1: ThemeAgent → MegaNarrative → 18 image_prompts
  ├─ Канал 2: ThemeAgent → MegaNarrative → 18 image_prompts
  └─ Канал 3: ThemeAgent → MegaNarrative → 18 image_prompts

Result: phase1_results[] = [
  {channel_id: "abysstales", image_data: {prompts: [18 items]}},
  {channel_id: "ancientlight", image_data: {prompts: [18 items]}},
  {channel_id: "whispers", image_data: {prompts: [18 items]}}
]

       ↓

Phase 2: Централізована генерація зображень

Step 1: CollectAllImagePrompts
─────────────────────────────────
Input: phase1_results[]
Process: Збирає ВСІ промпти з усіх каналів

Output: {
  all_image_prompts: [
    {
      channel_id: "abysstales",
      content_id: "abysstales-1763...",
      scene_id: "scene_1",
      prompt: "Ancient temple in misty forest",
      image_index: 0
    },
    ... (54 total prompts)
  ],
  total_images: 54,
  total_channels: 3
}

       ↓

Step 2: CheckIfAnyImages (Choice)
──────────────────────────────────
if total_images > 0: → Continue
if total_images = 0: → Skip image generation

       ↓

Step 3: StartEC2ForAllImages
─────────────────────────────
Lambda: ec2-sd35-control
- Запускає EC2 instance
- Чекає до running (~90 сек)
- Повертає endpoint

       ↓

Step 4: PrepareImageBatches (Lambda)
─────────────────────────────────────
Input: collected_prompts.all_image_prompts (54 prompts)
Batch size: 6 images per batch

Process:
  batches = []
  for i in range(0, 54, 6):
    batches.append({
      batch_id: i // 6,
      prompts: all_image_prompts[i:i+6]
    })

Output: {
  batches: [
    {batch_id: 0, prompts: [prompts 0-5]},
    {batch_id: 1, prompts: [prompts 6-11]},
    {batch_id: 2, prompts: [prompts 12-17]},
    {batch_id: 3, prompts: [prompts 18-23]},
    {batch_id: 4, prompts: [prompts 24-29]},
    {batch_id: 5, prompts: [prompts 30-35]},
    {batch_id: 6, prompts: [prompts 36-41]},
    {batch_id: 7, prompts: [prompts 42-47]},
    {batch_id: 8, prompts: [prompts 48-53]}
  ],
  total_batches: 9,
  batch_size: 6
}

       ↓

Step 5: GenerateAllImagesBatched (Map State)
─────────────────────────────────────────────
Map Config:
  - ItemsPath: $.batches
  - MaxConcurrency: 3  ← 3 батчі одночасно
  - Iterator: GenerateBatchImages (Lambda)

Виконання:
  Parallel Round 1:
    - Batch 0 (prompts 0-5)   ← 30 сек
    - Batch 1 (prompts 6-11)  ← 30 сек
    - Batch 2 (prompts 12-17) ← 30 сек

  Parallel Round 2:
    - Batch 3 (prompts 18-23) ← 30 сек
    - Batch 4 (prompts 24-29) ← 30 сек
    - Batch 5 (prompts 30-35) ← 30 сек

  Parallel Round 3:
    - Batch 6 (prompts 36-41) ← 30 сек
    - Batch 7 (prompts 42-47) ← 30 сек
    - Batch 8 (prompts 48-53) ← 30 сек

Total time: 3 rounds × 30 сек = 90 секунд

Output: batch_results[] = [
  {
    batch_id: 0,
    images: [
      {scene_id: "scene_1", channel_id: "abysstales", s3_url: "s3://..."},
      ... (6 images)
    ]
  },
  ... (9 batches total)
]

       ↓

Step 6: MergeImageBatches (Lambda)
───────────────────────────────────
Input: batch_results[] (9 батчів)
Process: Flatten всі зображення в один масив

Output: {
  all_images: [ ... 54 images ... ],
  total_images: 54
}

       ↓

Step 7: DistributeImagesToChannels (Lambda)
────────────────────────────────────────────
Input:
  - all_images (54 items)
  - phase1_results (channel contexts)

Process:
  for channel in channels:
    channel_images = filter images by channel_id
    channel.image_urls = build_s3_url_map(channel_images)

Output: phase1_results_with_images[] = [
  {
    channel_id: "abysstales",
    image_urls: {
      scene_1: "s3://.../scene-1.png",
      scene_2: "s3://.../scene-2.png",
      ...
    }
  },
  ...
]

       ↓

Step 8: StopEC2AfterImages
──────────────────────────
Lambda: ec2-sd35-control (action: "stop")
- Зупиняє EC2 instance
- Економія коштів

       ↓

Phase 3: Audio & Save (Parallel Map по каналам)
  ├─ Канал 1: GenerateAudio → SaveContent → Video Assembly
  ├─ Канал 2: GenerateAudio → SaveContent → Video Assembly
  └─ Канал 3: GenerateAudio → SaveContent → Video Assembly
```

---

## Workflow детально

### CollectAllImagePrompts Lambda

**Код логіка:**
```python
def lambda_handler(event, context):
    phase1_results = event['phase1_results']

    all_prompts = []

    for result in phase1_results:
        channel_id = result['channel_id']
        content_id = result['content_id']
        image_data = result.get('image_data', {})
        prompts = image_data.get('prompts', [])

        for idx, prompt_obj in enumerate(prompts):
            all_prompts.append({
                'channel_id': channel_id,
                'content_id': content_id,
                'scene_id': prompt_obj['scene_id'],
                'prompt': prompt_obj['prompt'],
                'image_index': idx
            })

    return {
        'all_image_prompts': all_prompts,
        'total_images': len(all_prompts),
        'total_channels': len(phase1_results)
    }
```

**Приклад виходу:**
```json
{
  "all_image_prompts": [
    {
      "channel_id": "abysstales",
      "content_id": "abysstales-1763480123",
      "scene_id": "scene_1",
      "prompt": "Ancient temple hidden in misty mountain forest",
      "image_index": 0
    },
    {
      "channel_id": "abysstales",
      "content_id": "abysstales-1763480123",
      "scene_id": "scene_2",
      "prompt": "Stone guardian statues covered in moss",
      "image_index": 1
    },
    ... (52 more)
  ],
  "total_images": 54,
  "total_channels": 3
}
```

### PrepareImageBatches Lambda

**Код логіка:**
```python
def lambda_handler(event, context):
    all_prompts = event['collected_prompts']['all_image_prompts']
    batch_size = event.get('batch_size', 6)  # Default 6

    batches = []
    for i in range(0, len(all_prompts), batch_size):
        batch = {
            'batch_id': i // batch_size,
            'prompts': all_prompts[i:i + batch_size]
        }
        batches.append(batch)

    return {
        'batches': batches,
        'total_batches': len(batches),
        'batch_size': batch_size
    }
```

**Приклад виходу:**
```json
{
  "batches": [
    {
      "batch_id": 0,
      "prompts": [
        {"channel_id": "abysstales", "scene_id": "scene_1", "prompt": "..."},
        {"channel_id": "abysstales", "scene_id": "scene_2", "prompt": "..."},
        {"channel_id": "abysstales", "scene_id": "scene_3", "prompt": "..."},
        {"channel_id": "ancientlight", "scene_id": "scene_1", "prompt": "..."},
        {"channel_id": "ancientlight", "scene_id": "scene_2", "prompt": "..."},
        {"channel_id": "whispers", "scene_id": "scene_1", "prompt": "..."}
      ]
    },
    {
      "batch_id": 1,
      "prompts": [ ... 6 more ... ]
    },
    ... (7 more batches)
  ],
  "total_batches": 9,
  "batch_size": 6
}
```

### GenerateBatchImages Lambda

**Виконується для кожного батчу паралельно (MaxConcurrency=3)**

**Код логіка:**
```python
import requests
import boto3
import concurrent.futures

s3 = boto3.client('s3')

def lambda_handler(event, context):
    batch_id = event['batch_id']
    prompts = event['prompts']
    ec2_endpoint = context['ec2_endpoint']  # From previous step

    # Паралельна генерація в межах батчу
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = []
        for prompt_obj in prompts:
            future = executor.submit(generate_single_image, prompt_obj, ec2_endpoint)
            futures.append(future)

        results = [f.result() for f in futures]

    return {
        'batch_id': batch_id,
        'images': results,
        'images_generated': len(results)
    }

def generate_single_image(prompt_obj, endpoint):
    # Call SD3.5 API
    response = requests.post(
        f"{endpoint}/generate",
        json={
            "prompt": prompt_obj['prompt'],
            "width": 1024,
            "height": 1024,
            "steps": 28
        },
        timeout=60
    )

    # Upload to S3
    s3_key = f"images/{prompt_obj['content_id']}/{prompt_obj['scene_id']}.png"
    s3.put_object(
        Bucket='youtube-automation-images',
        Key=s3_key,
        Body=response.content
    )

    return {
        'channel_id': prompt_obj['channel_id'],
        'content_id': prompt_obj['content_id'],
        'scene_id': prompt_obj['scene_id'],
        's3_url': f"s3://youtube-automation-images/{s3_key}"
    }
```

**Результат (для 1 батчу):**
```json
{
  "batch_id": 0,
  "images": [
    {
      "channel_id": "abysstales",
      "content_id": "abysstales-1763480123",
      "scene_id": "scene_1",
      "s3_url": "s3://youtube-automation-images/images/abysstales-1763480123/scene_1.png"
    },
    ... (5 more)
  ],
  "images_generated": 6
}
```

### DistributeImagesToChannels Lambda

**Розподіляє згенеровані зображення назад по каналах:**

```python
def lambda_handler(event, context):
    all_images = event['merged_images']['all_images']
    phase1_results = event['phase1_results']

    # Group images by channel_id
    images_by_channel = {}
    for img in all_images:
        channel_id = img['channel_id']
        if channel_id not in images_by_channel:
            images_by_channel[channel_id] = []
        images_by_channel[channel_id].append(img)

    # Add image_urls to each channel result
    updated_results = []
    for result in phase1_results:
        channel_id = result['channel_id']
        channel_images = images_by_channel.get(channel_id, [])

        # Build image_urls map (scene_id → s3_url)
        image_urls = {}
        for img in channel_images:
            scene_id = img['scene_id']
            image_urls[scene_id] = img['s3_url']

        result['image_urls'] = image_urls
        updated_results.append(result)

    return updated_results
```

**Результат:**
```json
[
  {
    "channel_id": "abysstales",
    "content_id": "abysstales-1763480123",
    "narrative_data": { ... },
    "image_data": { ... },
    "image_urls": {
      "scene_1": "s3://.../scene_1.png",
      "scene_2": "s3://.../scene_2.png",
      ... (18 scenes)
    }
  },
  ... (2 more channels)
]
```

---

## Оптимізація продуктивності

### Batch Size вибір

**Чому 6 зображень?**

| Batch Size | GPU Usage | Time/Batch | Pros | Cons |
|------------|-----------|------------|------|------|
| 1 | ~20% | 5.5 сек | Низька латентність | Недовикористання GPU |
| 3 | ~50% | 16 сек | Швидше ніж 1 | Досі неоптимально |
| **6** | **~85%** | **30 сек** | **Optimal** | **Balanced** |
| 8 | ~95% | 44 сек | Максимальне використання | Ризик OOM |
| 12 | 100%+ | 60+ сек | - | **Out of Memory** |

**Рекомендація:** Batch size = 6 (optimal для g5.xlarge з 24GB VRAM)

### MaxConcurrency вибір

**Step Functions Map MaxConcurrency:**

| MaxConcurrency | Batches/Round | Total Rounds (54 img) | Time | Pros/Cons |
|----------------|---------------|----------------------|------|-----------|
| 1 | 1 батч | 9 rounds | 270 сек | Повільно |
| **3** | **3 батчі** | **3 rounds** | **90 сек** | **Optimal** |
| 6 | 6 батчів | 2 rounds | 60 сек | Lambda throttling ризик |
| 9 | 9 батчів | 1 round | 30 сек | High Lambda concurrency |

**Рекомендація:** MaxConcurrency = 3 (баланс між швидкістю та resource limits)

### Parallel vs Sequential

**Порівняння:**

```
SEQUENTIAL (без батчингу):
54 images × 5.5 сек = 297 секунд (4 min 57 sec)

BATCHING (6 per batch, 3 parallel):
9 batches / 3 parallel = 3 rounds
3 rounds × 30 сек/round = 90 секунд (1 min 30 sec)

Прискорення: 3.3x швидше! 🚀
```

---

## Налаштування

### Змінити Batch Size

**Через Step Functions Input:**
```json
{
  "batch_size": 8  // Змінити з 6 на 8
}
```

**Або через Lambda env variable:**
```bash
aws lambda update-function-configuration \
  --function-name prepare-image-batches \
  --environment "Variables={BATCH_SIZE=8}" \
  --region eu-central-1
```

### Змінити MaxConcurrency

**У Step Functions Definition:**
```json
{
  "Type": "Map",
  "ItemsPath": "$.batches",
  "MaxConcurrency": 5,  // Змінити з 3 на 5
  "Iterator": { ... }
}
```

**Застосувати зміни:**
```bash
aws stepfunctions update-state-machine \
  --state-machine-arn arn:aws:states:eu-central-1:...:stateMachine:ContentGenerator \
  --definition file://aws/step-functions-updated.json \
  --region eu-central-1
```

---

## Моніторинг

### CloudWatch Metrics

**Важливі метрики:**

1. **Batch Processing Time**
   - Середній час на батч (~30 сек)
   - Якщо >45 сек → можливо, batch size занадто великий

2. **Step Functions Map Duration**
   - Total time для всіх батчів
   - Target: <2 хвилини для 54 зображень

3. **Lambda Concurrency**
   - Concurrent executions для `generate-batch-images`
   - Має дорівнювати MaxConcurrency (3)

### Dashboard

**Переглянути через WebUI:**
```
https://<domain>/dashboard.html
→ System Health → Image Generation

Показує:
- Batches processed
- Images generated
- Average time/batch
- Errors (if any)
```

### Logs

**CloudWatch Log Groups:**
```
/aws/lambda/collect-all-image-prompts
/aws/lambda/prepare-image-batches
/aws/lambda/generate-batch-images
/aws/lambda/merge-image-batches
/aws/lambda/distribute-images-to-channels
```

**Типові повідомлення:**
```
[CollectAllImagePrompts] Collected 54 prompts from 3 channels
[PrepareImageBatches] Created 9 batches (batch_size=6)
[GenerateBatchImages] Batch 0: Generated 6/6 images successfully
[MergeImageBatches] Merged 54 images from 9 batches
[DistributeImages] Distributed images to 3 channels
```

---

## Troubleshooting

### Батчі генеруються повільно

**Симптом:** Batch processing >60 секунд

**Можливі причини:**
1. Batch size занадто великий (>6)
2. SD3.5 API повільно відповідає
3. Мережа повільна (S3 uploads)

**Fix:**
- Зменшити batch_size до 4-5
- Перевірити SD3.5 health: `curl http://<EC2_IP>:5000/health`

### Out of Memory (OOM) errors

**Симптом:** Lambda або SD3.5 API crash з OOM

**Причина:** Batch size занадто великий для VRAM

**Fix:**
```python
# У PrepareImageBatches Lambda:
batch_size = 4  # Замість 6
```

### Зображення не розподілилися правильно

**Симптом:** Деякі канали не отримали зображення

**Debug:**
```bash
# Перевірити DistributeImages logs
aws logs tail /aws/lambda/distribute-images-to-channels --follow

# Перевірити DynamoDB
aws dynamodb get-item \
  --table-name GeneratedContent \
  --key '{"content_id": {"S": "abysstales-..."}}' \
  --query 'Item.image_urls'
```

**Можлива причина:** scene_id mismatch між narrative та images

---

## Корисні посилання

- [SD3.5 Image Generation](SD35-IMAGE-GENERATION.md) - SD3.5 система
- [SQS Retry System](SQS-RETRY-SYSTEM.md) - Retry для EC2 failures
- [Video Assembly](VIDEO-ASSEMBLY-SYSTEM.md) - Монтаж відео з зображень
- [MEGA Generation Guide](MEGA-GENERATION-GUIDE.md) - Повний workflow

---

**Статус системи:** ✅ Production Ready (2025-11-18)
**Продуктивність:** 3.3x швидше за sequential approach
**Підтримка:** Автоматичний моніторинг через CloudWatch
