# 🎬 Story Engine Redesign - Architecture Document

**Based on ChatGPT conversation analysis**
**Date:** 2026-02-20

---

## 📊 ОСНОВНА ІДЕЯ

Перехід від **одноетапної генерації** до **багатоетапного Story Engine** з підтримкою:
- **Fiction Mode** (повна творча свобода)
- **Real Events Mode** (строга фактологія + Wikipedia)
- **Hybrid Mode** (80% фактів + 20% кінематографічна подача)

**Ключова проблема:** Зараз система генерує ВСЕ за 1 промпт (narrative + image prompts + sfx + cta). Це призводить до:
- Нестабільної якості
- Відсутності контролю над логікою
- Неможливості створити **візуально консистентні серіали**

---

## 🏗️ ПОТОЧНА АРХІТЕКТУРА (що є зараз)

### Phase 1 (Theme → Narrative):
```
QueryTitles → ThemeAgent → CheckFactualMode → MegaNarrativeGenerator
                                ↓
                         SearchWikipediaFacts (якщо factual_mode=factual)
```

### MegaNarrativeGenerator (lambda):
- **Вхід:** selected_topic, wikipedia_facts (опціонально), channel_config
- **Вихід:** narrative + scenes + image_prompts + sfx + cta + thumbnail + description (ВСЕ ЗА ОДИН ЗАПИТ!)

### Проблема:
1. Один промпт робить все → важко контролювати якість
2. Немає етапу планування → логічні діри
3. Немає Character Consistency → персонажі змінюються
4. Visual Style дрейфує → кожна картинка інша

---

## 🎯 НОВА АРХІТЕКТУРА

### 1️⃣ Story Mode Switch (на рівні каналу)

**ChannelConfig.story_mode:**
- `"fiction"` - Fictional Mode
- `"real_events"` - Real Events Mode
- `"hybrid"` - Based on True Story

**UI (channels-unified.js):**
```html
<div class="story-mode-selector">
  <div class="mode-card" data-value="fiction">
    <i class="bi bi-magic"></i>
    <h4>Fiction</h4>
    <p>Повна творча свобода</p>
  </div>
  <div class="mode-card" data-value="real_events">
    <i class="bi bi-book"></i>
    <h4>Real Events</h4>
    <p>Тільки факти (Wikipedia)</p>
  </div>
  <div class="mode-card" data-value="hybrid">
    <i class="bi bi-film"></i>
    <h4>Hybrid</h4>
    <p>Факти + драма</p>
  </div>
</div>
```

---

### 2️⃣ Story DNA (незмінні характеристики каналу)

**ChannelConfig.story_dna (нові поля):**
```json
{
  "world_type": "medieval_fantasy | cyberpunk | realistic | post_apocalyptic | alternate_reality",
  "tone": "dark | emotional | epic | calm | disturbing",
  "psychological_depth": 3,  // 1-5 slider
  "plot_intensity": 4        // 1-5 slider
}
```

**UI:**
```html
<!-- World Type -->
<select id="world_type">
  <option value="realistic">Realistic</option>
  <option value="medieval_fantasy">Medieval Fantasy</option>
  <option value="cyberpunk">Cyberpunk</option>
  <option value="post_apocalyptic">Post-Apocalyptic</option>
  <option value="alternate_reality">Alternate Reality</option>
</select>

<!-- Tone -->
<select id="tone">
  <option value="dark">Dark</option>
  <option value="emotional">Emotional</option>
  <option value="epic">Epic</option>
  <option value="calm">Calm</option>
  <option value="disturbing">Disturbing</option>
</select>

<!-- Psychological Depth (slider 1-5) -->
<input type="range" id="psychological_depth" min="1" max="5" value="3">

<!-- Plot Intensity (slider 1-5) -->
<input type="range" id="plot_intensity" min="1" max="5" value="4">
```

---

### 3️⃣ Story Structure Control

**ChannelConfig.story_structure (нові поля):**
```json
{
  "mode": "one_shot | episodic | infinite",
  "template": "1. Hook\n2. World introduction\n3. Protagonist\n4. Conflict\n5. Twist\n6. Cliffhanger"
}
```

**UI:**
```html
<!-- Story Mode -->
<select id="story_structure_mode">
  <option value="one_shot">One-Shot Story (завершена історія)</option>
  <option value="episodic">Episodic Series (серіал)</option>
  <option value="infinite">Infinite Narrative (нескінченна)</option>
</select>

<!-- Structure Template (editable) -->
<textarea id="story_structure_template" rows="8">
1. Hook (емоційний гачок)
2. World introduction
3. Protagonist
4. Conflict
5. Twist
6. Cliffhanger
</textarea>
```

---

### 4️⃣ Character Engine

**ChannelConfig.character_settings (нові поля):**
```json
{
  "mode": "auto_generate | persistent",
  "archetype": "anti_hero | innocent | broken_genius | survivor | villain_pov",
  "enable_internal_conflict": true,
  "enable_secret": true,
  "moral_dilemma_level": 4  // 1-5
}
```

