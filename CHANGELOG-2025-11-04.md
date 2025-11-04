# Changelog - 2025-11-04

## AWS Polly Voice Filtering Fix

### Problem
When selecting "AWS Polly Standard" TTS service, ALL voices (both Neural and Standard) were showing in the dropdown, instead of filtering to show only Standard-compatible voices.

### Root Cause
The voice arrays included voices that AWS Polly Standard doesn't support. Specifically:
- **Neural-only voices:** Stephen, Ruth, Danielle (US English), Ivy (child voice)
- **Missing voices in Standard:** Kevin (initially thought to be Standard, but only works in Neural)

### Solution Implemented

#### 1. Fixed Voice Arrays (`js/channels-unified.js`)

**AWS Polly Neural (14 voices):**
- US English Males (4): Matthew, Joey, Stephen, Kevin
- US English Females (7): Joanna, Kendra, Kimberly, Salli, Ruth, Danielle, Ivy
- British English Males (1): Brian
- British English Females (2): Emma, Amy

**AWS Polly Standard (13 voices):**
- US English Males (3): Matthew, Joey, Justin
- US English Females (5): Joanna, Kendra, Kimberly, Salli, Ivy
- British English Males (1): Brian
- British English Females (2): Emma, Amy
- Australian English Males (1): Russell
- Australian English Females (1): Nicole

#### 2. Added Language Support Preparation

**Added to voice objects:**
```javascript
{ id: "Matthew", gender: "Male", language: "US English", description: "..." }
```

**Added TTS Language dropdown in HTML:**
```html
<select id="tts_language">
    <option value="US English">US English</option>
    <option value="British English">British English</option>
    <option value="Australian English">Australian English</option>
</select>
```

#### 3. Enhanced Debugging

Added comprehensive logging to track voice filtering:
```javascript
console.log("🔍 updateVoiceOptions called:", service, "language:", language);
console.log("✅ STANDARD voices loaded:", voices.length);
console.log("🌍 Filtered by language:", language, "→", voices.length);
console.log("👨 Males:", males.length, "👩 Females:", females.length);
```

### Testing Results

**US English + AWS Polly Standard:**
- Expected: 8 voices (3M + 5F)
- Actual: ✅ 8 voices
- Missing from Neural: Stephen, Ruth, Danielle, Kevin

**US English + AWS Polly Neural:**
- Expected: 11 voices (4M + 7F)
- Actual: ✅ 11 voices
- Includes: Stephen, Ruth, Danielle (Neural-only)

### Files Changed

1. **js/channels-unified.js**
   - Updated `AWS_POLLY_VOICES` object with correct voice arrays
   - Added language field to all voice objects
   - Enhanced `updateVoiceOptions()` function with logging
   - Prepared for language filtering (parameter added)

2. **channels.html**
   - Added TTS Language dropdown
   - Positioned between TTS Service and TTS Voice Profile

### Next Steps (Pending)

1. **Complete Language Filtering:**
   - Update `updateVoiceOptions()` to filter by selected language
   - Update `initializeVoiceSelect()` to listen to language changes
   - Test all language combinations

2. **Database Integration:**
   - Add `tts_language` field to `ChannelConfigs` table
   - Update `populateForm()` to load language preference
   - Update save functions to persist language selection

3. **Documentation:**
   - Update main documentation with new TTS options
   - Document available voices per language/engine combination

### Commit Info

**Commit:** af2afd2
**Message:** Fix AWS Polly voice filtering for Standard vs Neural engines
**Date:** 2025-11-04
**Pushed to:** origin/master

---

## Technical Notes

### AWS Polly Voice Availability

**Neural Engine:**
- Higher quality, more natural-sounding
- More voices available for US English
- Includes Stephen, Ruth, Danielle (not in Standard)
- Higher cost per character

**Standard Engine:**
- Lower cost
- Fewer voices available
- Missing some popular voices (Stephen, Ruth, Danielle, Kevin)
- Good quality but less natural than Neural

### Voice Distribution

| Language | Neural | Standard |
|----------|--------|----------|
| US English | 11 voices | 8 voices |
| British English | 3 voices | 3 voices |
| Australian English | 1 voice | 2 voices |
| **Total** | **15 voices** | **13 voices** |

---

*Generated: 2025-11-04*
