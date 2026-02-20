# 🚀 Story Engine - Full Implementation Plan

**Date:** 2026-02-20
**Goal:** Повна реалізація нової Story Engine системи + Manual Input Mode
**Approach:** Git-based, production-ready, поетапно через Git commits

---

## 📋 OVERVIEW

### Що реалізуємо:

1. ✅ **Manual Input Mode** - можливість ручного вводу narrative (пропуск AI етапів)
2. ✅ **Story Mode Switch** - Fiction / Real Events / Hybrid
3. ✅ **Story DNA** - world_type, tone, psychological_depth, plot_intensity
4. ✅ **Story Structure** - one_shot / episodic / infinite + template
5. ✅ **Character Engine** - auto / persistent, archetype, internal conflict
6. ✅ **Logic & Consistency** - generate_plan, consistency_check, no_cliches

### Нові Lambda функції:

1. **content-story-planner** - планує структуру перед написанням
2. **content-character-designer** - створює персонажів
3. **content-narrative-writer** - пише narrative (замість mega-generation)
4. **content-image-prompt-generator** - окремо генерує image prompts
5. **content-fact-extractor** - витягує факти з Wikipedia

### Новий Workflow:

```
Manual Mode: CheckInputMode → LoadManualNarrative → Phase2Parallel
AI Mode: ThemeAgent → FactExtractor → StoryPlanner → CharacterDesigner →
         NarrativeWriter → ImagePromptGenerator → Phase2Parallel
```

---

## 🎯 IMPLEMENTATION PHASES

---

## **PHASE 1: Manual Input Mode** (HIGHEST PRIORITY)

**Мета:** Додати можливість ручного вводу narrative → пропуск AI етапів

**Часова оцінка:** 4-6 годин

### Step 1.1: UI в channels.html (1 година)

**Файл:** `channels.html`

**Зміни:**
```html
<!-- New section in channel config modal -->
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
                ⚠️ Коли увімкнено - пропускаються AI етапи генерації.
                Система одразу переходить до audio/images/video.
            </span>
        </div>

        <!-- Manual Input Fields -->
        <div id="manual-input-fields" style="display: none;">

            <!-- Story Title -->
            <div class="form-group full">
                <label>📌 Story Title / Theme</label>
                <input type="text" id="manual_theme"
                       placeholder="Example: The Last Samurai's Secret">
                <span class="field-hint">Назва історії або тема відео</span>
            </div>

            <!-- Narrative JSON -->
            <div class="form-group full">
                <label>📝 Story Narrative (JSON format)</label>
                <textarea id="manual_narrative" rows="20"
                          placeholder="Paste narrative JSON here..."></textarea>
                <span class="field-hint">
                    Формат JSON має містити: story_title, scenes (array)
                    <br><br>
                    <strong>Приклад структури:</strong>
                    <pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; font-size: 12px; overflow-x: auto;">
{
  "story_title": "The Last Samurai's Secret",
  "scenes": [
    {
      "scene_number": 1,
      "scene_title": "The Village Burns",
      "scene_narration": "In fifteen eighty-seven, a quiet village in feudal Japan...",
      "image_prompt": "Japanese village on fire, cinematic wide shot, dramatic lighting...",
      "negative_prompt": "blurry, low quality, distorted",
      "music_track": "dramatic_japanese.mp3",
      "sfx_cues": ["fire_crackling.mp3", "wind_howling.mp3"],
      "timing_estimates": [0, 5, 10]
    }
  ],
  "metadata": {
    "total_scenes": 10,
    "estimated_duration_seconds": 600
  }
}</pre>
                </span>
            </div>

            <!-- Buttons -->
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
                     style="background: #f5f5f5; padding: 15px; border-radius: 8px;
                            max-height: 300px; overflow-y: auto; font-size: 13px;">
                    <em style="color: #718096;">Preview will appear after validation...</em>
                </div>
            </div>

        </div>
    </div>
</details>
```

**Commit message:**
```
feat: add Manual Input Mode UI to channels.html

- Add Manual Input Mode section with checkbox toggle
- Add manual_theme input field
- Add manual_narrative textarea with JSON example
- Add Generate Template and Validate buttons
- Add preview area for validation results

Part of Story Engine Phase 1 implementation
```

---

### Step 1.2: JavaScript Logic (1-2 години)

