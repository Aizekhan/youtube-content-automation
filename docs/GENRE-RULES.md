# Genre-Specific Voice Rules

Complete reference for SSML generation rules by genre.

## Overview

The SSML Generator applies different voice effects based on content genre to enhance storytelling and audience engagement.

---

## Supported Genres

### 🎭 Horror
**Purpose:** Create tension, atmosphere, and psychological unease

**Configuration:**
```python
{
    'default_rate': 'slow',
    'default_pitch': 'low',
    'pause_multiplier': 1.5,  # 450ms pauses
    'use_whisper': True,
    'variation_effects': {
        'whisper': {'phonation': 'soft', 'rate': 'slow'},
        'dramatic': {'volume': 'loud', 'rate': 'medium'},
        'normal': {'rate': 'medium'}
    }
}
```

**Effects:**
- **Whisper** (phonation="soft") - Creates intimacy and vulnerability
- **Slow rate** - Builds suspense and dread
- **Long pauses** (450ms) - Enhances atmospheric tension
- **Low pitch** - Adds gravitas and foreboding

**Best For:**
- Horror stories
- Psychological thrillers
- Dark atmospheric content
- Suspenseful narratives

**Example SSML:**
```xml
<speak><amazon:effect phonation="soft"><prosody rate="slow">
The shadows moved on their own accord, <break time="225ms"/>
watching, <break time="225ms"/> waiting. <break time="450ms"/>
I was no longer alone in the darkness.
</prosody></amazon:effect></speak>
```

**Audio Characteristics:**
- Duration: +30% longer than normal (due to slow rate + pauses)
- Tone: Intimate, unsettling
- Emotional impact: High tension

---

### ⚡ Action
**Purpose:** Create urgency, energy, and excitement

**Configuration:**
```python
{
    'default_rate': 'fast',
    'default_pitch': 'medium',
    'pause_multiplier': 0.7,  # 210ms pauses
    'use_whisper': False,
    'variation_effects': {
        'fast': {'rate': 'fast', 'volume': 'loud'},
        'slow': {'rate': 'medium'},
        'normal': {'rate': 'fast'}
    }
}
```

**Effects:**
- **Fast rate** - Creates urgency and momentum
- **Loud volume** - Emphasizes intensity
- **Short pauses** (210ms) - Maintains energy flow
- **No whisper** - Full vocal presence

**Best For:**
- Action sequences
- Chase scenes
- Combat descriptions
- Urgent situations

**Example SSML:**
```xml
<speak><prosody rate="fast" volume="loud">
The explosion ripped through the building. <break time="210ms"/>
Debris flew everywhere as I sprinted for the exit. <break time="105ms"/>
No time to think, <break time="105ms"/> only survive!
</prosody></speak>
```

**Audio Characteristics:**
- Duration: -20% shorter than normal (fast rate + short pauses)
- Tone: Energetic, intense
- Emotional impact: Adrenaline, excitement

---

### 🔍 Mystery
**Purpose:** Create intrigue and varied pacing for revelations

**Configuration:**
```python
{
    'default_rate': 'medium',
    'default_pitch': 'medium',
    'pause_multiplier': 1.2,  # 360ms pauses
    'use_whisper': False,  # But available for specific scenes
    'variation_effects': {
        'whisper': {'phonation': 'soft', 'rate': 'slow'},
        'dramatic': {'volume': 'medium', 'rate': 'slow'},
        'normal': {'rate': 'medium'}
    }
}
```

**Effects:**
- **Varied rate** - Different pace for investigation vs revelation
- **Medium pauses** (360ms) - Balanced for thought and action
- **Selective whisper** - Used for tense or secretive moments
- **Dramatic slow** - For big revelations

**Best For:**
- Detective stories
- Investigation content
- Puzzle-solving narratives
- Mystery revelations

**Example SSML (3 variations):**

**Investigation (normal):**
```xml
<speak><prosody rate="medium">
The detective examined the evidence carefully. <break time="360ms"/>
Something didn't add up.
</prosody></speak>
```

**Tense moment (whisper):**
```xml
<speak><amazon:effect phonation="soft"><prosody rate="slow">
A whisper echoed through the corridor. <break time="360ms"/>
Someone else was there.
</prosody></amazon:effect></speak>
```

**Revelation (dramatic):**
```xml
<speak><prosody rate="slow" volume="medium">
The pieces finally clicked into place. <break time="360ms"/>
It all made sense now!
</prosody></speak>
```

**Audio Characteristics:**
- Duration: Standard with flexibility
- Tone: Thoughtful, varied
- Emotional impact: Curiosity, surprise

---

### 📖 Default
**Purpose:** Standard narration without special effects

**Configuration:**
```python
{
    'default_rate': 'medium',
    'default_pitch': 'medium',
    'pause_multiplier': 1.0,  # 300ms pauses
    'use_whisper': False,
    'variation_effects': {
        'normal': {'rate': 'medium'}
    }
}
```

**Effects:**
- **Medium rate** - Natural speaking pace
- **Standard pauses** (300ms) - Normal rhythm
- **No special effects** - Clean, clear narration

