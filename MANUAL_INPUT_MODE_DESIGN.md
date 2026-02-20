# 🎬 Manual Input Mode - Architecture Extension

**Date:** 2026-02-20
**Purpose:** Додати можливість ручного вводу теми і наративу, пропустивши AI генерацію

---

## 📋 ВИМОГА

> Можливість ручного вводу теми і наративу, щоб пропустити фазу створення контенту і промптів для картинок, озвучки тощо, і відразу почати генерувати аудіо-імейдж файли і відео.

---

## 🎯 ЩО ПРОПУСКАЄТЬСЯ В MANUAL MODE

### ❌ Пропущені Lambda функції (Phase 1):
1. **ThemeAgent** - не генеруємо тему (користувач вводить)
2. **FactExtractor** - не шукаємо факти з Wikipedia
3. **StoryPlanner** - не плануємо структуру
4. **CharacterDesigner** - не створюємо персонажів
5. **NarrativeWriter** - не пишемо narrative (користувач вводить)

### ✅ Що виконується (Phase 2):
1. **ImagePromptGenerator** - генеруємо image prompts з narrative
2. **Audio Generation** - озвучуємо сцени
3. **Image Generation** - створюємо зображення
4. **Video Assembly** - збираємо відео

---

## 🏗️ АРХІТЕКТУРА

### 1️⃣ UI - Manual Input Panel

**Розташування:** `channels.html` → Channel Config Modal → Нова вкладка "✍️ Manual Input"

```html
<!-- New Tab in Channel Config -->
<details class="advanced-settings">
    <summary>✍️ Manual Input Mode</summary>
    <div class="advanced-settings-body">

        <!-- Enable Manual Mode -->
        <div class="form-group full">
            <label>
                <input type="checkbox" id="manual_mode_enabled">
                Enable Manual Input (skip AI generation)
            </label>
            <span class="field-hint">
                ⚠️ Коли увімкнено - пропускаються ThemeAgent, StoryPlanner, NarrativeWriter.
                Система одразу переходить до генерації audio/images/video.
            </span>
        </div>

        <!-- Manual Theme Input -->
        <div id="manual-input-fields" style="display: none;">
            <div class="form-group full">
                <label>📌 Story Title / Theme</label>
                <input type="text" id="manual_theme"
                       placeholder="Example: The Last Samurai's Secret">
                <span class="field-hint">Назва історії або тема відео</span>
            </div>

            <!-- Manual Narrative JSON -->
            <div class="form-group full">
                <label>📝 Story Narrative (JSON format)</label>
                <textarea id="manual_narrative" rows="20"
                          placeholder='Paste narrative JSON here...
Example:
{
  "story_title": "The Last Samurai",
  "scenes": [
    {
      "scene_number": 1,
      "scene_title": "The Village Burns",
      "scene_narration": "In 1587, a quiet village...",
      "image_prompt": "Japanese village on fire...",
      "music_track": "dramatic_japanese.mp3",
      "sfx_cues": ["fire_crackling.mp3", "wind_howling.mp3"]
    }
  ]
}'></textarea>
                <span class="field-hint">
                    Формат: JSON з полями story_title, scenes (array)
                </span>
            </div>

            <!-- Template Generator Button -->
            <div class="form-group full">
                <button type="button" class="btn btn-secondary"
                        onclick="generateManualNarrativeTemplate()">
                    📋 Generate Empty Template
                </button>
                <button type="button" class="btn btn-secondary"
                        onclick="validateManualNarrative()">
                    ✅ Validate JSON
                </button>
            </div>

            <!-- Preview -->
            <div class="form-group full">
                <label>👁️ Preview</label>
                <div id="manual-narrative-preview"
                     style="background: #f5f5f5; padding: 15px; border-radius: 8px; max-height: 300px; overflow-y: auto;">
                    <em>Preview will appear here after validation...</em>
                </div>
            </div>
        </div>

    </div>
</details>
```

**JavaScript Logic (`js/channels-unified.js`):**