**Файл:** `js/channels-unified.js`

**Додати функції:**

```javascript
// Toggle manual input fields visibility
document.addEventListener('DOMContentLoaded', function() {
    const manualModeCheckbox = document.getElementById('manual_mode_enabled');
    if (manualModeCheckbox) {
        manualModeCheckbox.addEventListener('change', function() {
            const manualFields = document.getElementById('manual-input-fields');
            if (manualFields) {
                manualFields.style.display = this.checked ? 'block' : 'none';
            }
        });
    }
});

/**
 * Generate empty narrative template
 */
function generateManualNarrativeTemplate() {
    const template = {
        "story_title": "Your Story Title Here",
        "scenes": [
            {
                "scene_number": 1,
                "scene_title": "Scene 1 Title",
                "scene_narration": "Narration text for scene 1... Write numbers as words (e.g., 'nineteen eighty-seven' not '1987')",
                "image_prompt": "Detailed image prompt for FLUX 1.1 Pro...",
                "negative_prompt": "blurry, low quality, distorted",
                "music_track": "epic_orchestral.mp3",
                "sfx_cues": ["sfx1.mp3", "sfx2.mp3"],
                "timing_estimates": [0, 5, 10]
            },
            {
                "scene_number": 2,
                "scene_title": "Scene 2 Title",
                "scene_narration": "Narration text for scene 2...",
                "image_prompt": "Another detailed image prompt...",
                "negative_prompt": "blurry, low quality",
                "music_track": "suspense_ambient.mp3",
                "sfx_cues": ["footsteps.mp3"],
                "timing_estimates": [0, 8]
            }
        ],
        "metadata": {
            "total_scenes": 2,
            "estimated_duration_seconds": 120
        }
    };

    document.getElementById('manual_narrative').value = JSON.stringify(template, null, 2);
    alert('✅ Template generated! You can now edit it.');
}

/**
 * Validate manual narrative JSON
 */
function validateManualNarrative() {
    const narrativeText = document.getElementById('manual_narrative').value.trim();
    const previewDiv = document.getElementById('manual-narrative-preview');

    if (!narrativeText) {
        previewDiv.innerHTML = '<span style="color: red;">❌ Please enter narrative JSON</span>';
        return;
    }

    try {
        const narrative = JSON.parse(narrativeText);

        // Validation rules
        const errors = [];

        if (!narrative.story_title) {
            errors.push('Missing story_title');
        }
        if (!narrative.scenes || !Array.isArray(narrative.scenes)) {
            errors.push('Missing or invalid scenes array');
        } else if (narrative.scenes.length === 0) {
            errors.push('Scenes array is empty (need at least 1 scene)');
        } else {
            // Validate each scene
            narrative.scenes.forEach((scene, idx) => {
                const requiredFields = ['scene_number', 'scene_title', 'scene_narration', 'image_prompt'];
                requiredFields.forEach(field => {
                    if (!scene[field]) {
                        errors.push(`Scene ${idx + 1}: missing ${field}`);
                    }
                });

                // Check narration length
                if (scene.scene_narration && scene.scene_narration.length < 50) {
                    errors.push(`Scene ${idx + 1}: scene_narration too short (min 50 chars)`);
                }
            });
        }

        if (errors.length > 0) {
            previewDiv.innerHTML = `
                <div style="color: red;">
                    <strong>❌ Validation Errors:</strong>
                    <ul style="margin: 10px 0; padding-left: 20px;">
                        ${errors.map(err => `<li>${err}</li>`).join('')}
                    </ul>
                </div>
            `;
            return;
        }

        // Show success preview
        previewDiv.innerHTML = `
            <div style="color: green;">
                <strong>✅ Valid JSON!</strong><br>
                <strong>Title:</strong> ${narrative.story_title}<br>
                <strong>Scenes:</strong> ${narrative.scenes.length}<br>
                <strong>Estimated Duration:</strong> ${narrative.metadata?.estimated_duration_seconds || 'N/A'}s
            </div>
            <hr style="margin: 10px 0;">
            <div style="max-height: 200px; overflow-y: auto;">
                ${narrative.scenes.map((s, i) => `
                    <div style="margin-bottom: 10px; padding: 8px; background: white; border-radius: 4px;">
                        <strong>Scene ${s.scene_number}:</strong> ${s.scene_title}<br>
                        <em style="color: #666; font-size: 12px;">${s.scene_narration.substring(0, 100)}...</em>
                    </div>
                `).join('')}
            </div>
        `;

        alert('✅ Narrative JSON is valid and ready to save!');

    } catch (error) {
        previewDiv.innerHTML = `
            <span style="color: red;">
                ❌ Invalid JSON syntax: ${error.message}
            </span>
        `;
    }
}
```

