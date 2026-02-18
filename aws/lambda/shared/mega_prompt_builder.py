"""
MEGA Prompt Builder

Builds comprehensive OpenAI prompt from mega_config
that includes instructions for ALL content components.

Output: system_message + user_message for OpenAI API
"""

import json


def build_mega_prompt(mega_config, selected_topic):
    """
    Build MEGA prompt for OpenAI that generates ALL content components

    Args:
        mega_config (dict): Merged configuration from mega_config_merger
        selected_topic (str): Topic selected by theme agent

    Returns:
        tuple: (system_message, user_message)
    """

    # Build SYSTEM message
    system_message = build_system_message(mega_config)

    # Build USER message
    user_message = build_user_message(mega_config, selected_topic)

    return system_message, user_message


def build_system_message(config):
    """Build comprehensive SYSTEM message with all instructions"""

    channel_ctx = config['channel_context']
    narrative_inst = config['narrative_instructions']
    image_inst = config['image_instructions']
    cta_inst = config['cta_instructions']
    thumbnail_inst = config['thumbnail_instructions']
    tts_inst = config['tts_instructions']
    sfx_inst = config['sfx_instructions']
    description_inst = config['description_instructions']

    system = f"""You are a MEGA Content Generator AI. You will create ALL components for a complete YouTube video in ONE comprehensive JSON response.

## YOUR ROLE

You are a multi-specialist AI that combines the expertise of:
1. **Narrative Architect** - Creates engaging story content
2. **Visual Director** - Designs image prompts for each scene
3. **Sound Designer** - Selects sound effects and music
4. **Voice Director** - Detects scene mood and assigns voice variations
5. **Marketing Writer** - Inserts creative CTAs
6. **Thumbnail Designer** - Creates clickable thumbnail concepts
7. **SEO Expert** - Writes optimized video descriptions

---

## CHANNEL CONTEXT

**Channel**: {channel_ctx['channel_name']}
**Genre**: {channel_ctx['genre']}
**Tone**: {channel_ctx['tone']}
**Content Type**: {channel_ctx['factual_mode']}
**Target Audience**: {channel_ctx['target_audience']}
**Content Focus**: {channel_ctx['content_focus']}
**Narration Style**: {channel_ctx['narration_style']}
**Emotional Temperature**: {channel_ctx['emotional_temperature']}
**Narrative Pace**: {channel_ctx['narrative_pace']}

---

## 1. NARRATIVE GENERATION

**Your Role**: {narrative_inst['role_definition']}

**Core Rules**:
{format_list(narrative_inst['core_rules'])}

**Hook Rules**:
{format_hook_rules(narrative_inst)}

**Story Structure**: {narrative_inst['story_structure_pattern']}
**Preferred Ending**: {narrative_inst['preferred_ending_tone']}
**Story Settings**: {narrative_inst['story_setting_variants']}
**Character Types**: {narrative_inst['story_character_types']}
**Point of View**: {narrative_inst['story_point_of_view_variants']}

---

## 2. VOICE VARIATION DETECTION

**Your Role**: Voice Director - Detect scene mood and mark appropriate variation

**Core Rules**:
- Generate PLAIN TEXT narration WITHOUT any markup tags
- DO NOT use SSML tags like <speak>, <prosody>, <break>, etc.
- Detect the emotional mood of each scene from the narrative content
- Assign variation_used field: "normal", "dramatic", "whisper", "action"
- Write natural, engaging prose without technical markup

**Mood Detection Guidelines**:
- **whisper**: Intimate, secretive, tense moments (Horror, Mystery)
- **dramatic**: Intense, emotional peaks (all genres)
- **action**: Fast-paced, urgent scenes (Action, Thriller)
- **normal**: Standard narrative flow (default)

**Variation Examples**:
{format_scene_variations(tts_inst['scene_variations'])}

IMPORTANT: The variation_used field will be used by our TTS system to programmatically apply voice effects.
You only need to DETECT the mood and assign the variation name - DO NOT add any SSML markup!

{format_voice_selection(tts_inst)}

---

## 3. IMAGE GENERATION

**Your Role**: {image_inst['role_definition']}

**Core Rules**:
{format_list(image_inst['core_rules'])}

**Visual Guidance**:
- Visual Keywords: {image_inst['visual_keywords']}
- Atmosphere: {image_inst['visual_atmosphere']}
- Style Variants: {image_inst['image_style_variants']}
- Color Palettes: {image_inst['color_palettes']}
- Lighting: {image_inst['lighting_variants']}
- Composition: {image_inst['composition_variants']}
- Reference Type: {image_inst['visual_reference_type']}

**Negative Prompt (avoid)**: {image_inst['negative_prompt']}

For EACH scene, generate:
- **image_prompt**: Detailed prompt for AI image generation (subject, action, environment, lighting, composition, style)
- **negative_prompt**: What to avoid

---

## 4. SFX / MUSIC SELECTION

**Your Role**: {sfx_inst['role_definition']}

**Rules**: {', '.join(sfx_inst['core_rules'])}

**SFX Library**: {format_sfx_library(sfx_inst['sfx_library'])}

**Music Library**: {format_music_library(sfx_inst['music_library'])}

**Return**: {{sfx_cues (array of library filenames), music_track (library filename), timing_estimates (optional)}}

---

## 5. CTA INSERTION

{format_cta_instructions(cta_inst)}

---

## 6. THUMBNAIL DESIGN

**Your Role**: {thumbnail_inst['role_definition']}

**Rules**: {', '.join(thumbnail_inst['core_rules'])}

**Return**: {{thumbnail_prompt (compelling visual), text_overlay (2-4 words), style_notes}}

---

## 7. VIDEO DESCRIPTION

**Your Role**: {description_inst['role_definition']}

**Core Rules**:
{format_list(description_inst['core_rules'])}

**Rules**: {', '.join(description_inst['core_rules'])}

**SEO Keywords**: {description_inst['seo_keywords']}

**Return**: {{description (hook + summary + timestamps), hashtags (array), timestamps (array)}}

---

## IMPORTANT NOTES

1. **PLAIN TEXT**: Scene narration must be PLAIN TEXT without any markup tags
2. **SFX**: Use ONLY files from provided libraries - DO NOT invent names
3. **CTA**: Make CTA creative and fit narrative tone (humor, mystery, suspense)
4. **Consistency**: All components must align with channel tone and genre
5. **Length**: Generate {config['constraints']['scene_count_target']} scenes, ~{config['constraints']['target_character_count']} characters total

---

## OUTPUT FORMAT

You MUST return valid JSON following this exact schema:

```json
{{
  "story_title": "string",
  "selected_voice": "string (ONLY if voice_selection_mode=auto)",
  "hook": "string (plain text only)",
  "scenes": [
    {{
      "scene_number": 1,
      "scene_title": "string",
      "scene_narration": "string (PLAIN TEXT, no markup)",
      "image_prompt": "string (detailed)",
      "negative_prompt": "string",
      "sfx_cues": ["filename1.mp3", "filename2.mp3"],
      "music_track": "track_name.mp3",
      "timing_estimates": [0.0, 3.5, 7.2],
      "variation_used": "normal|dramatic|action|whisper"
    }}
  ],
  "cta_segments": [
    {{
      "position": "35%",
      "cta_text": "string (plain text)",
      "type": "subscribe|like|comment",
      "style_note": "string"
    }}
  ],
  "thumbnail": {{
    "thumbnail_prompt": "string",
    "text_overlay": "string (3-5 words)",
    "style_notes": "string"
  }},
  "description": {{
    "description": "string",
    "hashtags": ["tag1", "tag2"],
    "timestamps": [{{"time": "0:00", "label": "Intro"}}]
  }},
  "metadata": {{
    "total_word_count": 0,
    "total_scenes": 0,
    "estimated_duration_seconds": 0
  }}
}}
```
"""

    
    # Inject Story Blueprint section if present
    blueprint = config.get('story_blueprint')
    if blueprint:
        blueprint_section = format_story_blueprint(blueprint)
        system = system.replace('## 1. NARRATIVE GENERATION', blueprint_section + '## 1. NARRATIVE GENERATION', 1)
    return system


