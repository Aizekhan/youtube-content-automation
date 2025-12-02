# 🎤 TTS Provider Architecture - Implementation Summary

**Date**: 2025-11-25
**Architecture Version**: 2.0 (Provider-based)

## ✅ Що було реалізовано

### 1. Lambda Layer: `tts-common`

**Локація**: `aws/lambda-layers/tts-common/`

Спільна бібліотека для всіх TTS Lambda функцій:

- ✅ **BaseTTSProvider** - абстрактний базовий клас
- ✅ **config_merger.py** - мапінг голосів між провайдерами
- ✅ **ssml_validator.py** - валідація та фіксинг SSML
- ✅ **cost_logger.py** - універсальний логер витрат

**Переваги**:
- Розмір кожної Lambda зменшився з ~50KB до ~5KB
- DRY принцип - код не дублюється
- Легко оновлювати спільну логіку

---

### 2. Lambda: `content-audio-polly`

**Локація**: `aws/lambda/content-audio-polly/`

AWS Polly TTS provider (Neural + Standard):

- ✅ **PollyProvider клас** - наслідує BaseTTSProvider
- ✅ **Підтримка Neural та Standard** engines
- ✅ **Автоматичний fallback** Neural → Standard
- ✅ **SSML валідація** та auto-fixing
- ✅ **Cost tracking** до DynamoDB

**Характеристики**:
- Runtime: Python 3.11
- Memory: 512 MB
- Timeout: 60s
- Package size: ~5 KB (без Layer)

**Підтримувані голоси**:
- US: Matthew, Joey, Justin, Kevin, Stephen, Joanna, Kendra, Kimberly, Salli, Ruth, Danielle, Ivy
- UK: Brian, Amy, Emma, Arthur
- AU: Nicole, Olivia
- IN: Kajal

---

### 3. Lambda: `content-audio-elevenlabs`

**Локація**: `aws/lambda/content-audio-elevenlabs/`

ElevenLabs TTS provider:

- ✅ **ElevenLabsProvider клас** - наслідує BaseTTSProvider
- ✅ **Три моделі**: Turbo v2.5, Multilingual v2, English v1
- ✅ **8+ голосів** (male/female)
- ✅ **Автоматичне stripping SSML** (ElevenLabs не підтримує SSML)
- ✅ **API key з Secrets Manager**
- ✅ **Cost tracking** до DynamoDB

**Характеристики**:
- Runtime: Python 3.11
- Memory: 512 MB
- Timeout: 300s (5 min) - ElevenLabs може бути повільний
- Package size: ~2 MB (з requests library)

**Підтримувані голоси**:
- Male: adam, antoni, josh, sam
- Female: bella, rachel, domi, elli

---

### 4. Step Functions: TTS Routing

**Локація**: `aws/step-functions-tts-provider-routing.json`

Choice State для роутингу між TTS провайдерами:

```
GetTTSConfig
    ↓
RouteTTSProvider (Choice)
    ├─ aws_polly_neural → content-audio-polly
    ├─ aws_polly_standard → content-audio-polly
    ├─ elevenlabs → content-audio-elevenlabs
    └─ google_tts → content-audio-google (future)
    ↓ (on error)
FallbackToPolly
```

**Фічі**:
- ✅ Автоматичний вибір провайдера на основі `tts_service`
- ✅ Fallback до AWS Polly при помилці
- ✅ Retry логіка для кожного провайдера
- ✅ Уніфікований output формат

---

## 📂 Структура файлів

```
youtube-content-automation/
├── aws/
│   ├── lambda-layers/
│   │   └── tts-common/                      ← Lambda Layer
│   │       ├── python/
│   │       │   └── tts_common/
│   │       │       ├── __init__.py
│   │       │       ├── base_provider.py     ← Базовий клас
│   │       │       ├── config_merger.py     ← Voice mapping
│   │       │       ├── ssml_validator.py    ← SSML validation
│   │       │       └── cost_logger.py       ← Cost tracking
│   │       └── README.md
│   │
│   ├── lambda/
│   │   ├── content-audio-polly/             ← AWS Polly Lambda
│   │   │   ├── lambda_function.py
│   │   │   ├── polly_provider.py
│   │   │   ├── create_zip.py
│   │   │   └── README.md
│   │   │
│   │   └── content-audio-elevenlabs/        ← ElevenLabs Lambda
│   │       ├── lambda_function.py
│   │       ├── elevenlabs_provider.py
│   │       ├── requirements.txt             (requests)
│   │       ├── create_zip.py
│   │       └── README.md
│   │
│   └── step-functions-tts-provider-routing.json  ← Step Functions
│
├── TTS-PROVIDER-ARCHITECTURE.md            ← Deployment Guide
├── TTS-ARCHITECTURE-SUMMARY.md             ← This file
└── deploy-tts-providers.sh                 ← One-click deploy script
```

---

## 🚀 Deployment

### Швидкий деплой (рекомендовано):