**Оновити функцію `saveModalConfig()`:**

```javascript
async function saveModalConfig() {
    const formData = new FormData();

    // ... existing fields ...

    // Manual mode fields
    const manualModeEnabled = document.getElementById('manual_mode_enabled')?.checked || false;
    formData.append('manual_mode_enabled', manualModeEnabled);

    if (manualModeEnabled) {
        const manualTheme = document.getElementById('manual_theme')?.value || '';
        const manualNarrative = document.getElementById('manual_narrative')?.value || '';

        formData.append('manual_theme', manualTheme);
        formData.append('manual_narrative', manualNarrative);

        // Validate before saving
        try {
            if (manualNarrative) {
                JSON.parse(manualNarrative);
            }
        } catch (e) {
            alert('❌ Invalid manual_narrative JSON. Please validate before saving.');
            return;
        }
    }

    // ... rest of save logic ...
}
```

**Оновити `populateForm()`:**

```javascript
const fieldsToPopulate = [
    // ... existing fields ...
    'manual_mode_enabled',  // checkbox
    'manual_theme',
    'manual_narrative'
];

// After populating, show/hide manual fields
if (config.manual_mode_enabled) {
    document.getElementById('manual-input-fields').style.display = 'block';
}
```

**Commit message:**
```
feat: add Manual Input Mode JavaScript logic

- Add toggle functionality for manual input fields
- Add generateManualNarrativeTemplate() function
- Add validateManualNarrative() with validation rules
- Update saveModalConfig() to save manual fields
- Update populateForm() to load manual fields

Part of Story Engine Phase 1 implementation
```

---

### Step 1.3: Backend - update-channel-config.php (30 хвилин)

**Файл:** `api/update-channel-config.php`

**Додати поля:**

```php
// Manual Input Mode fields
if (isset($_POST['manual_mode_enabled'])) {
    $updateFields['manual_mode_enabled'] = filter_var($_POST['manual_mode_enabled'], FILTER_VALIDATE_BOOLEAN);
}

if (isset($_POST['manual_theme'])) {
    $updateFields['manual_theme'] = trim($_POST['manual_theme']);
}

if (isset($_POST['manual_narrative'])) {
    $narrativeJson = trim($_POST['manual_narrative']);

    // Validate JSON before saving
    if (!empty($narrativeJson)) {
        $narrative = json_decode($narrativeJson, true);
        if (json_last_error() !== JSON_ERROR_NONE) {
            http_response_code(400);
            echo json_encode([
                'error' => 'Invalid manual_narrative JSON: ' . json_last_error_msg()
            ]);
            exit;
        }

        // Additional validation
        if (empty($narrative['story_title'])) {
            http_response_code(400);
            echo json_encode(['error' => 'manual_narrative missing story_title']);
            exit;
        }
        if (empty($narrative['scenes']) || !is_array($narrative['scenes'])) {
            http_response_code(400);
            echo json_encode(['error' => 'manual_narrative missing scenes array']);
            exit;
        }

        $updateFields['manual_narrative'] = $narrativeJson;
    } else {
        $updateFields['manual_narrative'] = '';
    }
}
```

**Commit message:**
```
feat: add Manual Input Mode support to update-channel-config.php

- Add manual_mode_enabled field (boolean)
- Add manual_theme field (string)
- Add manual_narrative field (JSON string) with validation
- Validate JSON structure before saving

Part of Story Engine Phase 1 implementation
```

---

### Step 1.4: Step Functions Update (1-2 години)

**Файл:** Створити новий JSON definition для Step Functions

**Новий файл:** `aws/step-functions/content-generation-v2.json`

**Зміни:**