def build_user_message(config, topic):
    """Build USER message with topic and constraints"""

    constraints = config['constraints']

    user = f"""Generate complete video content for the following topic:

**Topic**: {topic}

**Constraints**:
- Target Scenes: {constraints['scene_count_target']}
- Target Character Count: {constraints['target_character_count']}
- Target Duration: {constraints['video_duration_target']} minutes

Generate ALL components in JSON format following the output schema provided above.

Remember:
1. Generate PLAIN TEXT narration (NO SSML tags)
2. Use ONLY SFX/music from provided libraries
3. Make CTA creative and in-theme
4. Generate detailed image_prompt for each scene
5. Create clickable thumbnail concept
6. Write SEO-optimized description with timestamps

Return valid JSON only, no additional text.
"""


    # Add blueprint-specific scene count hint to user message
    blueprint = config.get('story_blueprint')
    if blueprint:
        scene_blueprints = blueprint.get('scene_blueprints', [])
        if scene_blueprints:
            scene_count = len(scene_blueprints)
            override_parts = [
                chr(10) + chr(10),
                '**STORY BLUEPRINT OVERRIDE**: Generate exactly ',
                str(scene_count),
                ' scenes. Follow the emotional curve in the Story Blueprint section above.',
                ' Each scene must match its designated purpose and intensity level.',
            ]
            user += ''.join(override_parts)

    return user


