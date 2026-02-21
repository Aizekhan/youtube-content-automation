# Sprint 2 - Topic Analyzer + Context Enrichment

**Layer 2 Architecture Implementation**

## Sprint Goal
Analyze topic → enrich context → prepare for story generation with facts, mood, and Story DNA

---

## Architecture Overview

```
Topic from Queue
    ↓
Topic Analyzer (genre, type, complexity)
    ↓
Context Enrichment Pipeline:
    ├─ Wikipedia Facts Search (if factual_mode)
    ├─ Mood & Atmosphere Builder
    ├─ Story DNA Generator (unique twist, hooks)
    └─ Historical/Cultural Context
    ↓
Enriched MasterConfig
    ↓
content-narrative (with all context)
```

---

## Tasks Breakdown

### Task 2.1: Topic Analyzer Lambda
**Purpose:** Analyze topic_text and determine story characteristics

**Input:**
```json
{
  "topic_text": "The Mystery of the Lost City",
  "topic_description": {
    "context": "Ancient civilization",
    "tone_suggestion": "dark"
  },
  "story_profile": {
    "story_mode": "fiction",
    "world_type": "realistic"
  }
}
```

**Output:**
```json
{
  "analysis": {
    "genre": "mystery",
    "sub_genre": "archaeological_thriller",
    "story_type": "discovery_quest",
    "complexity_level": 4,
    "estimated_scenes": 8,
    "key_themes": ["exploration", "ancient_secrets", "danger"],
    "mood_tags": ["mysterious", "suspenseful", "adventurous"],
    "setting_type": "historical_location",
    "time_period": "modern_day_with_flashbacks"
  }
}
```

**AI Model:** OpenAI GPT-4 (fast analysis)

---

### Task 2.2: Wikipedia Facts Search Lambda
**Purpose:** Gather factual information for real_events mode channels

**When to trigger:**
- `story_mode == "real_events"` OR `factual_mode == true`
- Topic requires historical/scientific facts

**Input:**
```json
{
  "topic_text": "The Fall of Constantinople 1453",
  "search_depth": "detailed"
}
```

**Output:**
```json
{
  "facts_found": 15,
  "key_facts": [
    {
      "fact": "Constantinople fell on May 29, 1453",
      "source": "Wikipedia: Fall of Constantinople",
      "confidence": "high",
      "category": "historical_date"
    },
    {
      "fact": "Mehmed II led the Ottoman siege with 80,000 troops",
      "source": "Wikipedia: Mehmed II",
      "confidence": "high",
      "category": "military_detail"
    }
  ],
  "references": [
    "https://en.wikipedia.org/wiki/Fall_of_Constantinople",
    "https://en.wikipedia.org/wiki/Mehmed_II"
  ],
  "fact_check_status": "verified"
}
```

**Implementation:**
- Use Wikipedia API (free, no auth needed)
- Extract 10-20 key facts
- Categorize facts (dates, people, events, numbers)
- Store references for accuracy

---

### Task 2.3: Context Enrichment Lambda
**Purpose:** Build comprehensive context for story generation

**Processing:**
1. Analyze mood & atmosphere from topic + tone
2. Generate sensory details (sounds, visuals, feelings)
3. Build cultural/historical context if needed
4. Create character archetypes hints
5. Suggest plot tension points

**Input:**
```json
{
  "topic_text": "The Last Dive",
  "tone_suggestion": "dark",
  "genre": "horror",
  "world_type": "realistic"
}
```

**Output:**
```json
{
  "enriched_context": {
    "atmosphere": {
      "primary_mood": "claustrophobic_dread",
      "sensory_palette": {
        "visual": ["murky water", "fading light", "metal corrosion"],
        "sound": ["muffled echoes", "breathing apparatus", "distant creaks"],
        "tactile": ["cold pressure", "wet suit", "limited movement"]
      },
      "emotional_arc": "curiosity → unease → terror → desperation"
    },
    "setting_details": {
      "primary_location": "deep_sea_wreck",
      "time_of_day": "eternal_darkness",
      "weather_conditions": "underwater_currents",
      "isolation_level": "extreme"
    },
    "cultural_context": null,
    "symbolic_elements": ["depth as descent into unknown", "oxygen as ticking clock"]
  }
}
```

---

### Task 2.4: Story DNA Generator Lambda
**Purpose:** Create unique narrative elements to avoid clichés

**What it generates:**
- **Unique Twist:** Unexpected angle on the topic
- **Character Seeds:** Quick character concept ideas
- **Plot Hooks:** 3-5 potential story directions
- **Emotional Core:** Central feeling/theme
- **Surprise Injection:** Element to break predictability

**Input:**
```json
{
  "topic_text": "The Forgotten Temple",
  "genre": "mystery",
  "no_cliches_mode": true,
  "surprise_injection_level": 4
}
```

