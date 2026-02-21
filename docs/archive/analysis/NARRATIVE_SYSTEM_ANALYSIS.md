# 🔍 Narrative Generation System - Complete Analysis & Cleanup Plan

**Date:** 2026-02-20
**Purpose:** Analyze current narrative generation system before implementing new Story Engine
**Related:** THEME_SYSTEM_ANALYSIS.md, STORY_ENGINE_REDESIGN.md

---

## 📊 CURRENT SYSTEM - FULL ANALYSIS

### **1. Lambda Functions**

#### **1.1 content-narrative (MEGA-GENERATION v3.0)**
📁 **Path:** `aws/lambda/content-narrative/lambda_function.py`

**Purpose:** Generate ALL 7 content components in ONE OpenAI request

**What it generates:**
1. ✅ Narrative with SSML (story text)
2. ✅ Image Prompts for each scene
3. ✅ SFX + Music selection
4. ✅ CTA segments (calls-to-action)
5. ✅ Thumbnail design
6. ✅ Video Description (title, description, tags, hashtags)
7. ✅ Metadata

**Key Features:**
- **MEGA-GENERATION Mode**: Single OpenAI call for all 7 components
- **Manual Narrative Bypass** (lines 333-381): Allows pre-written stories from `channel_config.manual_narrative`
- **Story Blueprint Support**: Loads optional Story Template for pacing/structure guidance
- **Multi-Tenant Security**: IDOR prevention (user_id verification)
- **Request Size Validation**: Prevents memory exhaustion attacks (max 10MB, max 100 scenes)
- **Response Caching**: 24-hour cache for identical prompts (saves API costs)
- **Cost Tracking**: Logs all OpenAI costs to CostTracking table with user_id

**Templates Used (7 types):**
```javascript
{
  narrative_template: 'NarrativeTemplates',        // Story structure & writing style
  image_template: 'ImageGenerationTemplates',      // Image prompt generation rules
  cta_template: 'CTATemplates',                    // Call-to-action placement & style
  thumbnail_template: 'ThumbnailTemplates',        // Thumbnail design rules
  tts_template: 'TTSTemplates',                    // Text-to-speech formatting (SSML)
  sfx_template: 'SFXTemplates',                    // Sound effects & music selection
  description_template: 'DescriptionTemplates'     // YouTube metadata generation
}
```

**Story Blueprint (Optional):**
- Table: `StoryTemplates`
- Field: `channel_config.story_template` (template_id)
- Provides: pacing_profile, opening_strategy, scene_blueprints

**Configuration Flow:**
```
ChannelConfig → load_all_templates() → merge_mega_configuration() → build_mega_prompt() → OpenAI
```

**Shared Modules:**
- `mega_config_merger.py` - Merges all 7 templates + channel config
- `mega_prompt_builder.py` - Builds comprehensive system + user prompts
- `openai_cache.py` - Response caching (TTL: 168 hours = 7 days)

**Saves to DynamoDB:**
- Table: `GeneratedContent`
- Type: `'mega_generation'`
- Fields: `narrative_text`, `scenes`, `full_response`, `model`, `cost_usd`, `tokens_used`

**Output for Step Functions:**
```javascript
{
  channel_id, content_id, selected_topic, story_title,
  narrative_content: { scenes, cta_segments, thumbnail, description, sfx_data },
  image_data: { scenes: [{ image_prompt }] },
  thumbnail_data: { thumbnail_prompt, text_overlay, style_notes },
  cta_data: { cta_segments },
  description_data: { title, description, tags, hashtags },
  sfx_data: { sfx_cues, music_track, timing_estimates },
  image_provider: 'ec2-sd35' | 'replicate',
  voice_config: { language, speaker },
  model, genre, character_count, scene_count, timestamp
}
```

**Conclusion:** ✅ **KEEP** - This is the CORE of the system, no need to delete or modify

---

#### **1.2 prompts-api**
📁 **Path:** `aws/lambda/prompts-api/lambda_function.py`

**Purpose:** API Gateway Lambda for managing `AIPromptConfigs` table (OLD SYSTEM)

**Methods:**
- GET /prompts - List all agents
- GET /prompts/:agent_id - Get agent config
- POST /prompts - Create new agent
- PUT /prompts/:agent_id - Update agent
- DELETE /prompts/:agent_id - Delete agent

**Table:** `AIPromptConfigs`

