# Templates Migration Analysis - Move to Hardcoded Logic

**Date:** 2026-02-20
**Purpose:** Analyze all Template tables, identify usage, and plan migration to hardcoded Lambda logic
**Goal:** Remove Templates tables + Prompts UI tab completely

---

## 📊 CURRENT TEMPLATE TABLES

### 1. **NarrativeTemplates** (1 record)
- **ID:** `narrative_architect_v2`
- **Used by:** `content-narrative` Lambda via `load_all_templates()`
- **Default in code:** `narr-universal` ⚠️ **MISMATCH!**
- **Contains:**
  - `ai_config.model`: `gpt-4o-mini`
  - `ai_config.temperature`: `0.8`
  - `ai_config.sections.role_definition`: AI role prompt
  - `ai_config.sections.core_rules`: Array of rules

### 2. **ImageGenerationTemplates** (1 record)
- **ID:** `image_template_1762366799272_n643wy`
- **Used by:** `content-narrative` Lambda via `load_all_templates()`
- **Default in code:** `img-universal-sd35` ⚠️ **MISMATCH!**
- **Contains:**
  - Image prompt generation rules
  - Visual style instructions
  - Composition guidelines

### 3. **CTATemplates** (1 record)
- **ID:** Unknown (need to check)
- **Used by:** `content-narrative` Lambda via `load_all_templates()`
- **Default in code:** `cta_template_1762366857242_3zx29p`
- **Contains:**
  - Call-to-action placement rules
  - CTA timing guidelines

### 4. **ThumbnailTemplates** (1 record)
- **ID:** Unknown
- **Used by:**
  - `content-narrative` Lambda via `load_all_templates()`
  - `content-generate-images` Lambda (line 502) - for thumbnail generation
- **Default in code:** `thumb-universal`
- **Contains:**
  - Thumbnail design rules
  - Text overlay guidelines

### 5. **TTSTemplates** (1 record)
- **ID:** Unknown
- **Used by:** `content-narrative` Lambda via `load_all_templates()`
- **Default in code:** `tts-universal`
- **Contains:**
  - SSML formatting rules
  - Pacing instructions

### 6. **SFXTemplates** (1 record)
- **ID:** Unknown
- **Used by:**
  - `content-narrative` Lambda via `load_all_templates()`
  - `update-sfx-library` Lambda (lines 138, 203) - for SFX library management
- **Default in code:** `sfx_universal_v1`
- **Contains:**
  - Sound effects selection rules
  - Music track guidelines

### 7. **DescriptionTemplates** (1 record)
- **ID:** Unknown
- **Used by:** `content-narrative` Lambda via `load_all_templates()`
- **Default in code:** `description_universal_v1`
- **Contains:**
  - YouTube metadata generation rules
  - Tags/hashtags guidelines

### 8. **StoryTemplates** (5 records)
- **IDs:**
  - `slow_burn_mystery` - Slow Burn Mystery
  - `emotional_journey` - Emotional Journey
  - `fast_escalation` - Fast Escalation
  - `shocking_revelation` - Shocking Revelation
  - `epic_legend` - Epic Legend
- **Used by:** `content-narrative` Lambda via `load_story_blueprint()`
- **Optional:** Only if `channel_config.story_template` is set
- **Contains:**
  - `pacing_profile`: Story pacing strategy
  - `opening_strategy`: How to start the story
  - `scene_blueprints`: Scene structure templates

### 9. **VideoEditingTemplates** (1 record)
- **ID:** Unknown
- **Used by:** `content-video-assembly` Lambda (line 20)
- **Contains:**
  - Video editing configuration
  - Transition effects
  - Rendering settings

---

## 🔍 USAGE ANALYSIS

### How Templates are Used:

#### **content-narrative Lambda:**
```python
# Load all 7 templates from DynamoDB
templates = load_all_templates(channel_config)

# Merge into mega_config
mega_config = merge_mega_configuration(
    channel_config,
    templates['narrative_template'],
    templates['image_template'],
    templates['cta_template'],
    templates['thumbnail_template'],
    templates['tts_template'],
    templates['sfx_template'],
    templates['description_template'],
    story_blueprint=story_blueprint
)

# Build prompt from mega_config
system_message, user_message = build_mega_prompt(mega_config, selected_topic, wikipedia_facts)

# Call OpenAI
response = openai.chat.completions.create(...)
```