**Output:**
```json
{
  "story_dna": {
    "unique_twist": "The temple isn't abandoned - it's avoiding being found",
    "character_seeds": [
      {
        "archetype": "reluctant_scholar",
        "unique_trait": "can't read ancient languages but feels their meaning",
        "internal_conflict": "logic vs intuition"
      }
    ],
    "plot_hooks": [
      "The temple changes location every full moon",
      "Previous explorers left warnings, not treasures",
      "The protagonist has been there before - in dreams"
    ],
    "emotional_core": "The fear of discovering you're part of what you're searching for",
    "anti_cliche_guards": [
      "NO: Ancient curse that kills",
      "YES: Ancient protocol that tests worthiness in unexpected ways"
    ],
    "surprise_element": "The temple's guardian is the protagonist's future self"
  }
}
```

---

### Task 2.5: MasterConfig Builder Integration
**Purpose:** Combine all enriched data into single config for content-narrative

**Flow:**
```
content-build-master-config (updated)
    ↓
1. Load topic from ContentTopicsQueue
2. Load channel config (Story Profile)
3. Call Topic Analyzer
4. Call Wikipedia Facts (if needed)
5. Call Context Enrichment
6. Call Story DNA Generator
7. Merge all into MasterConfig
    ↓
Output: Complete enriched config for narrative generation
```

**Final MasterConfig Structure:**
```json
{
  "channel_id": "channel_123",
  "topic": {
    "topic_id": "topic_...",
    "topic_text": "...",
    "topic_description": {...}
  },
  "story_profile": {...},
  "topic_analysis": {
    "genre": "mystery",
    "complexity_level": 4,
    ...
  },
  "factual_data": {
    "facts": [...],
    "references": [...]
  },
  "enriched_context": {
    "atmosphere": {...},
    "setting_details": {...}
  },
  "story_dna": {
    "unique_twist": "...",
    "character_seeds": [...],
    "plot_hooks": [...]
  },
  "all_channel_fields": {...}
}
```

---

### Task 2.6: Step Functions Integration
**Update workflow to include context enrichment pipeline**

**New Step Functions Flow:**
```
1. CheckFactualMode (Choice State)
   ├─ IF factual_mode=true → SearchWikipediaFacts
   └─ ELSE → Skip to AnalyzeTopic

2. SearchWikipediaFacts (Lambda)
   ↓
3. AnalyzeTopic (Lambda: content-topic-analyzer)
   ↓
4. EnrichContext (Lambda: content-context-enrichment)
   ↓
5. GenerateStoryDNA (Lambda: content-story-dna)
   ↓
6. BuildMasterConfig (Lambda: content-build-master-config - updated)
   ↓
7. MegaNarrativeGenerator (existing)
```

---

### Task 2.7: Testing & Validation
**Test scenarios:**

1. **Fiction Mode Test:**
   - Topic: "The Whispering Forest"
   - Expected: Story DNA with unique twist, no Wikipedia facts
   - Validate: Cliché avoidance, surprise injection

2. **Real Events Mode Test:**
   - Topic: "The Apollo 13 Mission"
   - Expected: Wikipedia facts + accurate timeline
   - Validate: Fact accuracy, reference links

3. **Hybrid Mode Test:**
   - Topic: "What if Napoleon had GPS?"
   - Expected: Historical facts + fictional twist
   - Validate: Facts accurate, fiction clearly marked

---

## Lambda Functions to Create

1. **content-topic-analyzer** (Task 2.1)
   - Runtime: Python 3.11
   - Timeout: 30s
   - Memory: 512MB
   - Dependencies: OpenAI SDK

2. **content-search-facts** (Task 2.2)
   - Runtime: Python 3.11
   - Timeout: 45s
   - Memory: 256MB
   - Dependencies: requests, wikipedia-api

3. **content-context-enrichment** (Task 2.3)
   - Runtime: Python 3.11
   - Timeout: 30s
   - Memory: 512MB
   - Dependencies: OpenAI SDK

4. **content-story-dna** (Task 2.4)
   - Runtime: Python 3.11
   - Timeout: 30s
   - Memory: 512MB
   - Dependencies: OpenAI SDK

---

## Success Criteria

✅ All 4 new Lambda functions deployed and working
✅ Wikipedia facts search returns accurate data
✅ Story DNA generates unique twists (no clichés)
✅ Context enrichment adds atmosphere & sensory details
✅ MasterConfig contains all enriched data
✅ Step Functions workflow includes new pipeline
✅ End-to-end test: Topic → Enriched Narrative

---

## Estimated Timeline

- Task 2.1 (Topic Analyzer): 45 min
- Task 2.2 (Wikipedia Search): 30 min
- Task 2.3 (Context Enrichment): 45 min
- Task 2.4 (Story DNA): 45 min
- Task 2.5 (MasterConfig Integration): 30 min
- Task 2.6 (Step Functions Update): 30 min
- Task 2.7 (Testing): 30 min

**Total: ~4 hours**

---

## Next Steps After Sprint 2

**Sprint 3** will focus on:
- Character Profile Generator (persistent characters)
- Plot Structure Validator
- Consistency Checker
- Integration with episodic series mode

---

## Open Questions

1. Should Wikipedia search be cached (to avoid repeated API calls)?
2. Maximum number of facts to extract per topic? (current: 10-20)
3. Should Story DNA be regenerated on retry, or cached?
4. Language support for Wikipedia (English only, or multi-language)?

---

**Status:** Ready to start implementation
**Priority:** High (blocks narrative quality improvements)
**Dependencies:** Sprint 1 completed ✅