**Current Records:**
1. `narrative_architect` (v1.0, gpt-4o) - OLD narrative generation
2. `theme_agent` (v1.0, gpt-4o) - OLD theme generation (we deleted content-theme-agent)

**Problem:** This table is NOT used by the current MEGA-GENERATION system. The current system uses:
- `NarrativeTemplates` (not AIPromptConfigs)
- `ImageGenerationTemplates`, `CTATemplates`, etc.

**Conclusion:** ⚠️ **DELETE** - Old system, replaced by new template architecture

---

### **2. DynamoDB Tables**

#### **2.1 Template Tables (NEW SYSTEM - MEGA-GENERATION v3.0)**

All these tables follow the same schema and are **actively used** by content-narrative Lambda:

##### **NarrativeTemplates**
- **Records:** 1 (`narr-universal`)
- **Purpose:** Story structure, writing style, scene composition rules
- **Used by:** `mega_config_merger.py` → `merge_mega_configuration()`
- **Conclusion:** ✅ **KEEP**

##### **ImageGenerationTemplates**
- **Records:** 1 (`img-universal-sd35`)
- **Purpose:** Image prompt generation rules, artistic style, composition
- **Used by:** `mega_config_merger.py` → `merge_mega_configuration()`
- **Conclusion:** ✅ **KEEP**

##### **CTATemplates**
- **Records:** 1 (`cta_template_1762366857242_3zx29p`)
- **Purpose:** Call-to-action placement, timing, messaging style
- **Used by:** `mega_config_merger.py` → `merge_mega_configuration()`
- **Conclusion:** ✅ **KEEP**

##### **ThumbnailTemplates**
- **Records:** 1 (`thumb-universal`)
- **Purpose:** Thumbnail design rules, text overlay, style
- **Used by:** `mega_config_merger.py` → `merge_mega_configuration()`
- **Conclusion:** ✅ **KEEP**

##### **TTSTemplates**
- **Records:** 1 (`tts-universal`)
- **Purpose:** Text-to-speech SSML formatting, pacing, emphasis
- **Used by:** `mega_config_merger.py` → `merge_mega_configuration()`
- **Conclusion:** ✅ **KEEP**

##### **SFXTemplates**
- **Records:** 1 (`sfx_universal_v1`)
- **Purpose:** Sound effects selection, music track selection, timing
- **Used by:** `mega_config_merger.py` → `merge_mega_configuration()`
- **Conclusion:** ✅ **KEEP**

##### **DescriptionTemplates**
- **Records:** 1 (`description_universal_v1`)
- **Purpose:** YouTube metadata generation (title, description, tags, hashtags)
- **Used by:** `mega_config_merger.py` → `merge_mega_configuration()`
- **Conclusion:** ✅ **KEEP**

---

##### **StoryTemplates**
- **Records:** 5 (Story Blueprints)
- **Purpose:** Advanced story structure templates (pacing, opening strategy, scene blueprints)
- **Used by:** `load_story_blueprint()` in content-narrative Lambda
- **Optional:** Channel can set `channel_config.story_template` to use a blueprint
- **Conclusion:** ✅ **KEEP** - Used for advanced story control

---

##### **VideoEditingTemplates**
- **Records:** 1
- **Purpose:** Video editing configuration for content-video-assembly Lambda
- **Used by:** `content-video-assembly` Lambda (Phase 3 - video assembly)
- **Fields:** Transition effects, timing, rendering settings
- **Conclusion:** ✅ **KEEP** - Actively used by video assembly pipeline

---

#### **2.2 Old System Tables (LEGACY - Pre-MEGA-GENERATION)**

##### **AIPromptConfigs**
- **Records:** 2 (`narrative_architect`, `theme_agent`)
- **Purpose:** OLD prompt configuration system (pre-v3.0)
- **Used by:** `prompts-api` Lambda (management API)
- **Problem:** NOT used by current content-narrative Lambda
- **Current system uses:** 7 separate template tables (NarrativeTemplates, ImageGenerationTemplates, etc.)
- **Conclusion:** ❌ **DELETE** - Replaced by new template architecture

##### **PromptTemplatesV2**
- **Records:** 2
  - `narrative_template_1762366787395_ki1h6w` - Universal Narrative Structure
  - `theme_template_1762366773464_dmt531` - Universal Theme Generator
- **Purpose:** OLD unified template system (before splitting into 7 tables)
- **Used by:** `prompts-api` Lambda (legacy)
- **Conclusion:** ❌ **DELETE** - Replaced by 7 specialized template tables

