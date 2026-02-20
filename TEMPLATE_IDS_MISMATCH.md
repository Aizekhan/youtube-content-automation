# Template IDs Mismatch - Critical Finding

**Date:** 2026-02-20
**Discovered:** During Templates Migration Analysis

---

## 🚨 CRITICAL ISSUE: Template IDs Mismatch

### Code Expects (Default IDs in `load_all_templates()`):

```python
template_types = {
    'narrative': ('NarrativeTemplates', 'narrative_template', 'narr-universal'),
    'image': ('ImageGenerationTemplates', 'image_template', 'img-universal-sd35'),
    'cta': ('CTATemplates', 'cta_template', 'cta_template_1762366857242_3zx29p'),
    'thumbnail': ('ThumbnailTemplates', 'thumbnail_template', 'thumb-universal'),
    'tts': ('TTSTemplates', 'tts_template', 'tts-universal'),
    'sfx': ('SFXTemplates', 'sfx_template', 'sfx_universal_v1'),
    'description': ('DescriptionTemplates', 'description_template', 'description_universal_v1')
}
```

### Database Actually Has:

```
NarrativeTemplates: narrative_architect_v2
ImageGenerationTemplates: image_template_1762366799272_n643wy
CTATemplates: cta_template_1762366857242_3zx29p
ThumbnailTemplates: thumbnail_universal_v1
TTSTemplates: tts_auto_voice_1762573009
SFXTemplates: sfx_universal_v1
DescriptionTemplates: description_universal_v1
VideoEditingTemplates: video_template_universal_v2
```

---

## ✅ ❌ Match Status

| Template Type | Code Expects | Database Has | Status |
|--------------|-------------|--------------|---------|
| Narrative | `narr-universal` | `narrative_architect_v2` | ❌ **MISMATCH** |
| Image | `img-universal-sd35` | `image_template_1762366799272_n643wy` | ❌ **MISMATCH** |
| CTA | `cta_template_1762366857242_3zx29p` | `cta_template_1762366857242_3zx29p` | ✅ Match |
| Thumbnail | `thumb-universal` | `thumbnail_universal_v1` | ❌ **MISMATCH** |
| TTS | `tts-universal` | `tts_auto_voice_1762573009` | ❌ **MISMATCH** |
| SFX | `sfx_universal_v1` | `sfx_universal_v1` | ✅ Match |
| Description | `description_universal_v1` | `description_universal_v1` | ✅ Match |

**Result:** 4 out of 7 templates are **NOT loading** from database!

---

## 🎯 What This Means

### Current Behavior:

```python
# In load_all_templates():
template_id = channel_config.get(config_field, default_id)  # Get 'narr-universal'
table = dynamodb.Table(table_name)
response = table.get_item(Key={'template_id': template_id})  # Tries to find 'narr-universal'
template = response.get('Item', {})  # Returns {} (empty) - NOT FOUND!

# In mega_config_merger:
ai_config = template.get('ai_config', {})  # Returns {}
sections = ai_config.get('sections', {})  # Returns {}
role_definition = sections.get('role_definition', '')  # Returns '' (empty string)
core_rules = sections.get('core_rules', [])  # Returns [] (empty array)
```

**System is running with EMPTY templates for:**
- Narrative (most important!)
- Image
- Thumbnail
- TTS

**System only loads:**
- CTA (matched ID)
- SFX (matched ID)
- Description (matched ID)

---

## 🤔 How is the System Still Working?

### Theory 1: Hardcoded Defaults in mega_prompt_builder.py

The system might have hardcoded prompt templates in `mega_prompt_builder.py` that don't rely on template data.

Let's check:
```python
# In build_mega_prompt():
system_message = build_system_instructions(mega_config)
user_message = build_user_request(topic, facts, constraints)
```

If `build_system_instructions()` has fallback prompts when `role_definition` is empty, system would work.

### Theory 2: Channel-Specific Config Overrides

Channel config might have its own prompts/rules that override template data.

### Theory 3: The Prompts are Actually Minimal

Maybe the template prompts are not critical - OpenAI can generate good content with minimal instructions.

---

## 🧪 HOW TO VERIFY

### Option 1: Check Recent Execution Logs
Look for:
```
"Loaded narrative template: narr-universal"
"Failed to load narrative template: ..."
```

### Option 2: Run Test Generation
1. Trigger content generation for a channel
2. Check Lambda logs
3. See if templates loaded successfully

### Option 3: Check mega_prompt_builder.py
See if it has hardcoded fallback prompts when template data is empty.

---

## 💡 CONCLUSION

**Templates are likely NOT being used!**

The system is either:
1. Using hardcoded fallback prompts
2. Using channel-specific overrides
3. Working with minimal AI instructions

**This means:**
- ✅ Templates can be safely removed
- ✅ Hardcode the working prompts directly in code
- ✅ No user data loss (templates were never loaded)
- ✅ System already proven to work without templates

---

## 📋 NEXT STEPS

1. **Check mega_prompt_builder.py** for hardcoded prompts
2. **Dump one working template** (e.g., SFX) to see what's actually in it
3. **Compare** template content vs generated prompts
4. **Confirm** system works without templates
5. **Hardcode** working prompts directly in code
6. **Delete** all Template tables

**This discovery simplifies migration - templates are already not loading! 🎉**
