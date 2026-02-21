# 📋 Story Engineering System - Implementation Plan

**Version:** v1.0
**Date:** 2026-02-20
**Total Duration:** 3 weeks (3 sprints)

---

## 🎯 SPRINT 1: MVP - Topics Queue + Basic Story Profile (Week 1)

**Goal:** Мінімальна робоча версія для User Mode з Topics Queue та базовими Story настройками.

### **Day 1-2: Topics Queue Backend**

#### **Task 1.1: Create DynamoDB Table**
```bash
Table: ContentTopicsQueue
PK: channel_id (String)
SK: topic_id (String)
GSI: status-index (channel_id + status)
```

**Fields (MVP version):**
```json
{
  "channel_id": "UCxxx",
  "topic_id": "uuid",
  "topic_text": "The Hidden Temples of Angkor Wat",
  "topic_description": {
    "context": "Brief historical/situational context",
    "tone_suggestion": "dark / emotional / epic / calm",
    "key_elements": ["temples", "mystery", "discovery"]
  },
  "priority": 100,
  "status": "draft",  // draft → approved → queued → in_progress → published
  "source": "manual",  // manual / ai_generated
  "created_at": "2026-02-20T...",
  "updated_at": "2026-02-20T...",
  "user_id": "xxx"
}
```

**Files:**
- `aws/dynamodb/create-topics-queue-table.json`
- Script: `aws/scripts/create-topics-table.sh`

---

#### **Task 1.2: Lambda - content-topics-add**
**Path:** `aws/lambda/content-topics-add/`

**Functionality:**
- Add topic manually (user input)
- Validate fields
- Generate topic_id (UUID)
- Set status = "draft"
- Save to DynamoDB

**Input:**
```json
{
  "user_id": "xxx",
  "channel_id": "UCxxx",
  "topic_text": "...",
  "topic_description": {
    "context": "...",
    "tone_suggestion": "dark",
    "key_elements": ["...", "..."]
  },
  "priority": 100
}
```

**Output:**
```json
{
  "success": true,
  "topic_id": "uuid",
  "message": "Topic added successfully"
}
```

**Files:**
- `lambda_function.py`
- `create_zip.py`

---

#### **Task 1.3: Lambda - content-topics-list**
**Path:** `aws/lambda/content-topics-list/`

**Functionality:**
- List all topics for channel
- Filter by status (optional)
- Sort by priority + created_at
- Pagination support

**Input:**
```json
{
  "user_id": "xxx",
  "channel_id": "UCxxx",
  "status": "draft",  // optional filter
  "limit": 50
}
```

**Output:**
```json
{
  "topics": [
    {
      "topic_id": "...",
      "topic_text": "...",
      "status": "draft",
      "priority": 100,
      "created_at": "..."
    }
  ],
  "count": 15,
  "next_token": null
}
```

**Files:**
- `lambda_function.py`
- `create_zip.py`

---

#### **Task 1.4: Lambda - content-topics-get-next**
**Path:** `aws/lambda/content-topics-get-next/`

**Functionality:**
- Get next "queued" topic for channel
- Sort by priority DESC
- Mark as "in_progress"
- Return full topic object

**Input:**
```json
{
  "user_id": "xxx",
  "channel_id": "UCxxx"
}
```

**Output:**
```json
{
  "topic_id": "...",
  "topic_text": "...",
  "topic_description": {...},
  "priority": 100
}
```

**Files:**
- `lambda_function.py`
- `create_zip.py`

---

#### **Task 1.5: Lambda - content-topics-update-status**
**Path:** `aws/lambda/content-topics-update-status/`