##### **PromptVersionHistory**
- **Records:** 8
- **Purpose:** Version history for old AIPromptConfigs / PromptTemplatesV2
- **Used by:** Auditing/rollback for old system
- **Conclusion:** ❌ **DELETE** - No longer needed (old system being deleted)

---

### **3. Shared Modules**

📁 **Path:** `aws/lambda/shared/`

#### **✅ KEEP - Current System (MEGA-GENERATION v3.0)**

1. **mega_config_merger.py** - Merges all 7 templates + channel config
2. **mega_prompt_builder.py** - Builds comprehensive OpenAI prompts
3. **openai_cache.py** - Response caching (saves API costs)
4. **response_extractor.py** - Parses AI JSON responses
5. **ssml_validator.py** - Validates TTS SSML formatting
6. **pipeline_helpers.py** - General utilities

#### **❌ DELETE - Old System**

1. **config_merger.py** - OLD merge logic for AIPromptConfigs
   - Used by old theme-agent / narrative-architect
   - Replaced by `mega_config_merger.py`
   - **Action:** Delete this file

---

### **4. Step Functions Flow (Phase 1)**

**Current Flow:**
```
GetActiveChannels
  ↓
Phase1ContentGeneration (Map - for each channel)
  ↓
  CheckFactualMode  ← NEW StartAt (after theme cleanup)
    ↓
  SearchWikipediaFacts / SetNoFacts
    ↓
  MegaNarrativeGenerator (content-narrative Lambda)
    ↓ [Returns: scenes + image_data + thumbnail + CTA + description + SFX]
    ↓
Phase2Parallel (Image Generation + Audio Generation)
```

**MegaNarrativeGenerator state:**
- Lambda: `content-narrative`
- Input: `channel_id`, `selected_topic`, `wikipedia_facts`, `has_real_facts`, `user_id`
- Output: Full content package (narrative + 6 other components)

