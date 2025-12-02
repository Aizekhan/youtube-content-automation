# Content Display Fix - Missing Narratives, CTA, Audio

**Date:** 2025-11-26
**Issue:** Narratives, CTA, and audio not showing in content.html
**Status:** ✅ FIXED

---

## Problem Description

User reported that in the content dashboard:
- ❌ Narratives under each scene are missing
- ❌ CTA is not visible
- ❌ Audio tracks not showing

---

## Root Cause

**The data IS in the database, but content.html was looking for wrong field names!**

### Investigation Results

1. **Checked DynamoDB GeneratedContent table:**
   - Latest mega_generation: 2025-11-26T01:00:42 (AFTER MEGA v3.0 deployment ✅)
   - Data structure found:
     ```json
     {
       "narrative_data": {
         "scenes": [
           {
             "scene_number": 1,
             "scene_title": "The Forgotten Entry",
             "scene_narration": "<speak>...</speak>",  // ✅ Field exists!
             "music_track": "battle-of-the-dragons-8037.mp3",
             "sfx_cues": ["ghost_bell.mp3"],
             "image_prompt": "..."
           }
         ]
       },
       "audio_files": [5 files],  // ✅ Exists!
       "cta_data": {
         "cta_segments": []  // Empty in this content
       }
     }
     ```

2. **Checked content.html code:**
   - **Line 924**: Looking for `scene.text_with_ssml` ❌ (field doesn't exist!)
   - **Actual field**: `scene.scene_narration` ✅
   - **Line 1162**: Looking for `item.sfx_data.scenes` ❌
   - **Actual location**: `item.narrative_data.scenes` ✅

---

## Solution

### Fix #1: Scene Narration Display (Line 924)

**Before:**
```javascript
<p class="ssml-text">${scene.text_with_ssml || ''}</p>
```

**After:**
```javascript
<p class="ssml-text">${scene.scene_narration || scene.text_with_ssml || ''}</p>
```

**Impact:** Now shows scene narratives with SSML markup

### Fix #2: Audio/SFX Display (Line 1162)

**Before:**
```javascript
function populateAudio(item) {
    // MEGA MODE: Use sfx_data
    if (!item.sfx_data || !item.sfx_data.scenes) {
        document.getElementById('audioContent').innerHTML = '<p class="text-muted">No background music or sound effects added yet</p>';
        return;
    }
    const sfxScenes = item.sfx_data.scenes || [];
```

**After:**
```javascript
function populateAudio(item) {
    // MEGA MODE: Use narrative_data.scenes for SFX info
    if (!item.narrative_data || !item.narrative_data.scenes) {
        document.getElementById('audioContent').innerHTML = '<p class="text-muted">No background music or sound effects added yet</p>';
        return;
    }
    const sfxScenes = item.narrative_data.scenes || [];
```

**Impact:** Now correctly reads music tracks and SFX cues from narrative_data.scenes

---

## Data Structure Clarification

### Where Data is Actually Stored (MEGA v3.0):

```
GeneratedContent Item
├── narrative_data                    // Main narrative content
│   ├── story_title
│   ├── character_count
│   ├── scene_count
│   ├── model
│   └── scenes[]                      // ⭐ SCENES WITH EVERYTHING!
│       ├── scene_number
│       ├── scene_title
│       ├── scene_narration           // ⭐ Narrative text with SSML
│       ├── image_prompt
│       ├── negative_prompt
│       ├── variation_used
│       ├── music_track               // ⭐ Background music
│       ├── sfx_cues[]                // ⭐ Sound effects
│       └── timing_estimates[]
│
├── audio_files[]                     // Generated Polly audio files
├── voice_id                          // e.g., "Matthew"
├── voice_profile                     // e.g., "deep_male"
├── tts_service                       // e.g., "aws_polly_neural"
│
├── cta_data                          // Call to action
│   └── cta_segments[]
│
├── description_data                  // Video description
│   ├── title
│   ├── description
│   ├── tags[]
│   └── hashtags[]
│
├── sfx_data                          // ⚠️ Currently empty in v3.0
│   └── (no fields)                   // Data is in narrative_data.scenes instead
│
├── image_data                        // Image generation info
│   └── scenes[]
│
├── scene_images[]                    // Generated image URLs
└── thumbnail_data                    // Thumbnail info
    ├── thumbnail_prompt
    ├── text_overlay
    └── style_notes
```

### Key Insight:
In MEGA v3.0, **SFX data (music_track, sfx_cues) is stored in `narrative_data.scenes`**, NOT in `sfx_data`.

This is because MEGA v3.0 generates everything in one OpenAI request, and the response includes SFX information per scene.

---

## CTA Status

**Current Status:** CTA segments are empty in the tested content.

**Possible Reasons:**
1. CTA template configuration might not be active
2. OpenAI may not have generated CTA content
3. CTA generation might be disabled in the channel config

**To Fix:**
1. Check CTATemplates table for the channel's CTA template
2. Verify `cta_template` is set in ChannelConfigs
3. Review MEGA prompt to ensure CTA generation is requested
4. Check if AI model actually generated CTA in full OpenAI response

---

## Files Modified

- **content.html** (2 fixes applied)
  - Line 924: `scene.text_with_ssml` → `scene.scene_narration`
  - Line 1162-1167: `item.sfx_data.scenes` → `item.narrative_data.scenes`

---

## Deployment Instructions

### Method 1: Manual Copy (Recommended)
```bash
# Copy fixed content.html to server
scp content.html ubuntu@3.75.97.188:/home/ubuntu/web-admin/html/content.html
```

### Method 2: Verify Locally First
```bash
# Open content.html in browser
# Navigate to a mega_generation content item
# Verify narratives, audio, and SFX display correctly
```

---

## Testing After Deployment

1. **Open content dashboard**
2. **Find a mega_generation content item** (type: "mega_generation")
3. **Check Story tab:**
   - ✅ Should see scene narratives with SSML tags
   - Example: `<speak><prosody rate="slow">I found myself...</prosody></speak>`
4. **Check Audio & SFX tab:**
   - ✅ Should see background music tracks
   - ✅ Should see SFX cues per scene
   - Example: "battle-of-the-dragons-8037.mp3" used in 5 scenes
5. **Check CTA tab:**
   - Depends on whether CTA was generated
   - If empty, investigate CTA template configuration

---

## Expected Display After Fix

### Story Tab:
```
Scenes (5):

Scene 1: The Forgotten Entry [dramatic]
<speak><prosody rate="slow">I found myself drawn to the abandoned house
on the edge of the village. Its windows, like hollow eyes, stared back
at me...</prosody></speak>

Scene 2: Whispers in the Attic [whisper]
<speak><prosody rate="slow"><break time="300ms"/>The stairs creaked
under my weight as I ascended to the attic...</prosody></speak>
```

### Audio & SFX Tab:
```
🎼 Background Music

Track: battle-of-the-dragons-8037.mp3
Used in 5 scene(s)

🔊 Sound Effects (2 total)

Scene 1
🔊 ghost_bell.mp3

Scene 2
🔊 Daytime Forrest Bonfire.mp3
```

---

## Related Issues

1. ✅ Narrative Lambda MEGA v3.0 deployed (2025-11-26 00:45:13)
2. ✅ Content.html field names fixed (2025-11-26 ~01:15)
3. 🔄 CTA generation needs investigation (separate issue)

---

**Status:** ✅ Fixed - Ready for testing
**Action Required:** Deploy content.html and refresh browser
**Impact:** High - Fixes core content display functionality