```bash
chmod +x deploy-tts-providers.sh
./deploy-tts-providers.sh
```

### Ручний деплой:

Див. `TTS-PROVIDER-ARCHITECTURE.md` для детальних інструкцій.

---

## 🔧 Конфігурація

### Додати в ChannelConfigs:

```json
{
  "config_id": "channel_config_001",
  "channel_id": "UCRmO5HB89GW_zjX3dJACfzw",
  "channel_name": "My Channel",

  "tts_service": "elevenlabs",        ← ADD THIS
  "tts_voice_profile": "adam_male",   ← Existing field
  "elevenlabs_model": "turbo"         ← ADD THIS (optional)
}
```

### Підтримувані значення `tts_service`:

| Значення | Провайдер | Lambda Function |
|----------|-----------|-----------------|
| `aws_polly_neural` | AWS Polly Neural | content-audio-polly |
| `aws_polly_standard` | AWS Polly Standard | content-audio-polly |
| `elevenlabs` | ElevenLabs | content-audio-elevenlabs |
| `google_tts` | Google TTS (future) | content-audio-google |

**Default**: `aws_polly_neural`

---

## 📊 Порівняння провайдерів

### Якість vs Ціна

| Провайдер | Модель | Якість | Швидкість | Ціна/1M chars | 10-min video |
|-----------|--------|--------|-----------|---------------|--------------|
| AWS Polly | Neural | ⭐⭐⭐ | ⚡⚡⚡ | $16 | $0.128 |
| AWS Polly | Standard | ⭐⭐ | ⚡⭐⚡⚡ | $4 | $0.032 |
| ElevenLabs | Turbo v2.5 | ⭐⭐⭐⭐ | ⚡⚡ | $30 | $0.24 |
| ElevenLabs | Multilingual v2 | ⭐⭐⭐⭐⭐ | ⚡ | $240 | $1.92 |

### Рекомендації:

- **Звичайні канали** → AWS Polly Neural (якість/ціна)
- **Преміум канали** → ElevenLabs Turbo (найкраща якість)
- **Високий об'єм** → AWS Polly Standard (економія)

---

## 🎯 Переваги нової архітектури

### ✅ Масштабованість
- Легко додати нові TTS провайдери (Google, Azure, PlayHT)
- Кожна Lambda масштабується незалежно
- Різні timeout/memory для різних провайдерів

### ✅ Надійність
- Автоматичний fallback до AWS Polly
- Ізольовані помилки - якщо ElevenLabs падає, Polly працює
- Retry логіка для кожного провайдера

### ✅ Економія
- Малий розмір Lambda → швидкий cold start
- Платиш тільки за використані провайдери
- Оптимізовані timeout для кожного провайдера

### ✅ Підтримка
- Single Responsibility Principle
- Чистий код з патернами проектування
- Легко тестувати та дебажити

---

## 🧪 Тестування

### 1. Test Lambda Layer

```bash
cd aws/lambda-layers/tts-common/python
python3 -c "from tts_common import BaseTTSProvider; print('✅ Layer OK')"
```

### 2. Test Polly Lambda

```bash
aws lambda invoke \
  --function-name content-audio-polly \
  --payload '{"channel_id":"test","narrative_id":"test","tts_service":"aws_polly_neural","tts_voice_profile":"matthew_male","scenes":[{"scene_number":1,"text_with_ssml":"<speak>Hello</speak>"}]}' \
  --region eu-central-1 \
  test-polly.json

cat test-polly.json
```

### 3. Test ElevenLabs Lambda

```bash
aws lambda invoke \
  --function-name content-audio-elevenlabs \
  --payload '{"channel_id":"test","narrative_id":"test","tts_service":"elevenlabs","tts_voice_profile":"adam_male","scenes":[{"scene_number":1,"text_with_ssml":"Hello"}]}' \
  --region eu-central-1 \
  test-elevenlabs.json

cat test-elevenlabs.json
```

### 4. Test Step Functions

```bash
# Start execution
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:eu-central-1:599297130956:stateMachine:ContentGenerator \
  --name test-tts-routing-$(date +%s) \
  --region eu-central-1

# Monitor execution
aws stepfunctions describe-execution \
  --execution-arn <execution-arn> \
  --region eu-central-1
```

---

## 📝 TODO (Майбутнє)

- [ ] Додати Google Cloud TTS provider
- [ ] Додати Azure TTS provider
- [ ] Реалізувати A/B тестування провайдерів
- [ ] Додати metrics та моніторинг
- [ ] Оптимізувати cost tracking
- [ ] Додати caching для частих запитів

---

## 🤝 Співпраця

Архітектура розроблена спільно:
- **AI Assistant (Claude)**: Дизайн архітектури, код, документація
- **Human**: Вимоги, рев'ю, тестування

**Результат**: Професійна, масштабована, надійна система! 🚀

---

**Version**: 2.0
**Status**: ✅ Ready for Deployment
**Next**: Deploy → Test → Scale