**UI:**
```html
<!-- Character Mode -->
<select id="character_mode">
  <option value="auto_generate">Auto Generate (новий персонаж кожної історії)</option>
  <option value="persistent">Persistent Character (той самий персонаж у серіалі)</option>
</select>

<!-- Archetype -->
<select id="character_archetype">
  <option value="anti_hero">Anti-Hero</option>
  <option value="innocent">Innocent</option>
  <option value="broken_genius">Broken Genius</option>
  <option value="survivor">Survivor</option>
  <option value="villain_pov">Villain POV</option>
</select>

<!-- Checkboxes -->
<input type="checkbox" id="enable_internal_conflict"> Internal Conflict
<input type="checkbox" id="enable_secret"> Character Secret
<input type="range" id="moral_dilemma_level" min="1" max="5" value="3"> Moral Dilemma Level
```

---

### 5️⃣ Logic & Consistency Module

**ChannelConfig.logic_settings (нові поля):**
```json
{
  "generate_plan_before_writing": true,
  "auto_consistency_check": true,
  "character_motivation_validation": true,
  "no_cliches_mode": true,
  "surprise_injection_level": 3  // 1-5
}
```

**UI:**
```html
<div class="logic-settings">
  <input type="checkbox" id="generate_plan_before_writing" checked>
  <label>Generate plot plan before writing</label>

  <input type="checkbox" id="auto_consistency_check" checked>
  <label>Auto consistency check</label>

  <input type="checkbox" id="character_motivation_validation" checked>
  <label>Character motivation validation</label>

  <input type="checkbox" id="no_cliches_mode" checked>
  <label>No clichés mode</label>

  <label>Surprise injection level:</label>
  <input type="range" id="surprise_injection_level" min="1" max="5" value="3">
</div>
```

---

### 6️⃣ Real Events Mode (додаткові поля)

**ChannelConfig.real_events_settings (тільки якщо story_mode = "real_events"):**
```json
{
  "fact_strictness": "strict | documentary | dramatic_retelling",
  "enable_ethics_mode": true,
  "enable_speculation_blocker": true
}
```

**UI (показувати тільки якщо story_mode == "real_events"):**
```html
<div id="real-events-settings" style="display: none;">
  <h3>📚 Real Events Settings</h3>

  <!-- Fact Strictness -->
  <select id="fact_strictness">
    <option value="strict">Strict (тільки підтверджені факти)</option>
    <option value="documentary">Documentary (факти + контекст)</option>
    <option value="dramatic_retelling">Dramatic Retelling (факти + художня подача)</option>
  </select>

  <!-- Ethics -->
  <input type="checkbox" id="enable_ethics_mode" checked>
  <label>Enable Ethics Mode (захист жертв, нейтральний тон)</label>

  <input type="checkbox" id="enable_speculation_blocker" checked>
  <label>Block Speculation (не дозволяти вигадувати деталі)</label>
</div>
```

---

### 7️⃣ Visual Consistency Engine (інтеграція з Variation Sets)

**ВАЖЛИВО:** Variation Sets вже існують! Треба тільки інтегрувати їх у новий Story Engine.

**Variation Set структура (вже є в DynamoDB):**
```json
{
  "set_id": 0,
  "set_name": "Dark Cinematic Horror",
  "visual_keywords": "cinematic dark realism, cold blue palette, dramatic side lighting",
  "visual_atmosphere": "dark, mysterious, tense",
  "image_style_variants": "oil painting, dark illustration, noir photography",
  "color_palettes": "cold blue, sepia, high contrast black",
  "lighting_variants": "dramatic shadows, night fog, backlit silhouettes",
  "composition_variants": "wide cinematic shot, close-up portrait, symmetrical framing",
  "visual_reference_type": "1940s noir films, Edward Hopper paintings",
  "negative_prompt": "modern objects, bright colors, smiling faces, text, watermark"
}
```

**Character Visual Lock (новий):**
```json
{
  "character_visual_profile": {
    "age": 35,
    "gender": "male",
    "hair_color": "dark brown",
    "distinctive_feature": "scar on left cheek",
    "clothing": "black wool coat",
    "always_apply_to_scenes": true
  }
}
```

**UI (додати в Variation Set Modal):**
```html
<div class="character-visual-lock">
  <h4>🎭 Character Visual Lock (опціонально)</h4>
  <p>Якщо персонаж постійний (серіал), опишіть його зовнішність:</p>

  <input type="text" id="character_age" placeholder="Вік (35)">
  <select id="character_gender">
    <option value="">— Не вказувати —</option>
    <option value="male">Male</option>
    <option value="female">Female</option>
  </select>
  <input type="text" id="character_hair_color" placeholder="Колір волосся (dark brown)">
  <input type="text" id="character_distinctive_feature" placeholder="Особлива риса (scar on left cheek)">
  <input type="text" id="character_clothing" placeholder="Одяг (black wool coat)">
</div>
```

---

## 🔄 НОВИЙ PIPELINE PHASE 1

### Поточний (один крок):
```
ThemeAgent → MegaNarrativeGenerator
```