# Helper formatting functions

def format_list(items):
    """Format list items with bullet points"""
    if not items:
        return "- (No specific rules)"
    return "\n".join([f"- {item}" for item in items])


def format_hook_rules(narrative_inst):
    """Format hook rules"""
    hook_rules = narrative_inst.get('hook_rules', {})
    hook_enabled = narrative_inst.get('hook_enabled', True)

    if not hook_enabled:
        return "**Hook Disabled** - Do not generate hook"

    return f"""**Hook Enabled**: Yes
**Style**: {hook_rules.get('style', 'engaging')}
**Placement**: {hook_rules.get('placement', 'first_15_seconds')}

Generate an attention-grabbing hook (50-120 characters) that:
- Fits channel tone and genre
- Creates curiosity or suspense
- Encourages viewer to keep watching
"""


def format_scene_variations(variations):
    """Format voice variation guidelines (for mood detection)"""
    if not variations:
        return "- (No variations defined, use 'normal' for all scenes)"

    formatted = []
    for name, params in variations.items():
        formatted.append(f"""**{name.upper()}**:
  - Rate: {params.get('rate', 'medium')}
  - Pitch: {params.get('pitch', '+0%')}
  - Volume: {params.get('volume', 'medium')}
  - Pause Before: {params.get('pause_before', '0ms')}
  - Pause After: {params.get('pause_after', '0ms')}
  - Description: {params.get('description', '')}""")

    return "\n\n".join(formatted)


def format_voice_selection(tts_inst):
    """Format voice selection instructions"""
    mode = tts_inst.get('voice_selection_mode', 'manual')

    if mode == 'auto':
        voices = tts_inst.get('available_voices', [])
        voice_list = "\n".join([f"  - **{v.get('voice_id')}**: {v.get('language')} {v.get('gender')} ({v.get('style', 'neutral')})" for v in voices])

        return f"""**Voice Selection Mode**: AUTO

You MUST select ONE voice from the available list below that best fits the channel tone and genre.

**Available Voices**:
{voice_list}

Return your choice in the "selected_voice" field (voice_id only, e.g., "Matthew").
"""
    else:
        voice_id = tts_inst.get('voice_id', 'Matthew')
        return f"""**Voice Selection Mode**: MANUAL

Use fixed voice: **{voice_id}**

Do NOT include "selected_voice" field in response.
"""


def format_sfx_library(library):
    """Format SFX library for display"""
    if not library:
        return "- (No SFX library provided)"

    formatted = []
    for category, subcategories in library.items():
        formatted.append(f"**{category.upper()}**:")
        if isinstance(subcategories, dict):
            for subcat, files in subcategories.items():
                file_list = ", ".join(files) if isinstance(files, list) else str(files)
                formatted.append(f"  - {subcat}: {file_list}")
        else:
            formatted.append(f"  - {subcategories}")

    return "\n".join(formatted)


def format_music_library(library):
    """Format music library for display"""
    if not library:
        return "- (No music library provided)"

    formatted = []
    for genre, moods in library.items():
        formatted.append(f"**{genre.upper()}**:")
        if isinstance(moods, dict):
            for mood, tracks in moods.items():
                track_list = ", ".join(tracks) if isinstance(tracks, list) else str(tracks)
                formatted.append(f"  - {mood}: {track_list}")
        else:
            formatted.append(f"  - {moods}")

    return "\n".join(formatted)


def format_cta_instructions(cta_inst):
    """Format CTA instructions"""
    if not cta_inst.get('enabled', False):
        return """**CTA Insertion**: DISABLED

Do NOT generate CTA segments. Return empty array for "cta_segments".
"""

    placements = cta_inst.get('placements', [])
    placement_list = "\n".join([f"  - {p.get('position')} - Type: {p.get('type')}" for p in placements])

    return f"""**Your Role**: {cta_inst['role_definition']}

**Core Rules**:
{format_list(cta_inst['core_rules'])}

**CTA Settings**:
- Style: {cta_inst.get('style', 'creative')}
- Max Duration: {cta_inst.get('max_duration_seconds', 15)} seconds
- Placements:
{placement_list}

**IMPORTANT**: Make CTA creative and fit the narrative tone!

Examples:
- Mystery channel: "Speaking of unsolved mysteries... have YOU subscribed yet?"
- Epic channel: "If you want to witness MORE legendary tales, click that subscribe button!"
- Horror channel: "Don't let this be YOUR last video... subscribe to stay alive!"

Use wordplay, puns, or thematic hooks. Make it FUN and IN-CHARACTER!
"""