```json
{
  "Comment": "Content Generation Workflow v2 - with Manual Input Mode support",
  "StartAt": "GetChannels",
  "States": {
    "GetChannels": {
      "Type": "Task",
      "Resource": "arn:aws:states:::lambda:invoke",
      "Parameters": {
        "FunctionName": "content-get-channels"
      },
      "ResultPath": "$.channelsResult",
      "Next": "Phase1ContentGeneration"
    },

    "Phase1ContentGeneration": {
      "Type": "Map",
      "ItemsPath": "$.channelsResult.Payload.data",
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
            "Default": "ThemeAgent"
          },

          "LoadManualNarrative": {
            "Type": "Pass",
            "Comment": "Manual mode: load narrative from channel config",
            "Parameters": {
              "channel_id.$": "$.channel_id",
              "manual_theme.$": "$.manual_theme",
              "narrativeResult": {
                "statusCode": 200,
                "body.$": "States.StringToJson($.manual_narrative)"
              }
            },
            "ResultPath": "$",
            "Next": "Phase2Parallel"
          },

          "ThemeAgent": {
            "Type": "Task",
            "Resource": "arn:aws:states:::lambda:invoke",
            "Parameters": {
              "FunctionName": "content-theme-agent",
              "Payload": {
                "channel_id.$": "$.channel_id"
              }
            },
            "ResultPath": "$.themeResult",
            "Next": "CheckFactualMode"
          },

          "CheckFactualMode": {
            "Type": "Choice",
            "Choices": [
              {
                "Variable": "$.factual_mode",
                "StringEquals": "factual",
                "Next": "SearchWikipediaFacts"
              }
            ],
            "Default": "SetNoFacts"
          },

          "SearchWikipediaFacts": {
            "Type": "Task",
            "Resource": "arn:aws:states:::lambda:invoke",
            "Parameters": {
              "FunctionName": "content-search-facts",
              "Payload": {
                "channel_id.$": "$.channel_id",
                "selected_topic.$": "$.themeResult.Payload.selected_topic"
              }
            },
            "ResultPath": "$.factsResult",
            "Next": "MegaNarrativeGenerator"
          },

          "SetNoFacts": {
            "Type": "Pass",
            "Result": {
              "statusCode": 200,
              "body": {
                "content": ""
              }
            },
            "ResultPath": "$.factsResult",
            "Next": "MegaNarrativeGenerator"
          },

          "MegaNarrativeGenerator": {
            "Type": "Task",
            "Resource": "arn:aws:states:::lambda:invoke",
            "Parameters": {
              "FunctionName": "content-narrative",
              "Payload": {
                "channel_id.$": "$.channel_id",
                "selected_topic.$": "$.themeResult.Payload.selected_topic",
                "wikipedia_facts.$": "$.factsResult.Payload.body"
              }
            },
            "ResultPath": "$.narrativeResult",
            "Next": "Phase2Parallel"
          },

          "Phase2Parallel": {
            "Type": "Parallel",
            "Comment": "Generate audio + images in parallel",
            "Branches": [
              {
                "StartAt": "AudioQwen3TTS",
                "States": {
                  "AudioQwen3TTS": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::lambda:invoke",
                    "Parameters": {
                      "FunctionName": "content-audio-qwen3tts",
                      "Payload": {
                        "channel_id.$": "$.channel_id",
                        "narrative.$": "$.narrativeResult.Payload.body"
                      }
                    },
                    "End": true
                  }
                }
              },
              {
                "StartAt": "ImageGeneration",
                "States": {
                  "ImageGeneration": {
                    "Type": "Task",
                    "Resource": "arn:aws:states:::lambda:invoke",
                    "Parameters": {
                      "FunctionName": "content-generate-images",
                      "Payload": {
                        "channel_id.$": "$.channel_id",
                        "narrative.$": "$.narrativeResult.Payload.body"
                      }
                    },
                    "End": true
                  }
                }
              }
            ],
            "Next": "VideoAssembly"
          },

          "VideoAssembly": {
            "Type": "Task",
            "Resource": "arn:aws:states:::lambda:invoke",
            "Parameters": {
              "FunctionName": "content-video-assembly",
              "Payload": {
                "channel_id.$": "$.channel_id",
                "narrative.$": "$.narrativeResult.Payload.body"
              }
            },
            "ResultPath": "$.videoResult",
            "Next": "SaveResult"
          },

          "SaveResult": {
            "Type": "Task",
            "Resource": "arn:aws:states:::lambda:invoke",
            "Parameters": {
              "FunctionName": "content-save-result",
              "Payload": {
                "channel_id.$": "$.channel_id",
                "narrative.$": "$.narrativeResult.Payload.body",
                "video_url.$": "$.videoResult.Payload.video_url"
              }
            },
            "End": true
          }

        }
      },
      "End": true
    }
  }
}
```