```javascript
// Toggle manual input fields
document.getElementById('manual_mode_enabled').addEventListener('change', function() {
    const manualFields = document.getElementById('manual-input-fields');
    manualFields.style.display = this.checked ? 'block' : 'none';
});

// Generate empty template
function generateManualNarrativeTemplate() {
    const template = {
        "story_title": "Your Story Title Here",
        "scenes": [
            {
                "scene_number": 1,
                "scene_title": "Scene 1 Title",
                "scene_narration": "Narration text for scene 1...",
                "image_prompt": "Detailed image prompt for FLUX...",
                "negative_prompt": "blurry, low quality",
                "music_track": "epic_orchestral.mp3",
                "sfx_cues": ["sfx1.mp3", "sfx2.mp3"],
                "timing_estimates": [0, 5, 10]
            }
        ],
        "metadata": {
            "total_scenes": 1,
            "estimated_duration_seconds": 60
        }
    };

    document.getElementById('manual_narrative').value = JSON.stringify(template, null, 2);
}

// Validate JSON
function validateManualNarrative() {
    const narrativeText = document.getElementById('manual_narrative').value.trim();

    try {
        const narrative = JSON.parse(narrativeText);

        // Validation rules
        if (!narrative.story_title) {
            throw new Error('Missing story_title');
        }
        if (!narrative.scenes || !Array.isArray(narrative.scenes)) {
            throw new Error('Missing or invalid scenes array');
        }
        if (narrative.scenes.length === 0) {
            throw new Error('Scenes array is empty');
        }

        // Validate each scene
        narrative.scenes.forEach((scene, idx) => {
            const required = ['scene_number', 'scene_title', 'scene_narration', 'image_prompt'];
            required.forEach(field => {
                if (!scene[field]) {
                    throw new Error(`Scene ${idx + 1}: missing ${field}`);
                }
            });
        });

        // Show preview
        const preview = document.getElementById('manual-narrative-preview');
        preview.innerHTML = `
            <strong>✅ Valid JSON!</strong><br>
            <strong>Title:</strong> ${narrative.story_title}<br>
            <strong>Scenes:</strong> ${narrative.scenes.length}<br>
            <hr>
            ${narrative.scenes.map((s, i) => `
                <div style="margin-bottom: 10px;">
                    <strong>Scene ${s.scene_number}:</strong> ${s.scene_title}<br>
                    <em>${s.scene_narration.substring(0, 100)}...</em>
                </div>
            `).join('')}
        `;

        alert('✅ Narrative JSON is valid!');

    } catch (error) {
        alert(`❌ Invalid JSON: ${error.message}`);
        const preview = document.getElementById('manual-narrative-preview');
        preview.innerHTML = `<span style="color: red;">❌ ${error.message}</span>`;
    }
}

// Save to channel config
function saveChannelConfig() {
    const formData = new FormData();

    // ... existing fields ...

    // Manual mode fields
    const manualModeEnabled = document.getElementById('manual_mode_enabled').checked;
    formData.append('manual_mode_enabled', manualModeEnabled);

    if (manualModeEnabled) {
        const manualTheme = document.getElementById('manual_theme').value;
        const manualNarrative = document.getElementById('manual_narrative').value;

        formData.append('manual_theme', manualTheme);
        formData.append('manual_narrative', manualNarrative);
    }

    // ... rest of save logic ...
}
```

---

### 2️⃣ DynamoDB Schema Changes

**Table:** `ChannelConfigs`

**New Fields:**
```json
{
  "manual_mode_enabled": false,
  "manual_theme": "",
  "manual_narrative": "{...}"  // JSON string
}
```

**PHP Update (`api/update-channel-config.php`):**
```php
// Add new fields
if (isset($_POST['manual_mode_enabled'])) {
    $updateFields['manual_mode_enabled'] = filter_var($_POST['manual_mode_enabled'], FILTER_VALIDATE_BOOLEAN);
}
if (isset($_POST['manual_theme'])) {
    $updateFields['manual_theme'] = $_POST['manual_theme'];
}
if (isset($_POST['manual_narrative'])) {
    // Validate JSON before saving
    $narrative = json_decode($_POST['manual_narrative'], true);
    if (json_last_error() === JSON_ERROR_NONE) {
        $updateFields['manual_narrative'] = $_POST['manual_narrative'];
    } else {
        http_response_code(400);
        echo json_encode(['error' => 'Invalid manual_narrative JSON']);
        exit;
    }
}
```

---