### Новий (багатоетапний):
```
GetChannelConfig (з story_mode, story_dna, character_settings, etc)
  ↓
StoryModeSwitch (Choice state: Fiction / Real Events / Hybrid)
  ↓
  ├─ FICTION BRANCH:
  │   → StoryPlanner (планує історію)
  │   → CharacterBuilder (створює персонажів)
  │   → WorldBuilder (створює світ, тільки для Fiction)
  │   → OutlineGenerator (детальний outline)
  │
  ├─ REAL EVENTS BRANCH:
  │   → FactExtractor (витягує факти з Wikipedia)
  │   → TimelineBuilder (будує timeline подій)
  │   → SourceValidator (перевіряє факти)
  │   → OutlineGenerator (outline на основі фактів)
  │
  └─ HYBRID BRANCH:
      → FactExtractor (витягує факти)
      → StoryPlanner (планує кінематографічну подачу)
      → CharacterBuilder (реальні персонажі)
      → OutlineGenerator (факти + драма)
  ↓
MegaNarrativeGenerator (з урахуванням outline, персонажів, світу)
  ↓
ConsistencyChecker (перевіряє логіку, персонажів, timeline)
  ↓
ImagePromptGenerator (генерує промпти з Global Visual Style з Variation Sets)
```

---

## 🧩 НОВІ LAMBDA ФУНКЦІЇ

### 1. **content-story-planner** (нова)
**Призначення:** Створює детальний план історії перед narrative

**Вхід:**
- `channel_id`
- `user_id`
- `selected_topic`
- `story_dna` (world_type, tone, psychological_depth, plot_intensity)
- `story_structure` (mode, template)
- `character_settings`

**Вихід:**
```json
{
  "story_plan": {
    "title": "The Shadow of the Past",
    "genre": "dark fantasy",
    "estimated_scenes": 8,
    "plot_points": [
      { "act": 1, "point": "Hook - stranger arrives at village" },
      { "act": 1, "point": "Inciting incident - mysterious disappearances" },
      { "act": 2, "point": "Rising action - investigation begins" },
      { "act": 2, "point": "Midpoint twist - stranger is connected to past" },
      { "act": 3, "point": "Climax - confrontation" },
      { "act": 3, "point": "Resolution - dark truth revealed" }
    ],
    "emotional_arc": ["curiosity", "tension", "fear", "shock", "dread"],
    "key_themes": ["guilt", "redemption", "consequences of past"]
  }
}
```

---

### 2. **content-character-builder** (нова)
**Призначення:** Створює персонажів з консистентним profile

**Вхід:**
- `story_plan`
- `character_settings` (mode, archetype, enable_internal_conflict, etc)
- `story_mode` (fiction/real/hybrid)

**Вихід:**
```json
{
  "characters": [
    {
      "character_id": "protagonist_001",
      "name": "Marcus",
      "role": "protagonist",
      "archetype": "broken_genius",
      "age": 35,
      "background": "Former detective haunted by unsolved case",
      "internal_conflict": "Guilt vs. Redemption",
      "secret": "Was involved in the original incident 10 years ago",
      "moral_dilemma": "Truth vs. Protecting loved ones",
      "visual_profile": {
        "gender": "male",
        "hair_color": "dark brown",
        "distinctive_feature": "scar on left cheek",
        "clothing": "black wool coat"
      }
    }
  ]
}
```

---

### 3. **content-world-builder** (нова, тільки для Fiction)
**Призначення:** Створює світ для fictional історій

**Вхід:**
- `story_plan`
- `world_type` (medieval_fantasy, cyberpunk, etc)
- `tone`

**Вихід:**
```json
{
  "world": {
    "setting": "Small isolated village in misty mountains, 1800s",
    "atmosphere": "Dark, foggy, claustrophobic",
    "time_period": "Early 19th century",
    "key_locations": [
      { "name": "The Old Church", "description": "Abandoned, gothic architecture" },
      { "name": "Village Square", "description": "Cobblestone, gas lamps" },
      { "name": "Forest Edge", "description": "Dense fog, ancient trees" }
    ],
    "world_rules": [
      "Superstitions are taken seriously",
      "Outsiders are distrusted",
      "Night brings danger"
    ]
  }
}
```

---

### 4. **content-outline-generator** (нова)
**Призначення:** Генерує детальний outline сцена-за-сценою

**Вхід:**
- `story_plan`
- `characters`
- `world` (якщо Fiction)
- `facts_timeline` (якщо Real Events)

**Вихід:**
```json
{
  "outline": {
    "total_scenes": 8,
    "scenes": [
      {
        "scene_number": 1,
        "act": 1,
        "location": "Village Square",
        "time_of_day": "dusk",
        "characters_present": ["Marcus"],
        "action": "Marcus arrives at the village, observes suspicious behavior",
        "emotion": "curiosity",
        "plot_purpose": "Hook - introduce protagonist and setting"
      },
      {
        "scene_number": 2,
        "act": 1,
        "location": "The Old Church",
        "time_of_day": "night",
        "characters_present": ["Marcus", "Village Elder"],
        "action": "Elder reveals recent disappearances",
        "emotion": "tension",
        "plot_purpose": "Inciting incident - establish conflict"
      }
    ]
  }
}
```

---

### 5. **content-narrative (ЗМІНИТИ)**
**Зараз:** Генерує ВСЕ за один промпт

**Після рефакторингу:**
- **Вхід:** `outline` + `characters` + `world` + `story_mode`
- **Завдання:** Тільки написати текст narrative згідно з outline
- **НЕ генерує:** image prompts, sfx, cta (це робить окремо)

**Промпт стає простішим:**
```
System: You are a narrative writer. Write scene narration based on the provided outline.

User:
Outline: {outline}
Characters: {characters}
World: {world}
Tone: {tone}

Write narrative text for each scene. Follow the outline exactly. Maintain character consistency.
```

---

### 6. **content-consistency-checker** (нова)
**Призначення:** Перевіряє логіку, timeline, персонажів