**Команда для оновлення Step Functions:**

```bash
aws stepfunctions update-state-machine \
  --state-machine-arn arn:aws:states:eu-central-1:599297130956:stateMachine:ContentGenerationStateMachine \
  --definition file://aws/step-functions/content-generation-v2.json \
  --region eu-central-1
```

**Commit message:**
```
feat: add Manual Input Mode support to Step Functions

- Add CheckInputMode Choice state
- Add LoadManualNarrative Pass state
- Manual mode skips ThemeAgent, FactExtractor, NarrativeGenerator
- Manual mode goes directly to Phase2Parallel (audio+images)

Part of Story Engine Phase 1 implementation
```

---

### Step 1.5: Testing (1 година)

**Test Plan:**

1. ✅ UI Testing:
   - Увімкнути Manual Mode checkbox → поля з'являються
   - Натиснути "Generate Template" → JSON шаблон з'являється
   - Редагувати JSON → натиснути "Validate" → показує помилки/успіх
   - Зберегти channel config → перевірити DynamoDB

2. ✅ Workflow Testing:
   - Запустити генерацію з `manual_mode_enabled: true`
   - Перевірити CloudWatch logs → пропущені ThemeAgent, NarrativeGenerator
   - Перевірити що Phase2Parallel (audio+images) виконався
   - Перевірити фінальне відео

**Commit message:**
```
test: verify Manual Input Mode end-to-end

- UI toggles work correctly
- Template generation works
- JSON validation catches errors
- Manual narrative saves to DynamoDB
- Workflow skips AI stages and goes to Phase2
- Video assembly completes successfully

Part of Story Engine Phase 1 implementation
```

---

## **PHASE 2: Story Engine UI** (PRIORITY 2)

**Мета:** Додати всі нові поля Story Engine в UI

**Часова оцінка:** 6-8 годин

### Step 2.1: Story Mode Switch UI (1 година)

**Файл:** `channels.html`

**Додати після секції "Основне":**

```html
<!-- ═══ STORY MODE ═══ -->
<details class="advanced-settings" open>
    <summary>🎭 Story Mode</summary>
    <div class="advanced-settings-body">

        <div class="form-group full">
            <label>Режим створення історії</label>
            <div class="story-mode-toggle" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px;">

                <!-- Fiction Mode -->
                <div class="mode-card" data-value="fiction" onclick="setStoryMode('fiction')"
                     style="cursor: pointer; padding: 20px; border: 2px solid #e0e0e0; border-radius: 10px; text-align: center; transition: all 0.3s;">
                    <div style="font-size: 40px; margin-bottom: 10px;">✨</div>
                    <h4 style="margin: 0 0 8px 0; color: #2d3748;">Fiction</h4>
                    <p style="margin: 0; font-size: 13px; color: #718096;">Повна творча свобода AI</p>
                </div>

                <!-- Real Events Mode -->
                <div class="mode-card" data-value="real_events" onclick="setStoryMode('real_events')"
                     style="cursor: pointer; padding: 20px; border: 2px solid #e0e0e0; border-radius: 10px; text-align: center; transition: all 0.3s;">
                    <div style="font-size: 40px; margin-bottom: 10px;">📚</div>
                    <h4 style="margin: 0 0 8px 0; color: #2d3748;">Real Events</h4>
                    <p style="margin: 0; font-size: 13px; color: #718096;">Тільки факти (Wikipedia)</p>
                </div>

                <!-- Hybrid Mode -->
                <div class="mode-card" data-value="hybrid" onclick="setStoryMode('hybrid')"
                     style="cursor: pointer; padding: 20px; border: 2px solid #e0e0e0; border-radius: 10px; text-align: center; transition: all 0.3s;">
                    <div style="font-size: 40px; margin-bottom: 10px;">🎬</div>
                    <h4 style="margin: 0 0 8px 0; color: #2d3748;">Hybrid</h4>
                    <p style="margin: 0; font-size: 13px; color: #718096;">Факти + драматична подача</p>
                </div>

            </div>

            <!-- Hidden select for form submission -->
            <select id="story_mode" style="display: none;">
                <option value="fiction">fiction</option>
                <option value="real_events">real_events</option>
                <option value="hybrid">hybrid</option>
            </select>
        </div>

    </div>
</details>
```