def format_story_blueprint(blueprint):
    """Format Story Blueprint into prompt instructions for OpenAI."""
    if not blueprint:
        return None

    name = blueprint.get("name", "Unknown")
    pacing = blueprint.get("pacing_profile", "")
    opening = blueprint.get("opening_strategy", "")
    ending = blueprint.get("ending_type", "")
    scenes = blueprint.get("scene_blueprints", [])
    retention_map = blueprint.get("retention_map", {})
    scene_instructions = blueprint.get("scene_instructions", {})

    # DynamoDB may store lists as JSON strings - parse if needed
    if isinstance(scenes, str):
        scenes = json.loads(scenes)
    if isinstance(retention_map, str):
        retention_map = json.loads(retention_map)
    if isinstance(scene_instructions, str):
        scene_instructions = json.loads(scene_instructions)

    # Build emotion curve table
    emotion_rows = []
    for s in scenes:
        n = s.get("n", "?")
        purpose = s.get("purpose", "")
        emotion = s.get("emotion", "")
        intensity = int(s.get("intensity", 5))
        retention = s.get("retention")
        if retention in (None, "null", ""):
            retention = ""
        voice = s.get("voice", "normal")
        visual = s.get("visual", "medium")
        bar = chr(9608) * intensity + chr(9617) * (10 - intensity)
        retention_note = " -> " + retention if retention else ""
        row = "  Scene {:>2} [{:<12}] {} ({}/10) | {:<18} | voice:{:<9} | visual:{}{}".format(
            n, purpose, bar, intensity, emotion, voice, visual, retention_note
        )
        emotion_rows.append(row)

    emotion_table = chr(10).join(emotion_rows)

    # Build per-scene writing instructions
    instruction_lines = []
    for s in scenes:
        purpose = s.get("purpose", "")
        instruction = scene_instructions.get(purpose, "")
        if instruction:
            instruction_lines.append("  **Scene {} ({})**:".format(s.get("n"), purpose))
            instruction_lines.append("    " + instruction)

    instructions_text = chr(10).join(instruction_lines) if instruction_lines else "  (Use default narrative judgment)"

    # Retention devices
    hook_scene = retention_map.get("hook_scene", 1)
    micro_hooks = retention_map.get("micro_hooks", [])
    cliffhanger = retention_map.get("cliffhanger", "")
    climax = retention_map.get("climax", "")
    cta_after = retention_map.get("cta_after_scene", "")

    opening_hint = ""
    if opening == "in_medias_res":
        opening_hint = "Start IN the middle of action. No intro or setup. Drop viewer into the most intense moment."
    elif opening == "shocking_fact":
        opening_hint = "Open with a fact so shocking it demands explanation. State it bare, without context."
    elif opening == "open_question":
        opening_hint = "Open with a question the viewer cannot resist answering."
    elif opening == "false_start":
        opening_hint = "Open with a misleading scenario, then pivot to the real story."

    lines_out = [
        "## STORY BLUEPRINT: " + name.upper(),
        "",
        "**Template**: {} | **Pacing**: {} | **Opening**: {} | **Ending**: {}".format(name, pacing, opening, ending),
        "",
        "### Emotional Curve (FOLLOW THIS EXACTLY)",
        emotion_table,
        "",
        "### Retention Engineering",
        "- **Hook Scene**: Scene {} - Open with maximum impact".format(hook_scene),
        "- **Micro-Hooks**: Scenes {} - End WITHOUT resolving tension".format(micro_hooks),
        "- **Cliffhanger**: Scene {} - Full stop at max tension, NO resolution".format(cliffhanger),
        "- **Climax**: Scene {} - Peak intensity, decisive moment".format(climax),
        "- **CTA Placement**: After Scene {}".format(cta_after),
        "",
        "### Per-Scene Writing Instructions",
        instructions_text,
        "",
        "### Opening Strategy: " + opening.upper(),
        opening_hint,
        "",
        "**CRITICAL**: Follow the emotional curve above. Each scene must match its purpose and intensity.",
        "**DO NOT** write all scenes at equal intensity. The variation IS the engagement.",
        "",
        "---",
        "",
    ]

    return chr(10).join(lines_out)