**Вхід:**
- `narrative`
- `outline`
- `characters`
- `story_mode`

**Вихід:**
```json
{
  "consistency_report": {
    "status": "passed | failed",
    "errors": [
      { "type": "timeline_error", "scene": 5, "issue": "Character was in two places at once" },
      { "type": "character_inconsistency", "scene": 7, "issue": "Character hair color changed from brown to blonde" }
    ],
    "warnings": [
      { "type": "cliche_detected", "scene": 3, "issue": "Used 'it was a dark and stormy night'" }
    ],
    "suggestions": [
      { "scene": 4, "suggestion": "Strengthen emotional transition from fear to hope" }
    ]
  }
}
```

---

### 7. **content-image-prompt-generator** (нова/змінити існуючий)
**Призначення:** Генерує image prompts з Global Visual Style

**Вхід:**
- `narrative` (scenes)
- `variation_set` (з ChannelConfig)
- `character_visual_profile` (якщо є)
- `story_mode`

**Вихід:**
```json
{
  "image_prompts": [
    {
      "scene_number": 1,
      "image_prompt": "cinematic dark realism, cold blue palette, dramatic side lighting, small isolated village in misty mountains, dusk, male protagonist age 35 dark brown hair scar on left cheek black wool coat, standing in cobblestone square with gas lamps, fog in background, wide cinematic shot, high detail, 1800s clothing accurate, no modern objects, no text, no bright colors"
    }
  ]
}
```

**Логіка:**
```
Image Prompt =
  Global Visual Style (з Variation Set)
  + Scene Description (з narrative)
  + Character Visual Profile (якщо persistent character)
  + Era/World Restrictions (no modern objects якщо historical)
  + Negative Prompt (з Variation Set)
```

---

## 📦 ЗМІНИ В DYNAMODB SCHEMA

### **ChannelConfigs** (таблиця):

**Нові поля:**
```json
{
  // STORY MODE
  "story_mode": "fiction | real_events | hybrid",

  // STORY DNA
  "story_dna": {
    "world_type": "realistic | medieval_fantasy | cyberpunk | post_apocalyptic | alternate_reality",
    "tone": "dark | emotional | epic | calm | disturbing",
    "psychological_depth": 3,  // 1-5
    "plot_intensity": 4        // 1-5
  },

  // STORY STRUCTURE
  "story_structure": {
    "mode": "one_shot | episodic | infinite",
    "template": "1. Hook\n2. World\n3. Protagonist\n4. Conflict\n5. Twist\n6. Cliffhanger"
  },

  // CHARACTER SETTINGS
  "character_settings": {
    "mode": "auto_generate | persistent",
    "archetype": "anti_hero | innocent | broken_genius | survivor | villain_pov",
    "enable_internal_conflict": true,
    "enable_secret": true,
    "moral_dilemma_level": 4  // 1-5
  },

  // LOGIC SETTINGS
  "logic_settings": {
    "generate_plan_before_writing": true,
    "auto_consistency_check": true,
    "character_motivation_validation": true,
    "no_cliches_mode": true,
    "surprise_injection_level": 3  // 1-5
  },

  // REAL EVENTS SETTINGS (тільки якщо story_mode = "real_events")
  "real_events_settings": {
    "fact_strictness": "strict | documentary | dramatic_retelling",
    "enable_ethics_mode": true,
    "enable_speculation_blocker": true
  },

  // VARIATION SETS (вже існує, додати character_visual_profile)
  "variation_sets": [
    {
      "set_id": 0,
      "set_name": "Dark Cinematic",
      "visual_keywords": "...",
      // ... інші поля ...

      // НОВИЙ БЛОК для Character Visual Lock:
      "character_visual_profile": {
        "age": 35,
        "gender": "male",
        "hair_color": "dark brown",
        "distinctive_feature": "scar on left cheek",
        "clothing": "black wool coat"
      }
    }
  ]
}
```

---

## 🎨 ЗМІНИ В UI (channels-unified.js)