**JavaScript для setStoryMode():**

```javascript
function setStoryMode(mode) {
    // Update hidden select
    document.getElementById('story_mode').value = mode;

    // Update visual cards
    document.querySelectorAll('.story-mode-toggle .mode-card').forEach(card => {
        if (card.dataset.value === mode) {
            card.style.borderColor = '#667eea';
            card.style.background = '#f0f4ff';
        } else {
            card.style.borderColor = '#e0e0e0';
            card.style.background = 'white';
        }
    });
}
```

---

### Step 2.2: Story DNA UI (1-2 години)

**Додати після Story Mode:**

```html
<!-- ═══ STORY DNA ═══ -->
<details class="advanced-settings">
    <summary>🧬 Story DNA (Character of the Channel)</summary>
    <div class="advanced-settings-body">

        <div class="form-grid">

            <!-- World Type -->
            <div class="form-group full">
                <label>🌍 World Type</label>
                <select id="world_type">
                    <option value="realistic">Realistic (сучасний світ)</option>
                    <option value="medieval_fantasy">Medieval Fantasy (середньовіччя, магія)</option>
                    <option value="cyberpunk">Cyberpunk (майбутнє, технології)</option>
                    <option value="post_apocalyptic">Post-Apocalyptic (після катастрофи)</option>
                    <option value="alternate_reality">Alternate Reality (альтернативна історія)</option>
                </select>
                <span class="field-hint">Світ в якому відбуваються історії</span>
            </div>

            <!-- Tone -->
            <div class="form-group full">
                <label>🎨 Tone (Тональність)</label>
                <select id="tone">
                    <option value="dark">Dark (темний, похмурий)</option>
                    <option value="emotional">Emotional (емоційний, зворушливий)</option>
                    <option value="epic">Epic (епічний, грандіозний)</option>
                    <option value="calm">Calm (спокійний, медитативний)</option>
                    <option value="disturbing">Disturbing (тривожний, моторошний)</option>
                </select>
                <span class="field-hint">Емоційна атмосфера історій</span>
            </div>

            <!-- Psychological Depth -->
            <div class="form-group full">
                <label>🧠 Psychological Depth (Психологічна глибина)</label>
                <input type="range" id="psychological_depth" min="1" max="5" value="3" step="1"
                       oninput="updateSliderValue(this, 'psychological_depth_value')">
                <div style="display: flex; justify-content: space-between; margin-top: 5px; font-size: 12px; color: #718096;">
                    <span>1 (Поверхнево)</span>
                    <span id="psychological_depth_value" style="font-weight: 600; color: #667eea;">3</span>
                    <span>5 (Глибоко)</span>
                </div>
                <span class="field-hint">1 = проста подача, 5 = складні персонажі і мотивації</span>
            </div>

            <!-- Plot Intensity -->
            <div class="form-group full">
                <label>⚡ Plot Intensity (Інтенсивність сюжету)</label>
                <input type="range" id="plot_intensity" min="1" max="5" value="4" step="1"
                       oninput="updateSliderValue(this, 'plot_intensity_value')">
                <div style="display: flex; justify-content: space-between; margin-top: 5px; font-size: 12px; color: #718096;">
                    <span>1 (Повільний)</span>
                    <span id="plot_intensity_value" style="font-weight: 600; color: #667eea;">4</span>
                    <span>5 (Швидкий)</span>
                </div>
                <span class="field-hint">1 = спокійний темп, 5 = динамічний екшн</span>
            </div>

        </div>

    </div>
</details>
```

**JavaScript:**

```javascript
function updateSliderValue(slider, valueId) {
    document.getElementById(valueId).textContent = slider.value;
}
```

---

### Step 2.3: Character Engine UI (1 година)

(Продовжується в наступному кроці...)

---

**Чи продовжити з детальним планом всіх Phase 2-5?**

Або хочеш **почати реалізацію Phase 1 ЗАРАЗ** (Manual Input Mode)?

**Що робимо?** 🚀
