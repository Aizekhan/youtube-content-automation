# Template System Structure

## 📊 DynamoDB Tables

### 1. PromptTemplatesV2 (існує)
**Types**: Theme Templates, Narrative Templates

**Purpose**: Text-based AI prompts for OpenAI (theme generation & narrative/SSML)

**Key Features**:
- Theme generation prompts
- Narrative templates with SSML parameters
- Stores `text` + `ssml_params`, generates SSML on-the-fly per TTS service

**Schema**: See `aws/dynamodb-schemas/PromptTemplatesV2-updated-schema.json`

---

### 2. ImageGenerationTemplates (нова ✨)
**Type**: Image Generation Templates

**Purpose**: AI image generation prompts for DALL-E, Midjourney, Stable Diffusion, Leonardo

**Key Features**:
- Base prompt with variables
- Style modifiers
- Negative prompts
- Quality settings per AI service
- Aspect ratio support

**Schema**: See `aws/dynamodb-schemas/ImageGenerationTemplates-schema.json`

**Example**:
```json
{
  "template_id": "img_template_horror_001",
  "template_name": "Cinematic Horror Scene",
  "ai_service": "stable-diffusion",
  "prompt_structure": {
    "base_prompt": "Cinematic shot, {scene_description}, dark moody lighting, film grain, 4K",
    "style_modifiers": ["photorealistic", "cinematic", "atmospheric"],
    "negative_prompt": "cartoon, anime, low quality, blurry",
    "aspect_ratio": "16:9"
  }
}
```

---

### 3. VideoEditingTemplates (нова ✨)
**Type**: Video Editing Templates

**Purpose**: Video editing parameters: transitions, effects, pacing, audio mixing

**Key Features**:
- Scene duration settings
- Transition types with weights
- Visual effects (color grading, vignette, film grain)
- Pacing control (slow/medium/fast)
- Audio mixing (voice/music/sfx volumes)
- Export settings (resolution, fps, codec)

**Schema**: See `aws/dynamodb-schemas/VideoEditingTemplates-schema.json`

**Example**:
```json
{
  "template_id": "video_template_mystery_001",
  "template_name": "Fast-Paced Mystery Edit",
  "editing_params": {
    "scene_duration": {"min": 3, "max": 8, "unit": "seconds"},
    "transitions": [
      {"type": "cut", "weight": 0.7},
      {"type": "fade", "duration": 0.5, "weight": 0.2}
    ],
    "effects": {
      "color_grading": "moody-dark",
      "vignette": true,
      "film_grain": 0.3
    },
    "pacing": "fast"
  }
}
```

---

### 4. CTATemplates (нова ✨)
**Type**: CTA (Call-to-Action) Templates

**Purpose**: Subscribe buttons, like prompts, end screens with voice-over

**Key Features**:
- CTA type (subscribe, like, comment, etc.)
- Position (start, middle, end, overlay)
- Visual layout (background, gradients, images)
- Elements (text, buttons, icons)
- Animations (entrance/exit)
- Optional voice-over with SSML

**Schema**: See `aws/dynamodb-schemas/CTATemplates-schema.json`

**Example**:
```json
{
  "template_id": "cta_template_horror_001",
  "template_name": "Subscribe CTA - Horror Theme",
  "cta_type": "subscribe",
  "position": "end",
  "duration": 5,
  "elements": [
    {
      "type": "text",
      "content": "👻 Subscribe for more chilling stories",
      "style": {"font_size": "large", "color": "#ffffff"}
    },
    {
      "type": "button",
      "content": "SUBSCRIBE",
      "action": "subscribe"
    }
  ]
}
```

---

## 🔄 SSML System

### Universal SSML Parameters

Instead of storing service-specific SSML, we store **universal parameters** and generate SSML on-the-fly:

```json
{
  "text": "Welcome to our dark story",
  "ssml_params": {
    "rate": "fast",
    "pitch": "+5%",
    "volume": "loud",
    "emphasis": "strong",
    "pause_after": "500ms"
  }
}
```

### TTS Service Support

| Parameter | AWS Polly | Google TTS | Azure TTS | ElevenLabs |
|-----------|-----------|------------|-----------|------------|
| rate      | ✅        | ✅         | ✅        | ❌ (use stability) |
| pitch     | ✅        | ✅         | ✅        | ❌ |
| volume    | ✅        | ✅         | ✅        | ❌ |
| emphasis  | ✅        | ✅         | ✅        | ❌ |
| pause     | ✅        | ✅         | ✅        | ⚠️ (add silence) |

---

## 📁 File Structure

```
aws/
├── dynamodb-schemas/
│   ├── ImageGenerationTemplates-schema.json
│   ├── VideoEditingTemplates-schema.json
│   ├── CTATemplates-schema.json
│   └── PromptTemplatesV2-updated-schema.json
├── create-template-tables.sh
└── create-template-tables.ps1

prompts-editor.html (оновлено з підвкладками)
```

---

## 🚀 Next Steps

1. ✅ Створити DynamoDB таблиці
2. 🔄 Оновити prompts-api Lambda
3. ⏳ Створити SSML generator для різних TTS сервісів
4. ⏳ Оновити frontend для роботи з новими типами
5. ⏳ Протестувати всі типи темплейтів

---

**Created**: 2025-11-05
**Status**: Tables Created ✅