### **Додати нову секцію в Modal:**
```html
<!-- Section 4.7: STORY ENGINE -->
<div class="config-section">
  <h2>🎬 Story Engine Settings</h2>

  <!-- 4.7.1 Story Mode -->
  <div class="form-group">
    <label>Story Type</label>
    <div class="story-mode-selector">
      <div class="mode-card" data-value="fiction" onclick="setStoryMode('fiction')">
        <i class="bi bi-magic"></i>
        <h4>Fiction</h4>
        <p>Повна творча свобода</p>
      </div>
      <div class="mode-card" data-value="real_events" onclick="setStoryMode('real_events')">
        <i class="bi bi-book"></i>
        <h4>Real Events</h4>
        <p>Тільки факти</p>
      </div>
      <div class="mode-card" data-value="hybrid" onclick="setStoryMode('hybrid')">
        <i class="bi bi-film"></i>
        <h4>Hybrid</h4>
        <p>Факти + драма</p>
      </div>
    </div>
    <input type="hidden" id="story_mode" value="fiction">
  </div>

  <!-- 4.7.2 Story DNA -->
  <div class="form-group">
    <label>World Type</label>
    <select id="world_type">
      <option value="realistic">Realistic</option>
      <option value="medieval_fantasy">Medieval Fantasy</option>
      <option value="cyberpunk">Cyberpunk</option>
      <option value="post_apocalyptic">Post-Apocalyptic</option>
      <option value="alternate_reality">Alternate Reality</option>
    </select>
  </div>

  <div class="form-group">
    <label>Tone</label>
    <select id="tone">
      <option value="dark">Dark</option>
      <option value="emotional">Emotional</option>
      <option value="epic">Epic</option>
      <option value="calm">Calm</option>
      <option value="disturbing">Disturbing</option>
    </select>
  </div>

  <div class="form-group">
    <label>Psychological Depth: <span id="psychological_depth_value">3</span></label>
    <input type="range" id="psychological_depth" min="1" max="5" value="3" oninput="document.getElementById('psychological_depth_value').textContent = this.value">
  </div>

  <div class="form-group">
    <label>Plot Intensity: <span id="plot_intensity_value">4</span></label>
    <input type="range" id="plot_intensity" min="1" max="5" value="4" oninput="document.getElementById('plot_intensity_value').textContent = this.value">
  </div>

  <!-- 4.7.3 Story Structure -->
  <div class="form-group">
    <label>Story Structure Mode</label>
    <select id="story_structure_mode">
      <option value="one_shot">One-Shot Story</option>
      <option value="episodic">Episodic Series</option>
      <option value="infinite">Infinite Narrative</option>
    </select>
  </div>

  <!-- 4.7.4 Character Settings -->
  <div class="form-group">
    <label>Character Mode</label>
    <select id="character_mode">
      <option value="auto_generate">Auto Generate (новий кожної історії)</option>
      <option value="persistent">Persistent Character (серіал)</option>
    </select>
  </div>

  <div class="form-group">
    <label>Character Archetype</label>
    <select id="character_archetype">
      <option value="anti_hero">Anti-Hero</option>
      <option value="innocent">Innocent</option>
      <option value="broken_genius">Broken Genius</option>
      <option value="survivor">Survivor</option>
      <option value="villain_pov">Villain POV</option>
    </select>
  </div>

  <div class="form-group">
    <input type="checkbox" id="enable_internal_conflict" checked>
    <label>Enable Internal Conflict</label>
  </div>

  <div class="form-group">
    <input type="checkbox" id="enable_secret" checked>
    <label>Character has Secret</label>
  </div>

  <div class="form-group">
    <label>Moral Dilemma Level: <span id="moral_dilemma_level_value">3</span></label>
    <input type="range" id="moral_dilemma_level" min="1" max="5" value="3" oninput="document.getElementById('moral_dilemma_level_value').textContent = this.value">
  </div>

  <!-- 4.7.5 Logic Settings -->
  <div class="form-group">
    <h3>Logic & Consistency</h3>
    <input type="checkbox" id="generate_plan_before_writing" checked> Generate plan before writing<br>
    <input type="checkbox" id="auto_consistency_check" checked> Auto consistency check<br>
    <input type="checkbox" id="character_motivation_validation" checked> Character motivation validation<br>
    <input type="checkbox" id="no_cliches_mode" checked> No clichés mode<br>

    <label>Surprise Injection Level: <span id="surprise_injection_level_value">3</span></label>
    <input type="range" id="surprise_injection_level" min="1" max="5" value="3" oninput="document.getElementById('surprise_injection_level_value').textContent = this.value">
  </div>

  <!-- 4.7.6 Real Events Settings (показувати тільки якщо story_mode = "real_events") -->
  <div id="real_events_settings" style="display: none;">
    <h3>📚 Real Events Settings</h3>

    <div class="form-group">
      <label>Fact Strictness</label>
      <select id="fact_strictness">
        <option value="strict">Strict (тільки факти)</option>
        <option value="documentary">Documentary (факти + контекст)</option>
        <option value="dramatic_retelling">Dramatic Retelling (факти + драма)</option>
      </select>
    </div>

    <input type="checkbox" id="enable_ethics_mode" checked> Ethics Mode (захист жертв)<br>
    <input type="checkbox" id="enable_speculation_blocker" checked> Block Speculation
  </div>
</div>
```

### **JavaScript функції:**
```javascript
// Set story mode and toggle UI sections
function setStoryMode(mode) {
  document.getElementById('story_mode').value = mode;

  // Update mode cards
  document.querySelectorAll('.mode-card').forEach(card => {
    card.classList.toggle('active', card.dataset.value === mode);
  });

  // Show/hide Real Events settings
  const realEventsSection = document.getElementById('real_events_settings');
  if (mode === 'real_events' || mode === 'hybrid') {
    realEventsSection.style.display = 'block';
  } else {
    realEventsSection.style.display = 'none';
  }
}

// Save Story Engine settings to config
function saveStoryEngineSettings() {
  return {
    story_mode: document.getElementById('story_mode').value,
    story_dna: {
      world_type: document.getElementById('world_type').value,
      tone: document.getElementById('tone').value,
      psychological_depth: parseInt(document.getElementById('psychological_depth').value),
      plot_intensity: parseInt(document.getElementById('plot_intensity').value)
    },
    story_structure: {
      mode: document.getElementById('story_structure_mode').value,
      template: document.getElementById('story_structure_template')?.value || ''
    },
    character_settings: {
      mode: document.getElementById('character_mode').value,
      archetype: document.getElementById('character_archetype').value,
      enable_internal_conflict: document.getElementById('enable_internal_conflict').checked,
      enable_secret: document.getElementById('enable_secret').checked,
      moral_dilemma_level: parseInt(document.getElementById('moral_dilemma_level').value)
    },
    logic_settings: {
      generate_plan_before_writing: document.getElementById('generate_plan_before_writing').checked,
      auto_consistency_check: document.getElementById('auto_consistency_check').checked,
      character_motivation_validation: document.getElementById('character_motivation_validation').checked,
      no_cliches_mode: document.getElementById('no_cliches_mode').checked,
      surprise_injection_level: parseInt(document.getElementById('surprise_injection_level').value)
    },
    real_events_settings: {
      fact_strictness: document.getElementById('fact_strictness')?.value || 'strict',
      enable_ethics_mode: document.getElementById('enable_ethics_mode')?.checked || false,
      enable_speculation_blocker: document.getElementById('enable_speculation_blocker')?.checked || false
    }
  };
}
```