**Functionality:**
- Update topic status
- State transitions: draft → approved → queued → in_progress → published
- Validation (can't skip states)

**Input:**
```json
{
  "user_id": "xxx",
  "channel_id": "UCxxx",
  "topic_id": "uuid",
  "new_status": "approved"
}
```

**Files:**
- `lambda_function.py`
- `create_zip.py`

---

### **Day 3-4: Topics Queue Frontend (UI)**

#### **Task 1.6: Create topics-manager.html**
**Path:** `topics-manager.html`

**Sections:**

**1. Header**
- Title: "📋 Topics Queue Manager"
- Current Channel selector dropdown

**2. Add Topic Form (Collapsible)**
```html
<details class="add-topic-form">
  <summary>➕ Add New Topic</summary>
  <form id="addTopicForm">
    <input id="topic_text" placeholder="Topic title..." />

    <label>📝 Description</label>
    <textarea id="topic_context" placeholder="Brief context..."></textarea>

    <label>🎨 Tone Suggestion</label>
    <select id="tone_suggestion">
      <option value="dark">Dark</option>
      <option value="emotional">Emotional</option>
      <option value="epic">Epic</option>
      <option value="calm">Calm</option>
    </select>

    <label>🔑 Key Elements (comma-separated)</label>
    <input id="key_elements" placeholder="temples, mystery, discovery" />

    <label>⭐ Priority</label>
    <input type="number" id="priority" value="100" />

    <button type="submit">Add Topic</button>
  </form>
</details>
```

**3. Topics List Table**
```html
<table id="topicsTable">
  <thead>
    <tr>
      <th>Status</th>
      <th>Priority</th>
      <th>Topic</th>
      <th>Tone</th>
      <th>Created</th>
      <th>Actions</th>
    </tr>
  </thead>
  <tbody id="topicsTableBody">
    <!-- Dynamically populated -->
  </tbody>
</table>
```

**4. Status Filter Tabs**
```html
<div class="status-filters">
  <button data-status="all" class="active">All</button>
  <button data-status="draft">Draft</button>
  <button data-status="approved">Approved</button>
  <button data-status="queued">Queued</button>
  <button data-status="in_progress">In Progress</button>
  <button data-status="published">Published</button>
</div>
```

**Files:**
- `topics-manager.html`
- `js/topics-manager.js`
- `css/topics-manager.css`

---

#### **Task 1.7: JavaScript - topics-manager.js**
**Path:** `js/topics-manager.js`

**Functions:**
```javascript
// Load topics list
async function loadTopics(channelId, status = 'all') {}

// Add new topic
async function addTopic(formData) {}

// Update topic status
async function updateTopicStatus(topicId, newStatus) {}

// Delete topic
async function deleteTopic(topicId) {}

// Render topics table
function renderTopicsTable(topics) {}

// Event listeners
document.getElementById('addTopicForm').addEventListener('submit', addTopic);
```

---

### **Day 5-6: Story Profile Integration**

#### **Task 1.8: Add Story Profile Fields to channels.html**

**Add new section after Manual Input Mode:**

```html
<!-- ═══ STORY PROFILE (BASIC) ═══ -->
<details class="advanced-settings">
  <summary>📖 Story Profile</summary>
  <div class="advanced-settings-body">

    <div class="form-group full">
      <label>🎭 Atmosphere</label>
      <select id="atmosphere">
        <option value="dark">Dark</option>
        <option value="light">Light</option>
        <option value="mysterious">Mysterious</option>
        <option value="uplifting">Uplifting</option>
      </select>
    </div>

    <div class="form-group full">
      <label>⚡ Pacing</label>
      <select id="pacing">
        <option value="slow">Slow Burn</option>
        <option value="medium">Medium</option>
        <option value="fast">Fast Paced</option>
      </select>
    </div>

    <div class="form-group full">
      <label>🧠 Depth</label>
      <select id="depth">
        <option value="simple">Simple</option>
        <option value="medium">Medium</option>
        <option value="deep">Deep</option>
      </select>
    </div>

    <div class="form-group full">
      <label>🔥 Intensity Level</label>
      <input type="range" id="intensity_level" min="1" max="5" value="3" />
      <div style="display: flex; justify-content: space-between;">
        <span>1 (Calm)</span>
        <span id="intensity_level_value">3</span>
        <span>5 (Extreme)</span>
      </div>
    </div>

  </div>
</details>
```

**Update JavaScript:**
- Add fields to `populateForm()` array
- Add fields to `saveModalConfig()`

---

#### **Task 1.9: Lambda - build-master-config**
**Path:** `aws/lambda/build-master-config/`

**Functionality:**
- Merge channel_config + topic + story_profile
- Build centralized MasterConfig object

**Input:**
```json
{
  "user_id": "xxx",
  "channel_id": "UCxxx",
  "topic_id": "uuid"
}
```

**Output (MasterConfig):**
```json
{
  "channel_context": {
    "channel_id": "UCxxx",
    "channel_name": "...",
    "language": "en",
    "genre": "..."
  },
  "topic": {
    "topic_text": "...",
    "topic_description": {...}
  },
  "story_profile": {
    "atmosphere": "dark",
    "pacing": "medium",
    "depth": "deep",
    "intensity_level": 3
  }
}
```

**Files:**
- `lambda_function.py`
- `config_builder.py`
- `create_zip.py`

---

#### **Task 1.10: Update content-narrative Lambda**

**Modify:** `aws/lambda/content-narrative/lambda_function.py`

**Changes:**
1. Call `build-master-config` Lambda before OpenAI
2. Use MasterConfig instead of only channel_config
3. Inject topic_description into prompt
4. Pass story_profile to mega_prompt_builder

**New flow:**
```python
# 1. Build MasterConfig
master_config = invoke_lambda('build-master-config', {
    'user_id': user_id,
    'channel_id': channel_id,
    'topic_id': topic_id  # From Topics Queue
})

# 2. Build prompt with MasterConfig
system_message, user_message = build_mega_prompt(
    master_config,
    selected_topic
)

# 3. Call OpenAI
# ...
```

---

### **Day 7: Testing & Deployment**

#### **Task 1.11: End-to-End Testing**

**Test Flow:**
1. Add topic manually via topics-manager.html
2. Approve topic (status: draft → approved → queued)
3. Trigger content generation
4. Verify GetNextTopic is called
5. Verify MasterConfig is built
6. Verify content-narrative receives correct config
7. Verify topic status changes to "in_progress" → "published"

**Test Checklist:**
- [ ] Topics CRUD operations work
- [ ] Status transitions validate correctly
- [ ] MasterConfig merges all layers
- [ ] Story Profile affects OpenAI prompt
- [ ] Topic description injected into narrative

---

#### **Task 1.12: Deploy to Production**

**Deploy:**
- [ ] DynamoDB table ContentTopicsQueue
- [ ] 5 Lambda functions (topics-add, topics-list, topics-get-next, topics-update-status, build-master-config)
- [ ] topics-manager.html to server
- [ ] Updated channels.html to server
- [ ] Updated content-narrative Lambda

**Git Commit:**
```bash
git commit -m "feat: Sprint 1 - Topics Queue + Basic Story Profile (MVP)

- Created ContentTopicsQueue DynamoDB table
- Implemented 5 Topics Lambda functions
- Built Topics Manager UI
- Added Story Profile fields to Channel Config
- Created MasterConfig builder
- Integrated Topics Queue into content-narrative pipeline

Sprint 1 Complete ✅"
```

---

## 🚀 SPRINT 2: Advanced Features - DNA Layers + Retention (Week 2)

**Goal:** Додати Channel DNA (Visual/Voice/Narrative), Character Engine, Retention Profile.

### **Day 1-2: Channel DNA Implementation**

#### **Task 2.1: Visual DNA UI**

**Add to channels.html:**

```html
<!-- ═══ VISUAL DNA ═══ -->
<details class="advanced-settings">
  <summary>🎨 Visual DNA</summary>
  <div class="advanced-settings-body">

    <div class="form-group full">
      <label>Style Preset</label>
      <select id="visual_style_preset">
        <option value="cinematic_dark">Cinematic Dark</option>
        <option value="anime">Anime</option>
        <option value="photorealistic">Photorealistic</option>
        <option value="oil_painting">Oil Painting</option>
      </select>
    </div>

    <div class="form-group full">
      <label>Custom Style Description (optional)</label>
      <textarea id="visual_custom_style" placeholder="e.g. 1980s VHS aesthetic with grain..."></textarea>
    </div>

    <div class="form-group full">
      <label>Style Strength</label>
      <input type="range" id="visual_style_strength" min="0" max="1" step="0.1" value="0.8" />
      <span id="visual_style_strength_value">0.8</span>
    </div>

    <div class="form-group full">
      <label>Lighting Profile</label>
      <select id="visual_lighting_profile">
        <option value="moonlight">Moonlight</option>
        <option value="golden_hour">Golden Hour</option>
        <option value="studio">Studio</option>
        <option value="neon">Neon</option>
      </select>
    </div>

    <div class="form-group full">
      <label>Primary Color</label>
      <select id="visual_color_primary">
        <option value="cold_blue">Cold Blue</option>
        <option value="warm_amber">Warm Amber</option>
        <option value="crimson">Crimson</option>
        <option value="emerald">Emerald</option>
      </select>
    </div>

    <div class="form-group full">
      <label>Saturation (%)</label>
      <input type="range" id="visual_saturation" min="0" max="100" value="65" />
      <span id="visual_saturation_value">65</span>
    </div>

    <div class="form-group full">
      <label>
        <input type="checkbox" id="visual_consistency_lock" checked />
        Lock Consistency (same style across all scenes)
      </label>
    </div>

  </div>
</details>
```

**Fields to save in ChannelConfigs:**
```json
{
  "visual_dna": {
    "style_preset": "cinematic_dark",
    "custom_style_description": "",
    "style_strength": 0.8,
    "lighting_profile": "moonlight",
    "color_palette": {
      "primary": "cold_blue",
      "saturation": 65
    },
    "consistency_lock": true
  }
}
```

---

#### **Task 2.2: Voice DNA UI**

```html
<!-- ═══ VOICE DNA ═══ -->
<details class="advanced-settings">
  <summary>🎤 Voice DNA</summary>
  <div class="advanced-settings-body">

    <div class="form-group full">
      <label>Voice Model ID</label>
      <input type="text" id="voice_model_id" placeholder="clone_001 or leave empty for default" />
    </div>

    <div class="form-group full">
      <label>Voice Character Description</label>
      <textarea id="voice_character_description" placeholder="e.g. Deep, gravelly narrator voice with subtle British accent..."></textarea>
    </div>

    <div class="form-group full">
      <label>Emotion Expression Level</label>
      <select id="voice_emotion_expression">
        <option value="minimal">Minimal</option>
        <option value="natural">Natural</option>
        <option value="expressive">Expressive</option>
      </select>
    </div>

    <div class="form-group full">
      <label>Tempo</label>
      <input type="range" id="voice_tempo" min="0.7" max="1.3" step="0.05" value="0.95" />
      <span id="voice_tempo_value">0.95</span>
    </div>

    <div class="form-group full">
      <label>
        <input type="checkbox" id="voice_tone_stability_lock" checked />
        Tone Stability Lock
      </label>
    </div>

    <div class="form-group full">
      <label>
        <input type="checkbox" id="voice_dynamic_emotion" checked />
        Dynamic Emotion Mode (sync with scene mood)
      </label>
    </div>

  </div>
</details>
```

---

#### **Task 2.3: Narrative DNA UI**

```html
<!-- ═══ NARRATIVE DNA ═══ -->
<details class="advanced-settings">
  <summary>📚 Narrative DNA</summary>
  <div class="advanced-settings-body">

    <div class="form-group full">
      <label>Default Structure Type</label>
      <select id="narrative_default_structure">
        <option value="slow_burn">Slow Burn</option>
        <option value="hero_journey">Hero's Journey</option>
        <option value="mystery_box">Mystery Box</option>
        <option value="three_act">Three Act Structure</option>
      </select>
    </div>

    <div class="form-group full">
      <label>Complexity Level</label>
      <select id="narrative_complexity">
        <option value="simple">Simple</option>
        <option value="medium">Medium</option>
        <option value="complex">Complex</option>
      </select>
    </div>

    <div class="form-group full">
      <label>Audience Level</label>
      <select id="narrative_audience_level">
        <option value="general">General Audience</option>
        <option value="mature">Mature</option>
        <option value="young_adult">Young Adult</option>
      </select>
    </div>

    <div class="form-group full">
      <label>Default Tone</label>
      <select id="narrative_default_tone">
        <option value="dark">Dark</option>
        <option value="light">Light</option>
        <option value="balanced">Balanced</option>
      </select>
    </div>

  </div>
</details>
```

---

### **Day 3-4: Character Engine**

#### **Task 2.4: Character Engine UI**

```html
<!-- ═══ CHARACTER ENGINE ═══ -->
<details class="advanced-settings">
  <summary>👤 Character Engine</summary>
  <div class="advanced-settings-body">

    <h4>Protagonist</h4>

    <div class="form-group full">
      <label>Type</label>
      <select id="char_protagonist_type">
        <option value="reluctant_hero">Reluctant Hero</option>
        <option value="anti_hero">Anti-Hero</option>
        <option value="everyman">Everyman</option>
        <option value="tragic_hero">Tragic Hero</option>
      </select>
    </div>

    <div class="form-group full">
      <label>
        <input type="checkbox" id="char_internal_conflict" checked />
        Internal Conflict
      </label>
    </div>

    <div class="form-group full">
      <label>Arc Type</label>
      <select id="char_arc_type">
        <option value="growth">Growth</option>
        <option value="fall">Fall</option>
        <option value="flat">Flat (no change)</option>
      </select>
    </div>

    <hr />

    <h4>Secondary Characters</h4>

    <div id="secondary-characters-list">
      <!-- Dynamically populated -->
    </div>

    <button type="button" onclick="addSecondaryCharacter()">
      ➕ Add Secondary Character
    </button>

  </div>
</details>
```

**Secondary Character Form:**
```html
<div class="secondary-character-card">
  <input placeholder="Character name" />
  <select>
    <option value="mentor">Mentor</option>
    <option value="sidekick">Sidekick</option>
    <option value="antagonist">Antagonist</option>
    <option value="love_interest">Love Interest</option>
  </select>
  <input placeholder="Function in story..." />
  <select>
    <option value="early_story">Early Story</option>
    <option value="mid_story">Mid Story</option>
    <option value="late_story">Late Story</option>
  </select>
  <button onclick="removeCharacter()">🗑️</button>
</div>
```

**Save format:**
```json
{
  "character_engine": {
    "protagonist": {
      "type": "reluctant_hero",
      "internal_conflict": true,
      "arc_type": "growth"
    },
    "secondary_characters": [
      {
        "name": "Old Wizard",
        "role": "mentor",
        "function": "Guides protagonist in early chapters",
        "screen_presence": "early_story"
      }
    ]
  }
}
```

---

### **Day 5-6: Retention Profile**

#### **Task 2.5: Retention Profile UI (Admin Only)**

**Create:** `admin/retention-settings.html`

```html
<!-- ═══ RETENTION PROFILE ═══ -->
<div class="retention-settings">

  <h3>🎯 Retention Strategy</h3>

  <div class="form-group">
    <label>Target Retention %</label>
    <input type="number" id="retention_target_percent" value="65" />
  </div>

  <div class="form-group">
    <label>Hook Aggression (1-5)</label>
    <input type="range" id="retention_hook_aggression" min="1" max="5" value="4" />
    <span id="retention_hook_aggression_value">4</span>
  </div>

  <div class="form-group">
    <label>Micro-Hook Interval (seconds)</label>
    <input type="number" id="retention_micro_hook_interval" value="45" />
  </div>

  <div class="form-group">
    <label>Cliffhanger Positions</label>
    <select id="retention_cliffhanger_positions" multiple>
      <option value="before_climax">Before Climax</option>
      <option value="mid_story">Mid Story</option>
      <option value="early">Early Hook</option>
    </select>
  </div>

  <div class="form-group">
    <label>Emotional Peak Timing (%)</label>
    <input type="number" id="retention_emotional_peak_percent" value="70" />
  </div>

  <div class="form-group">
    <label>
      <input type="checkbox" id="retention_early_payoff" />
      Early Payoff (give satisfaction early to retain viewers)
    </label>
  </div>

</div>
```

**Save as global template or per-channel:**
```json
{
  "retention_profile": {
    "target_retention_percent": 65,
    "hook_aggression": 4,
    "micro_hook_interval_seconds": 45,
    "cliffhanger_positions": ["before_climax"],
    "emotional_peak_timing_percent": 70,
    "early_payoff": false
  }
}
```

---

### **Day 7: MasterConfig Update + Testing**

#### **Task 2.6: Update build-master-config Lambda**

**Add all new layers:**
```python
def build_master_config(channel_config, topic):
    """Build complete MasterConfig with all DNA layers"""

    return {
        # Layer 1: Channel DNA
        "visual_dna": channel_config.get('visual_dna', {}),
        "voice_dna": channel_config.get('voice_dna', {}),
        "narrative_dna": channel_config.get('narrative_dna', {}),

        # Layer 2: Topic
        "topic": topic,

        # Layer 3: Story Profile
        "story_profile": {
            "atmosphere": channel_config.get('atmosphere', 'dark'),
            "pacing": channel_config.get('pacing', 'medium'),
            "depth": channel_config.get('depth', 'medium'),
            "intensity_level": channel_config.get('intensity_level', 3)
        },

        # Layer 4: Character Engine
        "character_engine": channel_config.get('character_engine', {}),

        # Layer 5: Retention Profile
        "retention_profile": channel_config.get('retention_profile', {}),

        # Base context
        "channel_context": {
            "channel_id": channel_config['channel_id'],
            "channel_name": channel_config.get('channel_name'),
            "language": channel_config.get('language', 'en'),
            "genre": channel_config.get('genre')
        }
    }
```

---

#### **Task 2.7: Update mega_prompt_builder.py**

**Inject all DNA layers into OpenAI prompt:**

```python
def build_system_message(master_config):
    """Build system message with all DNA layers"""

    visual_dna = master_config.get('visual_dna', {})
    voice_dna = master_config.get('voice_dna', {})
    narrative_dna = master_config.get('narrative_dna', {})
    story_profile = master_config.get('story_profile', {})
    character_engine = master_config.get('character_engine', {})
    retention_profile = master_config.get('retention_profile', {})

    system_message = f"""
## VISUAL DNA
Style: {visual_dna.get('style_preset', 'cinematic_dark')}
Lighting: {visual_dna.get('lighting_profile', 'moonlight')}
Color Palette: {visual_dna.get('color_palette', {}).get('primary', 'cold_blue')}
Consistency: {'LOCKED - maintain exact style' if visual_dna.get('consistency_lock') else 'Flexible'}

## VOICE DNA
Emotion Level: {voice_dna.get('emotion_expression_level', 'natural')}
Tempo: {voice_dna.get('tempo', 0.95)}
Dynamic Emotion: {'ENABLED - sync with scene mood' if voice_dna.get('dynamic_emotion') else 'DISABLED'}

## STORY PROFILE
Atmosphere: {story_profile.get('atmosphere', 'dark')}
Pacing: {story_profile.get('pacing', 'medium')}
Depth: {story_profile.get('depth', 'medium')}
Intensity: {story_profile.get('intensity_level', 3)}/5

## CHARACTER ENGINE
Protagonist Type: {character_engine.get('protagonist', {}).get('type', 'reluctant_hero')}
Character Arc: {character_engine.get('protagonist', {}).get('arc_type', 'growth')}

## RETENTION STRATEGY
Hook Aggression: {retention_profile.get('hook_aggression', 4)}/5
Micro-hooks every: {retention_profile.get('micro_hook_interval_seconds', 45)}s
Emotional Peak at: {retention_profile.get('emotional_peak_timing_percent', 70)}%

Generate narrative following ALL these DNA parameters...
"""

    return system_message
```

---

## 🧪 SPRINT 3: Admin/Developer Mode + Analytics (Week 3)

**Goal:** Role-based access, Template Registry, Engine Inspector, Analytics.

### **Day 1-2: Authentication & Roles**

#### **Task 3.1: Implement Cognito User Pools**

**Setup:**
- Create Cognito User Pool
- Add custom attributes: `role` (user/admin/developer)
- Configure JWT tokens

**Lambda Authorizer:**
```python
def lambda_handler(event, context):
    """Verify JWT and extract role"""

    token = event['authorizationToken']
    decoded = verify_jwt(token)

    role = decoded.get('custom:role', 'user')
    user_id = decoded['sub']

    return {
        'principalId': user_id,
        'policyDocument': generate_policy('Allow', event['methodArn']),
        'context': {
            'role': role,
            'user_id': user_id
        }
    }
```

**Files:**
- `aws/lambda/authorizer/lambda_function.py`
- `aws/cognito/user-pool-config.json`

---

#### **Task 3.2: Role-Based UI Components**

**Update all HTML pages:**

```html
<script>
// Get user role from JWT
const userRole = authManager.getUserRole();  // 'user' / 'admin' / 'developer'

// Show/hide based on role
if (userRole === 'admin' || userRole === 'developer') {
  document.getElementById('admin-panel').style.display = 'block';
}

if (userRole === 'developer') {
  document.getElementById('developer-mode-toggle').style.display = 'block';
}
</script>
```

**Create:** `js/auth-manager.js`
```javascript
class AuthManager {
  getUserRole() {
    const token = localStorage.getItem('jwt_token');
    const decoded = parseJwt(token);
    return decoded['custom:role'] || 'user';
  }

  hasPermission(feature) {
    const role = this.getUserRole();
    const permissions = {
      'edit_templates': ['admin', 'developer'],
      'view_analytics': ['admin', 'developer'],
      'engine_inspector': ['developer'],
      'retention_settings': ['admin', 'developer']
    };
    return permissions[feature]?.includes(role) || false;
  }
}
```

---

### **Day 3-4: Template Registry (Admin)**

#### **Task 3.3: Template Manager UI**

**Create:** `admin/template-registry.html`

```html
<div class="template-registry">

  <h2>📚 Template Registry</h2>

  <button onclick="createNewTemplate()">➕ Create New Template</button>

  <table id="templatesTable">
    <thead>
      <tr>
        <th>Template ID</th>
        <th>Name</th>
        <th>Type</th>
        <th>Status</th>
        <th>Success Rate</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      <!-- Populated dynamically -->
    </tbody>
  </table>

</div>

<!-- Template Editor Modal -->
<div id="templateEditorModal" class="modal">
  <h3>Edit Template</h3>

  <label>Template Name</label>
  <input id="template_name" />

  <label>Structure Type</label>
  <select id="template_structure_type">
    <option value="slow_burn">Slow Burn</option>
    <option value="mystery_box">Mystery Box</option>
    <!-- ... -->
  </select>

  <label>Emotional Curve (JSON)</label>
  <textarea id="template_emotional_curve" rows="10"></textarea>

  <label>Hook Template</label>
  <textarea id="template_hook_template"></textarea>

  <button onclick="saveTemplate()">Save Template</button>
</div>
```

---

#### **Task 3.4: Lambda - templates CRUD**

**Create:**
- `content-templates-list`
- `content-templates-create`
- `content-templates-update`
- `content-templates-delete`

**DynamoDB Table:** `ContentTemplates`
```json
{
  "template_id": "uuid",
  "template_name": "Dark Mystery Slow Burn",
  "template_type": "structure",
  "structure_config": {
    "type": "slow_burn",
    "emotional_curve": [0.2, 0.3, 0.5, 0.7, 0.9, 0.6],
    "hook_template": "...",
    "pacing_rules": {...}
  },
  "retention_config": {...},
  "status": "active",
  "success_metrics": {
    "avg_retention": 67.5,
    "videos_generated": 143
  },
  "created_by": "admin_user_id",
  "created_at": "..."
}
```

---

### **Day 5-6: Engine Inspector (Developer Mode)**

#### **Task 3.5: Engine Inspector Panel**

**Create:** `developer/engine-inspector.html`

```html
<div class="engine-inspector">

  <h2>🧠 Engine Inspector</h2>

  <div class="tabs">
    <button onclick="showTab('master-config')">Master Config</button>
    <button onclick="showTab('emotional-curve')">Emotional Curve</button>
    <button onclick="showTab('retention-metrics')">Retention Metrics</button>
    <button onclick="showTab('character-graph')">Character Graph</button>
    <button onclick="showTab('prompt-log')">Prompt Log</button>
    <button onclick="showTab('generation-log')">Generation Log</button>
  </div>

  <div id="tab-master-config" class="tab-content">
    <h3>Master Config JSON</h3>
    <pre id="master-config-json"></pre>
  </div>

  <div id="tab-emotional-curve" class="tab-content">
    <h3>Emotional Curve Graph</h3>
    <canvas id="emotional-curve-chart"></canvas>
  </div>

  <div id="tab-retention-metrics" class="tab-content">
    <h3>Retention Profile Calculation</h3>
    <table id="retention-metrics-table">
      <tr>
        <td>Target Retention:</td>
        <td id="retention-target"></td>
      </tr>
      <tr>
        <td>Hook Positions:</td>
        <td id="hook-positions"></td>
      </tr>
      <tr>
        <td>Micro-hooks inserted:</td>
        <td id="micro-hooks-count"></td>
      </tr>
    </table>
  </div>

  <div id="tab-prompt-log" class="tab-content">
    <h3>Prompt Injection Log</h3>
    <pre id="prompt-injection-log"></pre>
  </div>

  <div id="tab-generation-log" class="tab-content">
    <h3>Generation Step-by-step Log</h3>
    <div id="generation-steps"></div>
  </div>

</div>
```

---

#### **Task 3.6: Lambda - engine-inspect**

**Path:** `aws/lambda/engine-inspect/`

**Functionality:**
- Retrieve generation logs for content_id
- Parse MasterConfig used
- Calculate retention metrics
- Extract emotional curve data
- Return all debug info

**Input:**
```json
{
  "user_id": "xxx",
  "content_id": "narrative_20260220_001",
  "include_logs": true
}
```

**Output:**
```json
{
  "master_config": {...},
  "emotional_curve": [0.2, 0.3, ...],
  "retention_metrics": {
    "hook_positions": [0, 45, 90],
    "micro_hooks_count": 6,
    "emotional_peaks": [120, 240]
  },
  "prompt_log": "...",
  "generation_steps": [
    {"step": "Build MasterConfig", "duration_ms": 23},
    {"step": "Generate Outline", "duration_ms": 1542},
    ...
  ]
}
```

---

### **Day 7: Analytics Dashboard (Admin)**

#### **Task 3.7: Analytics Dashboard UI**

**Create:** `admin/analytics.html`

```html
<div class="analytics-dashboard">

  <h2>📊 Analytics Dashboard</h2>

  <div class="stats-grid">

    <div class="stat-card">
      <h3>Average Retention</h3>
      <div class="stat-value">67.5%</div>
      <div class="stat-trend">+3.2% vs last week</div>
    </div>

    <div class="stat-card">
      <h3>Template Success Rate</h3>
      <canvas id="template-success-chart"></canvas>
    </div>

    <div class="stat-card">
      <h3>User Adoption</h3>
      <div class="stat-value">143</div>
      <div class="stat-subtitle">Active Channels</div>
    </div>

    <div class="stat-card">
      <h3>Topics Generated</h3>
      <div class="stat-value">1,247</div>
      <div class="stat-subtitle">All time</div>
    </div>

  </div>

  <h3>Template Performance</h3>
  <table id="template-performance-table">
    <thead>
      <tr>
        <th>Template Name</th>
        <th>Videos Generated</th>
        <th>Avg Retention</th>
        <th>CTR</th>
        <th>Success Rate</th>
      </tr>
    </thead>
    <tbody>
      <!-- Populated from analytics Lambda -->
    </tbody>
  </table>

</div>
```

---

#### **Task 3.8: Lambda - analytics-aggregate**

**Path:** `aws/lambda/analytics-aggregate/`

**Functionality:**
- Scan GeneratedContent table
- Group by template_id
- Calculate metrics:
  - Average retention %
  - CTR
  - Videos generated count
  - Success rate
- Return aggregated data

---

## ✅ SPRINT 3 FINAL CHECKLIST

**Deployment:**
- [ ] Cognito User Pool configured
- [ ] Lambda Authorizer deployed
- [ ] Template Registry UI deployed
- [ ] Engine Inspector deployed
- [ ] Analytics Dashboard deployed
- [ ] All role-based permissions tested

**Git Commit:**
```bash
git commit -m "feat: Sprint 3 - Admin/Developer Mode + Analytics

- Implemented Cognito authentication
- Created Template Registry (Admin)
- Built Engine Inspector (Developer)
- Added Analytics Dashboard
- Role-based access control (User/Admin/Developer)

Story Engineering System v1.0 COMPLETE ✅"
```

---

## 🎯 FINAL SYSTEM ARCHITECTURE

```
┌─────────────────────────────────────────────────────┐
│                  USER MODE (Simple)                 │
│  - Channel Setup                                    │
│  - Topics Manager                                   │
│  - Story Settings (Basic)                           │
│  - Generate Button                                  │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│                 ADMIN MODE (Control)                │
│  + Template Registry                                │
│  + Retention Settings                               │
│  + Analytics Dashboard                              │
│  + Global Style Rules                               │
└─────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────┐
│              DEVELOPER MODE (Visibility)            │
│  + Engine Inspector                                 │
│  + MasterConfig JSON View                           │
│  + Prompt Injection Logs                            │
│  + Generation Step Trace                            │
└─────────────────────────────────────────────────────┘
```

---

## 📦 TOTAL DELIVERABLES

### **DynamoDB Tables:**
1. ContentTopicsQueue
2. ContentTemplates
3. ChannelConfigs (updated)
4. GeneratedContent (updated)

### **Lambda Functions (16 total):**
**Sprint 1:**
1. content-topics-add
2. content-topics-list
3. content-topics-get-next
4. content-topics-update-status
5. build-master-config

**Sprint 2:**
6. content-narrative (updated)
7. mega-prompt-builder (updated)

**Sprint 3:**
8. authorizer
9. content-templates-list
10. content-templates-create
11. content-templates-update
12. content-templates-delete
13. engine-inspect
14. analytics-aggregate

### **UI Pages:**
**User Mode:**
1. topics-manager.html
2. channels.html (updated)

**Admin Mode:**
3. admin/template-registry.html
4. admin/retention-settings.html
5. admin/analytics.html

**Developer Mode:**
6. developer/engine-inspector.html

### **JavaScript Modules:**
1. js/topics-manager.js
2. js/channels-unified.js (updated)
3. js/auth-manager.js
4. js/admin/templates.js
5. js/developer/inspector.js

---

## ⏱️ ESTIMATED TIMELINE

**Sprint 1:** 5-7 days
**Sprint 2:** 5-7 days
**Sprint 3:** 5-7 days

**Total:** 15-21 days (3 weeks)

---

**READY TO START SPRINT 1! 🚀**