### 3️⃣ Step Functions Changes

**Updated Workflow:**

```json
{
  "Phase1ContentGeneration": {
    "Type": "Map",
    "ItemsPath": "$.channelsResult.data",
    "MaxConcurrency": 5,
    "Iterator": {
      "StartAt": "CheckInputMode",
      "States": {

        "CheckInputMode": {
          "Type": "Choice",
          "Comment": "Check if manual input mode is enabled",
          "Choices": [
            {
              "Variable": "$.manual_mode_enabled",
              "BooleanEquals": true,
              "Next": "LoadManualNarrative"
            }
          ],
          "Default": "LoadChannelSettings"
        },

        "LoadManualNarrative": {
          "Type": "Pass",
          "Comment": "Manual mode: load narrative from channel config",
          "Parameters": {
            "channel_id.$": "$.channel_id",
            "manual_theme.$": "$.manual_theme",
            "manual_narrative.$": "$.manual_narrative",
            "narrativeResult": {
              "story_title.$": "States.StringToJson($.manual_narrative).story_title",
              "scenes.$": "States.StringToJson($.manual_narrative).scenes",
              "metadata.$": "States.StringToJson($.manual_narrative).metadata"
            }
          },
          "ResultPath": "$",
          "Next": "Phase2Parallel"
        },

        "LoadChannelSettings": {
          "Type": "Pass",
          "Comment": "AI mode: standard flow",
          "Next": "StoryModeSwitch"
        },

        "StoryModeSwitch": {
          "Type": "Choice",
          "Comment": "Route based on story_mode",
          "Choices": [
            {
              "Variable": "$.story_mode",
              "StringEquals": "fiction",
              "Next": "FictionBranch_ThemeAgent"
            }
          ]
        },

        "FictionBranch_ThemeAgent": {
          "Type": "Task",
          "Resource": "arn:aws:states:::lambda:invoke",
          "Parameters": {
            "FunctionName": "content-theme-agent",
            "Payload": { ... }
          },
          "Next": "StoryPlanner"
        },

        "StoryPlanner": {
          "Type": "Task",
          "Resource": "arn:aws:states:::lambda:invoke",
          "Parameters": {
            "FunctionName": "content-story-planner",
            "Payload": { ... }
          },
          "Next": "NarrativeWriter"
        },

        "NarrativeWriter": {
          "Type": "Task",
          "Resource": "arn:aws:states:::lambda:invoke",
          "Parameters": {
            "FunctionName": "content-narrative-writer",
            "Payload": { ... }
          },
          "Next": "Phase2Parallel"
        },

        "Phase2Parallel": {
          "Type": "Parallel",
          "Comment": "Generate audio + images in parallel",
          "Branches": [
            {
              "StartAt": "AudioGeneration",
              "States": { ... }
            },
            {
              "StartAt": "ImageGeneration",
              "States": { ... }
            }
          ],
          "Next": "VideoAssembly"
        },

        "VideoAssembly": {
          "Type": "Task",
          "Resource": "arn:aws:states:::lambda:invoke",
          "Parameters": {
            "FunctionName": "content-video-assembly",
            "Payload": { ... }
          },
          "End": true
        }
      }
    }
  }
}
```

**Key Changes:**
1. ✅ `CheckInputMode` - новий Choice state перевіряє `manual_mode_enabled`
2. ✅ `LoadManualNarrative` - завантажує вручну введений narrative з channel config
3. ✅ Якщо manual mode - **пропускаємо** ThemeAgent, StoryPlanner, NarrativeWriter
4. ✅ Одразу йдемо в `Phase2Parallel` (audio + images)

---

### 4️⃣ Lambda Function Updates

**Content-Narrative (existing):**
- Не потребує змін! Якщо manual mode - Lambda просто не викликається

**Content-Audio (existing):**
- Приймає narrative з `narrativeResult.scenes`
- Працює однаково для AI і manual mode

**Content-Generate-Images (existing):**
- Приймає image_prompts з `narrativeResult.scenes`
- Працює однаково для AI і manual mode

**Content-Video-Assembly (existing):**
- Приймає audio + images + narrative
- Працює однаково для AI і manual mode

---

## 🎯 USER FLOW - Manual Input Mode