---

## 🔀 НОВИЙ STEP FUNCTIONS DEFINITION

### **Phase 1 - Content Generation (ПОВНА ПЕРЕБУДОВА):**

```json
{
  "Phase1ContentGeneration": {
    "Type": "Map",
    "ItemsPath": "$.channelsResult.data",
    "MaxConcurrency": 5,
    "Iterator": {
      "StartAt": "LoadChannelSettings",
      "States": {
        "LoadChannelSettings": {
          "Type": "Pass",
          "Comment": "Extract story_mode, story_dna, character_settings from channel config",
          "ResultPath": "$.storySettings",
          "Next": "StoryModeSwitch"
        },

        "StoryModeSwitch": {
          "Type": "Choice",
          "Comment": "Route based on story_mode: fiction / real_events / hybrid",
          "Choices": [
            {
              "Variable": "$.story_mode",
              "StringEquals": "fiction",
              "Next": "FictionBranch_ThemeAgent"
            },
            {
              "Variable": "$.story_mode",
              "StringEquals": "real_events",
              "Next": "RealEventsBranch_ThemeAgent"
            },
            {
              "Variable": "$.story_mode",
              "StringEquals": "hybrid",
              "Next": "HybridBranch_ThemeAgent"
            }
          ],
          "Default": "FictionBranch_ThemeAgent"
        },

        "FictionBranch_ThemeAgent": {
          "Type": "Task",
          "Resource": "arn:aws:states:::lambda:invoke",
          "Parameters": {
            "FunctionName": "content-theme-agent",
            "Payload": {
              "channel_id.$": "$.channel_id",
              "story_mode": "fiction"
            }
          },
          "ResultPath": "$.themeResult",
          "Next": "StoryPlanner"
        },

        "RealEventsBranch_ThemeAgent": {
          "Type": "Task",
          "Resource": "arn:aws:states:::lambda:invoke",
          "Comment": "For Real Events: ThemeAgent suggests real events topics",
          "Parameters": {
            "FunctionName": "content-theme-agent",
            "Payload": {
              "channel_id.$": "$.channel_id",
              "story_mode": "real_events",
              "genre.$": "$.genre"
            }
          },
          "ResultPath": "$.themeResult",
          "Next": "FactExtractor"
        },

        "HybridBranch_ThemeAgent": {
          "Type": "Task",
          "Resource": "arn:aws:states:::lambda:invoke",
          "Comment": "Hybrid mode: starts like Real Events",
          "Parameters": {
            "FunctionName": "content-theme-agent",
            "Payload": {
              "channel_id.$": "$.channel_id",
              "story_mode": "hybrid"
            }
          },
          "ResultPath": "$.themeResult",
          "Next": "FactExtractor"
        },

        "FactExtractor": {
          "Type": "Task",
          "Resource": "arn:aws:states:::lambda:invoke",
          "Comment": "Extract facts from Wikipedia (for Real/Hybrid modes)",
          "Parameters": {
            "FunctionName": "content-search-facts",
            "Payload": {
              "selected_topic.$": "$.themeResult.data.generated_titles[0]",
              "genre.$": "$.genre"
            }
          },
          "ResultPath": "$.factsResult",
          "Next": "TimelineBuilder",
          "Catch": [
            {
              "ErrorEquals": ["States.ALL"],
              "ResultPath": "$.factsError",
              "Next": "SetNoFacts"
            }
          ]
        },

        "TimelineBuilder": {
          "Type": "Task",
          "Resource": "arn:aws:states:::lambda:invoke",
          "Comment": "Build timeline from Wikipedia facts",
          "Parameters": {
            "FunctionName": "content-timeline-builder",
            "Payload": {
              "wikipedia_facts.$": "$.factsResult.data.wikipedia_facts"
            }
          },
          "ResultPath": "$.timelineResult",
          "Next": "RealEventsOutlineGenerator"
        },

        "SetNoFacts": {
          "Type": "Pass",
          "Result": {
            "data": {
              "wikipedia_facts": null,
              "has_real_facts": false
            }
          },
          "ResultPath": "$.factsResult",
          "Next": "StoryPlanner"
        },

        "StoryPlanner": {
          "Type": "Task",
          "Resource": "arn:aws:states:::lambda:invoke",
          "Comment": "Create story plan (Fiction/Hybrid modes)",
          "Parameters": {
            "FunctionName": "content-story-planner",
            "Payload": {
              "channel_id.$": "$.channel_id",
              "user_id.$": "$.user_id",
              "selected_topic.$": "$.themeResult.data.generated_titles[0]",
              "story_dna.$": "$.story_dna",
              "story_structure.$": "$.story_structure",
              "character_settings.$": "$.character_settings",
              "story_mode.$": "$.story_mode"
            }
          },
          "ResultPath": "$.storyPlan",
          "Next": "CharacterBuilder"
        },

        "CharacterBuilder": {
          "Type": "Task",
          "Resource": "arn:aws:states:::lambda:invoke",
          "Comment": "Build characters (Fiction/Hybrid)",
          "Parameters": {
            "FunctionName": "content-character-builder",
            "Payload": {
              "story_plan.$": "$.storyPlan.data",
              "character_settings.$": "$.character_settings",
              "story_mode.$": "$.story_mode"
            }
          },
          "ResultPath": "$.charactersResult",
          "Next": "CheckIfFictionForWorld"
        },

        "CheckIfFictionForWorld": {
          "Type": "Choice",
          "Comment": "WorldBuilder only for pure Fiction",
          "Choices": [
            {
              "Variable": "$.story_mode",
              "StringEquals": "fiction",
              "Next": "WorldBuilder"
            }
          ],
          "Default": "OutlineGenerator"
        },

        "WorldBuilder": {
          "Type": "Task",
          "Resource": "arn:aws:states:::lambda:invoke",
          "Comment": "Build fictional world (Fiction only)",
          "Parameters": {
            "FunctionName": "content-world-builder",
            "Payload": {
              "story_plan.$": "$.storyPlan.data",
              "world_type.$": "$.story_dna.world_type",
              "tone.$": "$.story_dna.tone"
            }
          },
          "ResultPath": "$.worldResult",
          "Next": "OutlineGenerator"
        },

        "OutlineGenerator": {
          "Type": "Task",
          "Resource": "arn:aws:states:::lambda:invoke",
          "Comment": "Generate detailed scene-by-scene outline",
          "Parameters": {
            "FunctionName": "content-outline-generator",
            "Payload": {
              "story_plan.$": "$.storyPlan.data",
              "characters.$": "$.charactersResult.data.characters",
              "world.$": "$.worldResult.data.world",
              "story_mode.$": "$.story_mode"
            }
          },
          "ResultPath": "$.outlineResult",
          "Next": "MegaNarrativeGenerator"
        },

        "RealEventsOutlineGenerator": {
          "Type": "Task",
          "Resource": "arn:aws:states:::lambda:invoke",
          "Comment": "Generate outline from facts timeline (Real Events)",
          "Parameters": {
            "FunctionName": "content-outline-generator",
            "Payload": {
              "facts_timeline.$": "$.timelineResult.data.timeline",
              "story_mode": "real_events",
              "fact_strictness.$": "$.real_events_settings.fact_strictness"
            }
          },
          "ResultPath": "$.outlineResult",
          "Next": "MegaNarrativeGenerator"
        },

        "MegaNarrativeGenerator": {
          "Type": "Task",
          "Resource": "arn:aws:states:::lambda:invoke",
          "Comment": "Write narrative based on outline (SIMPLIFIED - no image prompts here)",
          "Parameters": {
            "FunctionName": "content-narrative",
            "Payload": {
              "channel_id.$": "$.channel_id",
              "user_id.$": "$.user_id",
              "selected_topic.$": "$.themeResult.data.generated_titles[0]",
              "outline.$": "$.outlineResult.data.outline",
              "characters.$": "$.charactersResult.data.characters",
              "world.$": "$.worldResult.data.world",
              "story_mode.$": "$.story_mode",
              "wikipedia_facts.$": "$.factsResult.data.wikipedia_facts"
            }
          },
          "ResultPath": "$.narrativeResult",
          "Next": "ConsistencyChecker"
        },

        "ConsistencyChecker": {
          "Type": "Task",
          "Resource": "arn:aws:states:::lambda:invoke",
          "Comment": "Check narrative for logic errors, timeline issues, character inconsistencies",
          "Parameters": {
            "FunctionName": "content-consistency-checker",
            "Payload": {
              "narrative.$": "$.narrativeResult.data",
              "outline.$": "$.outlineResult.data.outline",
              "characters.$": "$.charactersResult.data.characters",
              "story_mode.$": "$.story_mode",
              "logic_settings.$": "$.logic_settings"
            }
          },
          "ResultPath": "$.consistencyReport",
          "Next": "CheckConsistencyStatus",
          "Catch": [
            {
              "ErrorEquals": ["States.ALL"],
              "ResultPath": "$.consistencyError",
              "Next": "ImagePromptGenerator"
            }
          ]
        },

        "CheckConsistencyStatus": {
          "Type": "Choice",
          "Comment": "If consistency check failed, optionally retry or log warning",
          "Choices": [
            {
              "Variable": "$.consistencyReport.data.status",
              "StringEquals": "failed",
              "Next": "LogConsistencyWarning"
            }
          ],
          "Default": "ImagePromptGenerator"
        },

        "LogConsistencyWarning": {
          "Type": "Pass",
          "Comment": "Log consistency errors but continue",
          "ResultPath": "$.consistencyWarning",
          "Next": "ImagePromptGenerator"
        },

        "ImagePromptGenerator": {
          "Type": "Task",
          "Resource": "arn:aws:states:::lambda:invoke",
          "Comment": "Generate image prompts with Global Visual Style from Variation Sets",
          "Parameters": {
            "FunctionName": "content-image-prompt-generator",
            "Payload": {
              "narrative.$": "$.narrativeResult.data",
              "variation_set.$": "$.current_variation_set",
              "character_visual_profile.$": "$.charactersResult.data.characters[0].visual_profile",
              "story_mode.$": "$.story_mode",
              "world_type.$": "$.story_dna.world_type"
            }
          },
          "ResultPath": "$.imagePromptsResult",
          "End": true
        }
      }
    },
    "Next": "Phase2Start"
  }
}
```