**Best For:**
- Educational content
- Documentary-style narration
- General storytelling
- News-style content

**Example SSML:**
```xml
<speak><prosody rate="medium">
The story begins with a simple question. <break time="300ms"/>
What happens when curiosity meets opportunity?
</prosody></speak>
```

---

## Variation Types

### Available Variations

#### **normal**
- Standard narration
- No special effects
- Uses genre default rate

#### **whisper**
- Soft phonation (Polly only)
- Slow rate
- Intimate, secretive tone
- Available: Horror, Mystery

#### **dramatic**
- Increased volume
- Slow to medium rate
- Emphasizes importance
- Available: All genres

#### **action/fast**
- Fast rate
- Often loud volume
- High energy
- Available: Action, general use

#### **slow**
- Slow rate
- Thoughtful pacing
- Available: All genres

---

## Pause System

### Pause Calculation

**Base pause:** 300ms

**Multipliers by genre:**
- Horror: 1.5x = **450ms**
- Action: 0.7x = **210ms**
- Mystery: 1.2x = **360ms**
- Default: 1.0x = **300ms**

### Pause Locations

**Long pause (full multiplier):**
- After period (.)
- After exclamation (!)
- After question (?)
- After ellipsis (...) - 1.5x longer

**Short pause (0.5x multiplier):**
- After comma (,)

**Example:**
```
Horror genre (450ms base):
- Period: 450ms
- Ellipsis: 675ms (450 * 1.5)
- Comma: 225ms (450 * 0.5)
```

---

## Choosing the Right Genre

### Decision Matrix

| Content Type | Primary Genre | Alternative | Notes |
|--------------|---------------|-------------|-------|
| Horror stories | Horror | Mystery | Use Horror for atmospheric dread |
| Thrillers | Mystery | Action | Mystery for psychological, Action for physical |
| Action scenes | Action | - | Use Action exclusively for chase/combat |
| Documentary | Default | - | Keep it clean and clear |
| Educational | Default | - | Standard pacing for learning |
| Detective work | Mystery | - | Varied pace for investigation |
| Sci-fi | Default | Action | Action for space battles, Default otherwise |
| Fantasy | Default | Mystery | Mystery for magical secrets |

---

## Testing Genre Rules

### Test SSML Generator

```bash
# Horror test
aws lambda invoke \
  --function-name ssml-generator \
  --payload '{"scenes":[{"scene_number":1,"scene_narration":"The darkness crept closer","variation_used":"whisper"}],"genre":"Horror","tts_service":"aws_polly_neural"}' \
  horror-test.json

# Action test
aws lambda invoke \
  --function-name ssml-generator \
  --payload '{"scenes":[{"scene_number":1,"scene_narration":"The building exploded","variation_used":"fast"}],"genre":"Action","tts_service":"aws_polly_neural"}' \
  action-test.json
```

### Verify SSML

**Horror should contain:**
- `<amazon:effect phonation="soft">`
- `rate="slow"`
- `<break time="450ms"/>`

**Action should contain:**
- `rate="fast"`
- `volume="loud"`
- `<break time="210ms"/>`

---

## Adding New Genres

### Step 1: Define Rules

Edit `aws/lambda/ssml-generator/lambda_function.py`:

```python
GENRE_RULES = {
    'YourGenre': {
        'default_rate': 'medium',
        'default_pitch': 'medium',
        'pause_multiplier': 1.0,
        'use_whisper': False,
        'variation_effects': {
            'normal': {'rate': 'medium'},
            'dramatic': {'volume': 'loud', 'rate': 'slow'}
        }
    }
}
```

### Step 2: Test Locally

```bash
cd aws/lambda/ssml-generator
python test_ssml.py
```

### Step 3: Deploy

```bash
python -m zipfile -c function.zip lambda_function.py
aws lambda update-function-code \
  --function-name ssml-generator \
  --zip-file fileb://function.zip
```

### Step 4: Test in Production

Run Step Functions execution with new genre.

---

## Best Practices

### DO ✅
- Use Horror for atmospheric, slow-burn content
- Use Action for fast-paced, energetic scenes
- Use Mystery for investigative content with revelations
- Test each genre before production use
- Match genre to emotional tone of content

### DON'T ❌
- Mix genres within single video (confusing)
- Use Action for calm, thoughtful content
- Use Horror whisper for loud, energetic scenes
- Skip testing after changing genre rules
- Ignore pause multipliers (they matter!)

---

## Performance Impact

### Duration Comparison (same 100-word script)

| Genre | Duration | Delta | Reason |
|-------|----------|-------|--------|
| Horror | 52 seconds | +30% | Slow rate + long pauses |
| Default | 40 seconds | baseline | Standard pacing |
| Action | 32 seconds | -20% | Fast rate + short pauses |
| Mystery | 43 seconds | +7.5% | Slightly longer pauses |

---

## References

- [AWS Polly SSML Reference](https://docs.aws.amazon.com/polly/latest/dg/supportedtags.html)
- [TTS Architecture](./TTS-ARCHITECTURE.md)
- [Genre Comparison Report](../GENRE-COMPARISON.md)

---

**Last Updated:** 2025-11-25
**Status:** Production Ready ✅