#### **What is extracted from templates:**
```python
# From each template's ai_config.sections:
{
  'role_definition': "You are a narrative architect...",
  'core_rules': [
    "Rule 1: Scene structure...",
    "Rule 2: Character development...",
    ...
  ]
}
```

**THIS IS JUST AI PROMPTS! Not user data, not configuration - just static prompts!**

---

## ⚠️ KEY ISSUES

### 1. **Template ID Mismatch**
**Code expects:**
- `narr-universal`
- `img-universal-sd35`
- `thumb-universal`
- etc.

**Database has:**
- `narrative_architect_v2`
- `image_template_1762366799272_n643wy`
- Unknown IDs for others

**How it works now:**
- `load_all_templates()` tries to load by default ID
- If not found, template is `{}` (empty)
- `mega_config_merger` provides default values as fallback

**This means:** Templates might not even be loaded correctly right now!

### 2. **Templates are Static Prompts**
- No user-specific data
- No per-channel customization
- Just AI instructions (role definitions, rules)
- **Can be hardcoded directly in Lambda code!**

### 3. **No UI for Editing**
- Prompts tab exists but might not work correctly
- Users don't edit these templates
- Single default template per type

---

## 🎯 MIGRATION PLAN

### Phase 1: Verify Current State (URGENT)
1. Check if templates are actually loading correctly
2. If mismatched IDs → templates are empty → system uses fallback defaults
3. If using fallbacks → **templates are already ignored!**

### Phase 2: Hardcode Template Logic
1. Extract all `role_definition` and `core_rules` from each template type
2. Hardcode them directly in `mega_config_merger.py`
3. Remove `load_all_templates()` calls
4. Remove DynamoDB table reads

### Phase 3: Handle Special Cases
1. **StoryTemplates** (5 blueprints):
   - Keep if users actually use them (check `channel_config.story_template` usage)
   - If unused → hardcode default blueprint or remove entirely

2. **VideoEditingTemplates**:
   - Used by `content-video-assembly`
   - Check if actively used or if defaults are sufficient

3. **SFXTemplates**:
   - Used by `update-sfx-library` for library management
   - Might need to keep or migrate differently

### Phase 4: Remove Template Infrastructure
1. Delete `load_all_templates()` function
2. Delete template table reads from all Lambdas
3. Delete all 9 Template tables from DynamoDB
4. Delete Prompts UI tab
5. Update all Lambda functions

---

## 📋 INVESTIGATION CHECKLIST

### Step 1: Check if Templates are Actually Loading
- [ ] Check actual template IDs in each DynamoDB table
- [ ] Compare with default IDs in code
- [ ] Test if `load_all_templates()` successfully loads or fails
- [ ] Check Lambda logs for template loading errors

### Step 2: Check Template Usage in Channels
- [ ] Query `ChannelConfigs` for `story_template` field usage
- [ ] Check if any channels use non-default templates
- [ ] Verify if users can even change templates in UI

### Step 3: Dump Template Content
- [ ] Export all template `ai_config` content
- [ ] Identify what prompts/rules are actually used
- [ ] Verify if they match hardcoded fallbacks

### Step 4: Test Without Templates
- [ ] Temporarily modify Lambda to skip template loading
- [ ] Use only hardcoded defaults
- [ ] Run test generation
- [ ] Verify output quality is identical

---

## 🚀 EXPECTED OUTCOME

**After Migration:**
- ✅ No Template tables in DynamoDB
- ✅ No Prompts UI tab
- ✅ All AI prompts hardcoded in Lambda code
- ✅ Cleaner, faster system (no DynamoDB reads)
- ✅ No mismatch between code and database
- ✅ Easier to update prompts (just edit Lambda code)

**Code Changes:**
```python
# BEFORE (current):
templates = load_all_templates(channel_config)  # 7 DynamoDB reads
mega_config = merge_mega_configuration(channel_config, templates['narrative_template'], ...)

# AFTER (proposed):
mega_config = build_mega_config_hardcoded(channel_config)  # No DynamoDB reads
```

---

## ⏭️ NEXT STEPS

1. **Investigate current template loading** (check IDs, verify if working)
2. **Dump template content** to see actual prompts
3. **Create hardcoded version** of `mega_config_merger.py`
4. **Test side-by-side** (templates vs hardcoded)
5. **Deploy hardcoded version**
6. **Delete template tables**
7. **Remove Prompts UI**

**Estimated Time:** ~3-4 hours

---

**Ready to investigate! 🔍**