---

## 📋 MIGRATION PLAN

### **Phase 1: UI Changes (1-2 дні)**
1. Додати Story Engine секцію в `channels-unified.js`
2. Додати всі нові поля в Modal
3. Додати Character Visual Profile в Variation Set Modal
4. Протестувати збереження/завантаження нових полів

### **Phase 2: DynamoDB Schema (1 день)**
1. Додати нові поля в `update-channel-config.php` (або Lambda якщо вже міграція)
2. Протестувати збереження нових полів
3. Додати дефолтні значення для існуючих каналів

### **Phase 3: Lambda Functions (1 тиждень)**
1. Створити `content-story-planner`
2. Створити `content-character-builder`
3. Створити `content-world-builder`
4. Створити `content-outline-generator`
5. Створити `content-consistency-checker`
6. Створити `content-image-prompt-generator`
7. Рефакторити `content-narrative` (спростити, прибрати image generation)

### **Phase 4: Step Functions (2-3 дні)**
1. Створити новий State Machine definition
2. Протестувати кожну гілку (Fiction/Real/Hybrid)
3. Перевірити data flow між Lambda функціями

### **Phase 5: Testing (3-5 днів)**
1. Тестування Fiction mode end-to-end
2. Тестування Real Events mode
3. Тестування Hybrid mode
4. Тестування Visual Consistency (Variation Sets)
5. Тестування Character Consistency (persistent characters)

