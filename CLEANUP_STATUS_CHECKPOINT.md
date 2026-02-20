# Cleanup Status - Checkpoint

**Date:** 2026-02-20 21:00
**Context:** 126K tokens used
**Status:** Partial cleanup completed, needs continuation

---

## ✅ COMPLETED

### 1. DynamoDB Tables Deleted
- ✅ All 9 Template tables deleted (DELETING status)
  - NarrativeTemplates
  - ImageGenerationTemplates
  - CTATemplates
  - ThumbnailTemplates
  - TTSTemplates
  - SFXTemplates
  - DescriptionTemplates
  - StoryTemplates
  - VideoEditingTemplates

### 2. Code Updates Completed
- ✅ `aws/lambda/shared/mega_config_merger.py`
  - Removed entire variation_sets logic (~130 lines)
  - Simplified `extract_image_instructions()` to return minimal defaults
  - Lines 125-147 now clean

### 3. Partial Updates
- 🔄 `aws/lambda/content-narrative/lambda_function.py`
  - load_story_blueprint() - DELETED ✅
  - load_all_templates_REMOVED() - renamed but still exists (needs full removal)

---

## ⏳ TODO - Critical Lambda Updates

### aws/lambda/content-narrative/lambda_function.py

**DELETE completely:**
```python
# Lines 197-242: Function load_all_templates_REMOVED()
# Can be deleted entirely - dead code
```

**REPLACE (lines 360-386):**
```python
# OLD:
story_blueprint = load_story_blueprint(channel_config)
templates = load_all_templates(channel_config)
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

# NEW:
mega_config = merge_mega_configuration_simple(channel_config)
```

**NEW FUNCTION NEEDED:**
```python
def merge_mega_configuration_simple(channel_config):
    """
    Build mega_config WITHOUT templates
    Templates system removed - returns minimal config
    New Story Engine will provide full configuration
    """
    return {
        'channel_id': channel_config.get('channel_id'),
        'channel_name': channel_config.get('channel_name', 'Unnamed Channel'),
        'model': 'gpt-4o-mini',
        'temperature': 0.8,
        'max_tokens': int(channel_config.get('max_tokens', 16000)),

        'channel_context': {
            'channel_name': channel_config.get('channel_name', ''),
            'language': channel_config.get('language', 'en'),
            'genre': channel_config.get('genre', 'General'),
            'factual_mode': channel_config.get('factual_mode', 'fictional'),
        },

        # Empty instructions (Templates removed)
        'narrative_instructions': {'role_definition': '', 'core_rules': []},
        'image_instructions': {
            'role_definition': '',
            'core_rules': [],
            'visual_keywords': '',
            'visual_atmosphere': '',
            'image_style_variants': '',
            'color_palettes': '',
            'lighting_variants': '',
            'composition_variants': '',
            'visual_reference_type': '',
            'negative_prompt': 'blurry, low quality, distorted'
        },
        'cta_instructions': {'role_definition': '', 'core_rules': []},
        'thumbnail_instructions': {'role_definition': '', 'core_rules': []},
        'tts_instructions': {'role_definition': '', 'core_rules': [], 'scene_variations': []},
        'sfx_instructions': {'role_definition': '', 'core_rules': [], 'sfx_library': [], 'music_library': []},
        'description_instructions': {'role_definition': '', 'core_rules': [], 'seo_keywords': ''},

        'story_blueprint': None,  # Removed

        'constraints': {
            'target_character_count': int(channel_config.get('target_character_count', 8000)),
            'scene_count_target': int(channel_config.get('scene_count_target', 18)),
            'video_duration_target': int(channel_config.get('video_duration_target', 10))
        }
    }
```

---

### aws/lambda/shared/mega_config_merger.py

**OPTION A: Keep merge_mega_configuration() but simplify**
```python
def merge_mega_configuration(channel_config, *args, **kwargs):
    """
    SIMPLIFIED: Templates system removed
    Accepts old parameters for backward compatibility but ignores them
    """
    return merge_mega_configuration_simple(channel_config)
```

**OPTION B: Delete old function, use only new one**
- Rename `merge_mega_configuration_simple()` → `merge_mega_configuration()`
- Update content-narrative to call new signature

---

### Other Lambdas to Update

#### aws/lambda/content-generate-images/lambda_function.py
- Line 502: Check for ThumbnailTemplates usage → Remove if exists

#### aws/lambda/content-video-assembly/lambda_function.py
- Line 20: `template_table = dynamodb.Table('VideoEditingTemplates')` → Remove
- Lines 246-251: `get_template()` function → Remove or stub

---

## 🎨 UI Cleanup TODO

### Find and Remove:
1. **Variation Sets UI**
   - File: `js/channels-unified.js` or similar
   - Search for: `variation_sets`, `rotation_mode`, `manual_set_index`
   - Remove entire Variation Sets section

2. **Prompts UI Tab**
   - File: `prompts-editor.html` (likely)
   - Remove file completely
   - Remove navigation link to Prompts tab

---

## 🧪 TESTING NEEDED

After code updates:
1. Deploy updated Lambdas
2. Test content generation for one channel
3. Verify:
   - No DynamoDB errors (tables deleted)
   - Content generates successfully
   - Output quality acceptable
4. If successful → proceed with UI cleanup

---

## 📝 COMMIT PLAN

**Commit Message:**
```
cleanup: remove Templates system and Variation Sets

Phase 1 - Complete Template System Removal:

DynamoDB:
- Deleted 9 Template tables (Narrative, Image, CTA, Thumbnail, TTS, SFX, Description, Story, VideoEditing)

Lambda Updates:
- mega_config_merger.py: removed variation_sets logic (~130 lines)
- content-narrative: removed load_story_blueprint() and load_all_templates()
- Simplified mega_config to minimal defaults
- Templates system fully removed from backend

Reason: Preparing for new Story Engine with comprehensive dropdowns
Old system: static templates + variation sets rotation
New system: dynamic prompts from user dropdown selections

Backups: All template content saved to backups/20260220_cleanup/

Next: Remove Variation Sets + Prompts UI, implement new Story Engine

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

## 🚀 NEXT SESSION ACTIONS

1. **Continue Lambda Updates** (1 hour)
   - Implement merge_mega_configuration_simple()
   - Update content-narrative to use it
   - Update other Lambdas (images, video-assembly)

2. **UI Cleanup** (30 min)
   - Find and remove Variation Sets UI
   - Find and remove Prompts UI tab

3. **Testing** (15 min)
   - Deploy all changes
   - Test content generation
   - Verify no errors

4. **Commit & Push** (15 min)
   - Git add all changes
   - Commit with detailed message
   - Push to GitHub

**Total:** ~2 hours to complete cleanup

---

**CHECKPOINT SAVED! Ready to continue! 🎯**
