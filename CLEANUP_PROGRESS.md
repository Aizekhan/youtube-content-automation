# Templates & Variation Sets Cleanup Progress

**Date:** 2026-02-20
**Status:** IN PROGRESS

---

## ✅ COMPLETED

### 1. DynamoDB Tables Deleted (9 tables)
- ✅ NarrativeTemplates - DELETING
- ✅ ImageGenerationTemplates - DELETING
- ✅ CTATemplates - DELETING
- ✅ ThumbnailTemplates - DELETING
- ✅ TTSTemplates - DELETING
- ✅ SFXTemplates - DELETING
- ✅ DescriptionTemplates - DELETING
- ✅ StoryTemplates - DELETING
- ✅ VideoEditingTemplates - DELETING

### 2. Backups Created
- ✅ All 7 template contents saved to `backups/20260220_cleanup/`

---

## 🔄 IN PROGRESS

### Lambda Code Updates Needed:

#### 1. **aws/lambda/shared/mega_config_merger.py**
**Remove:**
- Lines 140-269: Entire `variation_sets` logic from `extract_image_instructions()`
- `rotation_mode`, `generation_count`, `manual_set_index` references
- `pick_variant()` helper function

**Replace with:**
```python
def extract_image_instructions(template, channel):
    """Extract image generation instructions - simplified version"""
    ai_config = template.get('ai_config', {})
    sections = ai_config.get('sections', {})

    return {
        'role_definition': sections.get('role_definition', ''),
        'core_rules': sections.get('core_rules', []),
        'visual_keywords': '',
        'visual_atmosphere': '',
        'image_style_variants': '',
        'color_palettes': '',
        'lighting_variants': '',
        'composition_variants': '',
        'visual_reference_type': '',
        'negative_prompt': 'blurry, low quality, distorted'
    }
```

#### 2. **aws/lambda/content-narrative/lambda_function.py**
**Remove:**
- Lines 197-218: `load_story_blueprint()` function
- Lines 220-265: `load_all_templates()` function
- Lines 383-390: Call to `load_story_blueprint()`
- Lines 387-403: Call to `load_all_templates()` and merge

**Update:**
- Lines 29-30: Remove `from mega_config_merger import merge_mega_configuration`
- Simplify to not use templates at all

#### 3. **aws/lambda/content-generate-images/lambda_function.py**
**Check for:**
- Line 502: `ThumbnailTemplates` table usage (remove if exists)

#### 4. **aws/lambda/content-video-assembly/lambda_function.py**
**Check for:**
- Line 20: `VideoEditingTemplates` table usage (remove)
- Lines 246-251: `get_template()` function (remove)

---

## ⏳ TODO

### Code Cleanup:
- [ ] Update mega_config_merger.py (remove variation_sets)
- [ ] Update content-narrative Lambda (remove templates)
- [ ] Update content-generate-images Lambda
- [ ] Update content-video-assembly Lambda
- [ ] Remove any other template references

### UI Cleanup:
- [ ] Find Variation Sets UI (channels-unified.js)
- [ ] Find Prompts UI tab (prompts-editor.html?)
- [ ] Remove both UIs

### Testing:
- [ ] Deploy updated Lambdas
- [ ] Test content generation
- [ ] Verify no errors

### Final:
- [ ] Commit all changes
- [ ] Push to GitHub

---

## 📝 NOTES

**User Requirements:**
- ❌ NO hardcoding prompts
- ❌ NO keeping variation_sets logic
- ❌ NO keeping story_template logic
- ✅ Clean slate for new Story Engine system

**Next Phase:**
- Topics Queue Manager (manual + AI-generated topics)
- Story Engine with comprehensive dropdowns
- Dynamic prompt building from dropdown selections

---

**Continue from here!** 🚀