### **Phase 6: Deployment (1 день)**
1. Deploy всіх Lambda функцій
2. Update Step Functions definition
3. Rollback plan (якщо щось зламається)

---

## ✅ BACKWARDS COMPATIBILITY

**ВАЖЛИВО:** Зберегти сумісність з існуючими каналами!

### **Дефолтні значення для існуючих каналів:**
```json
{
  "story_mode": "fiction",  // дефолт для всіх існуючих каналів
  "story_dna": {
    "world_type": "realistic",
    "tone": "dark",
    "psychological_depth": 3,
    "plot_intensity": 3
  },
  "story_structure": {
    "mode": "one_shot",
    "template": ""
  },
  "character_settings": {
    "mode": "auto_generate",
    "archetype": "anti_hero",
    "enable_internal_conflict": true,
    "enable_secret": false,
    "moral_dilemma_level": 3
  },
  "logic_settings": {
    "generate_plan_before_writing": true,
    "auto_consistency_check": false,  // вимкнено за дефолтом для швидкості
    "character_motivation_validation": false,
    "no_cliches_mode": false,
    "surprise_injection_level": 3
  }
}
```

### **Fallback Logic в Lambda функціях:**
```python
# У кожній новій Lambda функції:
def lambda_handler(event, context):
    story_mode = event.get('story_mode', 'fiction')  # fallback to fiction
    story_dna = event.get('story_dna', {
        'world_type': 'realistic',
        'tone': 'dark',
        'psychological_depth': 3,
        'plot_intensity': 3
    })
    # ...
```

---

## 🎯 SUCCESS METRICS

### **Якість історій:**
- ✅ 90%+ Consistency Check Pass Rate
- ✅ 80%+ No Clichés Detection
- ✅ Character consistency across episodes (для серіалів)

### **Visual Consistency:**
- ✅ 95%+ Same Style Score (image similarity check)
- ✅ Character Visual Lock збережено в 100% сцен

### **Performance:**
- ⏱️ Total Phase 1 time: < 5 хвилин (замість 2 хвилин зараз)
  - Допустимо, бо якість важливіша за швидкість
- 💰 Cost: +30% OpenAI API calls (більше етапів)
  - Але якість значно краща → менше відбракованих історій

---

## 📚 NEXT STEPS

1. **Обговорити з користувачем:**
   - Чи згоден з архітектурою?
   - Які пріоритети (Fiction / Real Events / Hybrid)?
   - Чи потрібні всі етапи або можна спростити?

2. **Початок розробки:**
   - Почати з UI (найпростіше)
   - Потім DynamoDB schema
   - Потім Lambda функції по одній

3. **Тестування:**
   - Створити тестовий канал для кожного режиму
   - Згенерувати 5-10 історій для перевірки consistency

---

## 🔥 ВИСНОВОК

Нова архітектура дає:
- ✅ **Контроль якості** через багатоетапну генерацію
- ✅ **Візуальну консистентність** через Visual Style Lock
- ✅ **Логічні історії** через Consistency Checker
- ✅ **Реальні події** через Wikipedia integration
- ✅ **Серіали** через Persistent Characters

**Trade-off:**
- ⏱️ +2-3 хвилини на генерацію (5 хвилин замість 2)
- 💰 +30% вартість API calls

**Але:** Якість історій значно краща → більше views → більше revenue! 🚀

---

**ГОТОВО ДО РЕАЛІЗАЦІЇ! 🎉**