### Крок 1: Увімкнути Manual Mode
1. Відкрити Channel Config Modal
2. Натиснути вкладку "✍️ Manual Input Mode"
3. Поставити галочку "Enable Manual Input"

### Крок 2: Ввести дані
1. **Story Title:** "The Last Samurai's Secret"
2. **Narrative JSON:**
   - Натиснути "📋 Generate Empty Template" (створює шаблон)
   - Заповнити поля:
     - `story_title`
     - `scenes[]` (масив сцен)
       - `scene_number`, `scene_title`, `scene_narration`
       - `image_prompt`, `music_track`, `sfx_cues`
   - Натиснути "✅ Validate JSON" (перевірка)

### Крок 3: Зберегти
1. Натиснути "Save Channel Config"
2. Дані зберігаються в DynamoDB `ChannelConfigs`

### Крок 4: Запустити генерацію
1. Workflow стартує як зазвичай (через Topics Queue або вручну)
2. Step Functions бачить `manual_mode_enabled: true`
3. **Пропускає AI етапи** (ThemeAgent, StoryPlanner, NarrativeWriter)
4. Завантажує `manual_narrative` з channel config
5. Одразу йде в Phase 2:
   - **Audio Generation** (озвучка сцен)
   - **Image Generation** (картинки з image_prompts)
   - **Video Assembly** (збірка відео)

---

## ⚠️ VALIDATION RULES

### Manual Narrative Schema:
```json
{
  "story_title": "string (required)",
  "scenes": [
    {
      "scene_number": "integer (required)",
      "scene_title": "string (required)",
      "scene_narration": "string (required, 50-500 chars)",
      "image_prompt": "string (required, for FLUX)",
      "negative_prompt": "string (optional)",
      "music_track": "string (optional, filename from library)",
      "sfx_cues": ["array of strings (optional, filenames)"],
      "timing_estimates": ["array of numbers (optional, seconds)"]
    }
  ],
  "metadata": {
    "total_scenes": "integer",
    "estimated_duration_seconds": "integer"
  }
}
```

### Validation Errors:
- ❌ Invalid JSON syntax → show error, prevent save
- ❌ Missing required fields → show which field
- ❌ Empty scenes array → require at least 1 scene
- ❌ Scene narration too short (<50 chars) → warn user

---

## 📊 IMPLEMENTATION PLAN

### Phase 1: UI (1 день)
1. ✅ Додати вкладку "Manual Input" в `channels.html`
2. ✅ Додати поля: checkbox, theme input, narrative textarea
3. ✅ Додати кнопки: Generate Template, Validate JSON
4. ✅ JavaScript функції: toggle fields, validate, preview

### Phase 2: Backend (1 день)
1. ✅ Оновити `update-channel-config.php` (додати нові поля)
2. ✅ Додати validation для `manual_narrative` JSON

### Phase 3: Step Functions (1 день)
1. ✅ Додати `CheckInputMode` Choice state
2. ✅ Додати `LoadManualNarrative` Pass state
3. ✅ Оновити flow: manual mode → Phase2Parallel (skip AI stages)

### Phase 4: Testing (1 день)
1. ✅ Тестувати UI: validate JSON, preview
2. ✅ Тестувати workflow: manual narrative → audio → images → video
3. ✅ Перевірити що AI stages пропущені

### Phase 5: Deploy (1 день)
1. ✅ Deploy frontend (channels.html, channels-unified.js)
2. ✅ Deploy backend (update-channel-config.php)
3. ✅ Update Step Functions definition

---

## ✅ BENEFITS

1. **Швидкість:** Пропуск AI етапів = економія 2-3 хвилини
2. **Контроль:** Повний контроль над текстом narrative
3. **Тестування:** Легко тестувати audio/image/video генерацію
4. **Flexibility:** Можна використати external narrative (ChatGPT, Claude, інші AI)
5. **Debugging:** Легше знайти проблеми в Phase 2 (якщо narrative фіксований)

---

## 🚀 NEXT STEPS

1. ✅ Узгодити дизайн з User
2. ✅ Реалізувати UI в `channels.html`
3. ✅ Оновити Step Functions
4. ✅ Тестувати manual mode
5. ✅ Deploy на продакшн

---

**Status:** READY FOR IMPLEMENTATION 🎯
