# Root Cause Analysis: Чому Не Зберігаються Дані

**Дата**: 2026-02-12 00:45
**Проблема**: Content не зберігається в DynamoDB і відео не створюється в S3

---

## 🔍 Що Ми Знаємо

### Останній Успішний Запис
**Час**: 2026-02-11 21:21:34 UTC (23:21 за Kyiv)
**Content ID**: 20260211T21130026895
**Канал**: UCRmO5HB89GW_zjX3dJACfzw

**Що БУЛО збережено:**
- ✅ `content_id`: 20260211T21130026895
- ✅ `story_title`: The Forgotten Prophecy of the Lost Hero
- ✅ `scene_images`: 19 images з повною інформацією (url, prompt, cost, etc)
- ✅ `has_audio`: true (в метаданих)
- ✅ `has_images`: true (в метаданих)
- ✅ `narrative_data`, `cta_data`, `image_data`, etc

**Що НЕ було збережено:**
- ❌ `generated_images` field - взагалі не існує
- ❌ `audio_files`: [] - порожній список (хоча has_audio: true!)

### Після Наших Змін
**Тести о 22:22, 23:11, 00:22** - НІ ОДИН не зберіг дані в DynamoDB
**Workflow Status**: SUCCEEDED ✅
**Але**: Нічого не збереглося

---

## 🧐 Аналіз: Що Змінилося

### Зміна #1: ResultPath = null
**Що зробили:**
```python
phase3['ResultPath'] = None  # Was: $.finalResults
```

**Вплив:**
- Map state тепер НЕ зберігає результати ітерацій
- Це ПРАВИЛЬНО виправило DataLimitExceeded
- **АЛЕ**: Це могло вплинути на наступні стани після Map

### Зміна #2: Видалені JSONPath References
**Видалили з SaveFinalContent:**
- `voice_id.$`
- `voice_profile.$`
- `tts_service.$`

**Вплив:**
- Ці поля більше не передаються в Lambda
- Це ПРАВИЛЬНО виправило JSONPath errors
- **АЛЕ**: Lambda може очікувати ці поля

---

## 🎯 Гіпотези

### Гіпотеза #1: SaveFinalContent Не Викликається
**Ймовірність**: НИЗЬКА
**Чому**:
- CloudWatch logs показують виклики content-save-result
- Останній log stream: 00:24:23 (ПІСЛЯ нашого тесту)

### Гіпотеза #2: SaveFinalContent Отримує ПУСТІ Дані
**Ймовірність**: ВИСОКА ⭐
**Чому**:
- Map state з `ResultPath: null` не передає результати далі
- SaveFinalContent всередині Map iterator
- Він може НЕ мати доступу до `audioResult`, `scene_images`, etc.

### Гіпотеза #3: Lambda Падає з Помилкою
**Ймовірність**: СЕРЕДНЯ
**Чому**:
- Workflow SUCCEEDED (не показав би success якби Lambda failed)
- Але Lambda може повертати error в Payload, а workflow вважає це success

### Гіпотеза #4: Дані Передаються, Але НЕ Зберігаються
**Ймовірність**: СЕРЕДНЯ
**Чому**:
- Lambda `content-save-result` перевіряє багато умов
- Може fails на validation (наприклад, відсутній config_id)
- Workflow вважає це успіхом бо Lambda не throw exception

---

## 🔬 Що Треба Перевірити

### 1. Перевірити Input до SaveFinalContent
```bash
# In execution history, check TaskStateEntered for SaveFinalContent
# See what data is actually passed
```

**Очікуємо побачити:**
- `channel_id`: має бути
- `content_id`: має бути
- `config_id`: має бути
- `audio_files`: має бути список
- `generated_images` (aka `scene_images`): має бути список

### 2. Перевірити CloudWatch Logs
```bash
# Check content-save-result logs for errors
aws logs filter-log-events \
  --log-group-name "/aws/lambda/content-save-result" \
  --start-time <timestamp> \
  --filter-pattern "ERROR"
```

**Шукаємо:**
- Validation errors
- Missing fields errors
- DynamoDB put_item errors

### 3. Перевірити Output від SaveFinalContent
```bash
# In execution history, check TaskStateExited for SaveFinalContent
# See what Lambda returned
```

**Очікуємо побачити:**
- Success status або error message

---

## 💡 Можливі Рішення

### Рішення #1: Перемістити SaveFinalContent ПІСЛЯ Map
**Що робити:**
- Видалити SaveFinalContent з Map Iterator
- Додати його як окремий стан ПІСЛЯ Phase3AudioAndSave
- Передавати дані через S3 або збирати з DynamoDB

**Переваги:**
- Уникнемо проблем з ResultPath
- SaveFinalContent матиме доступ до всіх даних

**Недоліки:**
- Потребує рефакторингу Step Functions
- Може зламати існуючу логіку

### Рішення #2: Повернути ResultPath
**Що робити:**
- Змінити `ResultPath: null` назад на `ResultPath: $.finalResults`
- Але тоді повернеться DataLimitExceeded...

**Переваги:**
- SaveFinalContent матиме дані

**Недоліки:**
- DataLimitExceeded error вернеться для великих workflow

### Рішення #3: Передавати Дані Інакше
**Що робити:**
- Зберігати проміжні результати в S3
- SaveFinalContent читає з S3 замість Step Functions state
- Або: Кожен Lambda сам пише в DynamoDB

**Переваги:**
- Уникаємо DataLimitExceeded
- SaveFinalContent матиме дані

**Недоліки:**
- Потребує змін у багатьох Lambda
- Складніша архітектура

### Рішення #4: Змінити SaveFinalContent Mapping
**Що робити:**
- Перевірити, чи всі JSONPath references правильні
- Можливо `$.scene_images` більше не доступний через ResultPath: null
- Змінити на direct references до попередніх станів

**Переваги:**
- Мінімальні зміни

**Недоліки:**
- Може не працювати через ResultPath: null

---

## 🎬 Рекомендовані Наступні Кроки

1. **ПЕРШЕ**: Перевірити Input до SaveFinalContent в execution history
   - Подивитися, чи передаються `audio_files` і `generated_images`
   - Якщо НІ - проблема в ResultPath: null

2. **ДРУГЕ**: Якщо дані НЕ передаються:
   - Option A: Повернути ResultPath (але тоді DataLimit...)
   - Option B: Перемістити SaveFinalContent після Map
   - Option C: Зберігати дані в S3 проміжно

3. **ТРЕТЄ**: Якщо дані ПЕРЕДАЮТЬСЯ:
   - Перевірити CloudWatch logs для validation errors
   - Виправити Lambda якщо потрібно

---

## ⚠️ ВАЖЛИВО

**ПРОБЛЕМА НЕ В МІГРАЦІЇ Z-IMAGE/QWEN3-TTS!**

Міграція працює ідеально:
- ✅ Z-Image генерує images
- ✅ Qwen3-TTS генерує audio
- ✅ Workflow виконується до кінця

Проблема в **архітектурі Step Functions** і тому, як дані передаються між станами після зміни `ResultPath: null`.

---

## 📊 Timeline

- **21:21** - Останній успішний save (ДО наших змін)
- **21:32-22:00** - Ми робили зміни (ResultPath, voice_id fix, etc)
- **22:22** - Перший тест після змін - FAILED (DataLimit)
- **23:11** - Другий тест - SUCCEEDED (але нічого не збереглося)
- **00:22** - Третій тест - SUCCEEDED (але нічого не збереглося)

**Висновок**: Зміна ResultPath: null виправила DataLimitExceeded, але зламала save functionality.