**Note:** No changes needed to Step Functions for narrative cleanup (it's working correctly)

---

## 🧹 CLEANUP PLAN

### **WHAT TO DELETE:**

#### ❌ **1. AIPromptConfigs Table**
- **Records:** 2 (`narrative_architect`, `theme_agent`)
- **Reason:** Replaced by 7 specialized template tables
- **Used by:** `prompts-api` Lambda (which we'll also delete)
- **Action:**
  1. Backup table to `backups/20260220_cleanup/AIPromptConfigs_backup.json`
  2. Delete table via AWS Console or CLI

#### ❌ **2. PromptTemplatesV2 Table**
- **Records:** 2 (narrative + theme templates)
- **Reason:** Replaced by NarrativeTemplates + ThemeTemplates (already deleted)
- **Action:**
  1. Backup table to `backups/20260220_cleanup/PromptTemplatesV2_backup.json`
  2. Delete table

#### ❌ **3. PromptVersionHistory Table**
- **Records:** 8 (history of old prompts)
- **Reason:** No longer needed (old system deleted)
- **Action:**
  1. Backup table to `backups/20260220_cleanup/PromptVersionHistory_backup.json`
  2. Delete table

#### ❌ **4. prompts-api Lambda**
- **Path:** `aws/lambda/prompts-api/`
- **Reason:** Manages deleted tables (AIPromptConfigs, PromptTemplatesV2)
- **Action:**
  1. Delete folder `aws/lambda/prompts-api/`
  2. Delete Lambda function in AWS Console

#### ❌ **5. config_merger.py (old shared module)**
- **Path:** `aws/lambda/shared/config_merger.py`
- **Reason:** Used by old AIPromptConfigs system, replaced by mega_config_merger.py
- **Action:**
  1. Check if any other Lambda still uses it (unlikely)
  2. Delete file

---

### **WHAT TO KEEP:**

#### ✅ **Lambda Functions**
1. **content-narrative** - CORE narrative generator (MEGA v3.0)

#### ✅ **DynamoDB Tables (8 Template Tables + Story Blueprints)**
1. **NarrativeTemplates** - Story structure & writing
2. **ImageGenerationTemplates** - Image prompts
3. **CTATemplates** - Calls-to-action
4. **ThumbnailTemplates** - Thumbnail design
5. **TTSTemplates** - Text-to-speech SSML
6. **SFXTemplates** - Sound effects & music
7. **DescriptionTemplates** - YouTube metadata
8. **VideoEditingTemplates** - Video assembly configuration
9. **StoryTemplates** - Story Blueprints (5 records)

#### ✅ **Shared Modules**
1. `mega_config_merger.py` - Template merging
2. `mega_prompt_builder.py` - Prompt building
3. `openai_cache.py` - Response caching
4. `response_extractor.py` - JSON parsing
5. `ssml_validator.py` - SSML validation
6. `pipeline_helpers.py` - Utilities

#### ✅ **Other Critical Tables**
1. **ChannelConfigs** - Channel settings
2. **GeneratedContent** - Content history (already cleaned - 0 records)
3. **CostTracking** - Cost monitoring

---

## 🔄 MIGRATION NOTES

### **No Migration Needed**

Unlike the theme system (which we're replacing with Topics Queue), the narrative generation system is **already in its final form** (MEGA-GENERATION v3.0).

**Why no changes needed:**
- ✅ Supports Fiction/Real/Hybrid modes (via `factual_mode` + `wikipedia_facts`)
- ✅ Supports Story Blueprints (via `StoryTemplates`)
- ✅ Supports Manual Narratives (via `channel_config.manual_narrative`)
- ✅ Multi-stage generation (7 components in 1 call)
- ✅ Template-based customization (7 specialized templates)
- ✅ Cost tracking & caching

**What we'll ADD in Story Engine redesign:**
- 📝 Comprehensive dropdowns in UI (World Type, Tone, Plot Structure, etc.)
- 📝 Character Consistency Engine
- 📝 Visual Consistency Engine (reference images)
- 📝 Advanced Story Blueprint editor

But the **backend Lambda (content-narrative) stays as-is** - it already supports everything we need!

---

## 📝 CLEANUP CHECKLIST

### **Phase 1: Backup (15 min)**
- [ ] Backup AIPromptConfigs table
- [ ] Backup PromptTemplatesV2 table
- [ ] Backup PromptVersionHistory table
- [ ] Verify backups saved to `backups/20260220_cleanup/`

### **Phase 2: Delete DynamoDB Tables (10 min)**
- [ ] Delete AIPromptConfigs table
- [ ] Delete PromptTemplatesV2 table
- [ ] Delete PromptVersionHistory table

### **Phase 3: Delete Lambda Functions (5 min)**
- [ ] Delete `aws/lambda/prompts-api/` folder
- [ ] Delete prompts-api Lambda in AWS Console

### **Phase 4: Delete Shared Module (2 min)**
- [ ] Check if config_merger.py is used anywhere
- [ ] Delete `aws/lambda/shared/config_merger.py`

### **Phase 5: Commit Changes (5 min)**
- [ ] Git add all deletions
- [ ] Create commit: "cleanup: remove old prompt system (AIPromptConfigs, PromptTemplatesV2, prompts-api)"
- [ ] Push to GitHub

**Total Time:** ~37 minutes

---

## 💡 RECOMMENDATIONS

### **1. Keep All 7 Template Tables**
These are the CORE of the MEGA-GENERATION system. Don't delete any of them.

### **2. Keep StoryTemplates**
Story Blueprints are used for advanced narrative control (pacing, structure). Will be useful for Story Engine.

### **3. Delete Old Prompt System**
AIPromptConfigs, PromptTemplatesV2, PromptVersionHistory are all legacy. Safe to delete.

### **4. Keep content-narrative Lambda Unchanged**
This Lambda is the heart of the system. It already supports:
- Fiction/Real/Hybrid modes
- Story Blueprints
- Manual narratives
- Multi-component generation

No need to modify it for Story Engine redesign - just enhance the UI to use its existing features!

### **5. Add UI Enhancements (Next Phase)**
After cleanup, add to `channels-unified.js`:
- Comprehensive dropdowns (World Type, Tone, Plot Structure, etc.)
- Story Blueprint selector
- Manual narrative editor
- Character/Visual consistency settings

---

## ⚠️ IMPORTANT

**Before Cleanup:**
1. ✅ Backup created: commit `3ea9920` (theme cleanup)
2. ⏳ Backup DynamoDB old prompt tables: TODO
3. ⏳ Verify no other Lambdas use old system: TODO

**After Cleanup:**
- Old prompt tables cannot be restored (only from backup)
- prompts-api Lambda cannot be restored (only from git)
- content-narrative Lambda **unchanged** (no risk)

---

**READY FOR NARRATIVE CLEANUP! 🧹**

But unlike theme cleanup, this is much simpler - we're just removing legacy infrastructure that's no longer used. The actual narrative generation system (MEGA v3.0) stays intact!
