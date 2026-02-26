"""
Three Phase Story Engine
Generates narrative through three sequential OpenAI calls:
- Phase 1a: Story Mechanics (archetype + mechanics JSON)
- Phase 1b: Narrative Generation (based on locked mechanics)
- Phase 1c: Image/Audio Prompts (with frozen character strings)
"""

import json
import http.client
import ssl
from archetype_mechanics import (
    get_archetype_pool,
    format_archetype_pool_for_prompt,
    validate_mechanics_json
)
from openai_cache import get_cached_response, cache_response


def call_openai_api(api_key, system_message, user_message, model='gpt-4o-mini',
                    temperature=0.7, max_tokens=4000, use_json=True):
    """
    Reusable OpenAI API caller

    Args:
        api_key (str): OpenAI API key
        system_message (str): System message
        user_message (str): User message
        model (str): Model name (gpt-4o, gpt-4o-mini)
        temperature (float): Temperature
        max_tokens (int): Max tokens
        use_json (bool): Use JSON response format

    Returns:
        dict: OpenAI API response
    """
    request_body = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': system_message},
            {'role': 'user', 'content': user_message}
        ],
        'temperature': temperature,
        'max_tokens': max_tokens
    }

    if use_json:
        request_body['response_format'] = {'type': 'json_object'}

    # SECURITY: SSL/TLS verification and timeout
    ssl_context = ssl.create_default_context()
    conn = http.client.HTTPSConnection('api.openai.com', context=ssl_context, timeout=240)
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }

    try:
        conn.request('POST', '/v1/chat/completions', body=json.dumps(request_body), headers=headers)
        response = conn.getresponse()
        response_data = response.read().decode('utf-8')
    finally:
        conn.close()

    if response.status != 200:
        raise Exception(f"OpenAI API Error: HTTP {response.status} - {response_data}")

    result = json.loads(response_data)

    if 'error' in result:
        raise Exception(f"OpenAI API Error: {result['error'].get('message', 'Unknown')}")

    return result


def build_voice_instructions(series_context):
    """
    Build VOICE_INSTRUCTIONS for Phase 1b prompt

    Args:
        series_context (dict|None): Series context with narrator and character voices

    Returns:
        str: Voice instructions or empty string
    """
    if not series_context:
        return ""

    narrator_voice = series_context.get('narrator_voice', {})
    characters = series_context.get('characters', {})

    if not narrator_voice and not characters:
        return ""

    narrator_speaker = narrator_voice.get('speaker', 'ryan')
    narrator_desc = narrator_voice.get('voice_description', 'Neutral narration')

    section = f"""
═══════════════════════════════════════════════════════════
🎙️ VOICE CONFIGURATION - SERIES MODE
═══════════════════════════════════════════════════════════

NARRATOR VOICE:
  Speaker: {narrator_speaker}
  Style: {narrator_desc}

"""

    if characters:
        section += "CHARACTER VOICES:\n"
        for char_id, char in characters.items():
            char_name = char.get('name', char_id)
            voice_config = char.get('voice_config', {})
            speaker = voice_config.get('speaker', 'ryan')
            voice_desc = voice_config.get('voice_description', 'Neutral voice')
            section += f"  [{char_id.upper()}] {char_name}: {speaker} - {voice_desc}\n"

    section += """
⚠️ MANDATORY TEXT FORMAT:

You MUST format ALL narration text with voice tags:

[NARRATOR] narration text here
[CHARACTER_ID] dialogue text here

EXAMPLE:
[NARRATOR] The forest was quiet. Too quiet. <break time='1s'/>
[EMMA] Did you hear that?
[NARRATOR] Emma's voice trembled slightly. She gripped the crystal tighter.
[MERLIN] The darkness is closer than you think, child.

CRITICAL RULES:
1. EVERY line of narration MUST start with [NARRATOR]
2. EVERY character dialogue MUST start with [CHARACTER_ID] in UPPERCASE
3. Use character IDs from the list above (e.g., [EMMA], [MERLIN])
4. Do NOT create new character voice tags - use only existing characters
5. If a character speaks who isn't in the list, use [NARRATOR] to describe their speech

═══════════════════════════════════════════════════════════
"""
    return section


def build_series_context_section(series_context):
    """
    Build SERIES_CONTEXT_SECTION for Phase 1a prompt

    Args:
        series_context (dict|None): Series context from content-topics-get-next

    Returns:
        str: Formatted series context section or empty string
    """
    if not series_context:
        return ""

    tension_level = int(series_context.get('tension_level', 5))
    archetypes_used = series_context.get('archetypes_used', [])
    open_threads = series_context.get('open_threads', [])
    characters = series_context.get('characters', {})
    episode_number = int(series_context.get('episode_number', 1))
    total_episodes = int(series_context.get('total_episodes', 10))
    arc_goal = series_context.get('season_arc', {}).get('arc_goal', '')

    # Build archetypes already used list
    used_archetypes_text = ""
    if archetypes_used:
        used_list = ", ".join([f"EP{a.get('ep')}: {a.get('archetype')}" for a in archetypes_used])
        used_archetypes_text = f"ARCHETYPES ALREADY USED: {used_list}\n⚠️ YOU MUST NOT REPEAT THESE ARCHETYPES"
    else:
        used_archetypes_text = "This is the first episode - choose any archetype from the pool"

    # Tension level guidance
    tension_guide = {
        range(1, 4): "CALM DEVELOPMENT - No major conflicts, character building, setup",
        range(4, 7): "MODERATE TENSION - Develop existing threads, introduce complications",
        range(7, 9): "HIGH CONFLICT - Major twist, revelation, or confrontation required",
        range(9, 11): "CLIMAX/FINALE - Resolution of major threads, peak dramatic moment"
    }
    tension_desc = next((desc for r, desc in tension_guide.items() if tension_level in r), "Moderate")

    # Open threads
    threads_text = ""
    if open_threads:
        high_threads = [t for t in open_threads if t.get('priority') == 'HIGH']
        if high_threads and tension_level >= 7:
            threads_text = f"\n\n🔴 HIGH PRIORITY THREADS (MUST address at tension {tension_level}):\n"
            for t in high_threads[:2]:
                threads_text += f"  - {t.get('description')}\n"
        else:
            threads_text = f"\n\nOPEN THREADS:\n"
            for t in open_threads[:3]:
                priority_icon = "🔴" if t.get('priority') == 'HIGH' else "🟡"
                threads_text += f"  {priority_icon} {t.get('description')}\n"

    # Characters
    characters_text = ""
    if characters:
        characters_text = f"\n\nEXISTING CHARACTERS (Do NOT create new ones unless tension >= 5 and narratively essential):\n"
        for char_id, char in list(characters.items())[:5]:
            characters_text += f"  - {char.get('name')}: {char.get('visual_frozen', 'N/A')}\n"

    section = f"""
═══════════════════════════════════════════════════════════
🎬 SERIES CONTEXT - EPISODE {episode_number}/{total_episodes}
═══════════════════════════════════════════════════════════

SERIES ARC GOAL: {arc_goal}

{used_archetypes_text}

TENSION LEVEL FOR THIS EPISODE: {tension_level}/10
{tension_desc}

SERIES RULES YOU MUST FOLLOW:

1️⃣ ARCHETYPE SELECTION:
   - You MUST choose an archetype that is NOT in the "ALREADY USED" list above
   - Repeating archetypes breaks series variety - this is MANDATORY

2️⃣ TENSION MATCHING:
   - Tension {tension_level}/10 means: {tension_desc}
   - Your mechanics MUST match this intensity level

3️⃣ PLOT THREADS:{threads_text}
   {"- If tension >= 7: You MUST develop or resolve at least one HIGH priority thread" if tension_level >= 7 else "- Continue developing threads or introduce new MEDIUM priority threads"}

4️⃣ CHARACTERS:{characters_text}
   - Use existing characters when possible
   - New characters only if narratively essential and tension >= 5

═══════════════════════════════════════════════════════════
"""
    return section


def generate_phase1a_mechanics(api_key, topic, complexity_level, genre, archetype_pool,
                               series_context=None, use_cache=True, cache_key_suffix=''):
    """
    Phase 1a: Story Mechanics Generation

    Args:
        api_key (str): OpenAI API key
        topic (str): Content topic
        complexity_level (int): 1-10 complexity
        genre (str): Channel genre
        archetype_pool (list): List of allowed archetypes
        series_context (dict|None): Series context for episodic content
        use_cache (bool): Whether to use cache
        cache_key_suffix (str): Optional suffix for cache key (e.g., topic_id)

    Returns:
        dict: Mechanics JSON with archetype and mechanics
    """
    print("\n═══ PHASE 1a: STORY MECHANICS ═══")
    print(f"  Topic: {topic}")
    print(f"  Complexity: {complexity_level}")
    print(f"  Genre: {genre}")
    print(f"  Archetype Pool: {archetype_pool}")

    # Load Phase 1a prompt template
    with open('./story_prompts/phase1a-story-mechanics.txt', 'r', encoding='utf-8') as f:
        template = f.read()

    # Format archetype pool for prompt
    archetype_descriptions = format_archetype_pool_for_prompt(archetype_pool)

    # Build series context section
    series_context_section = build_series_context_section(series_context)

    # Build prompt
    user_message = template.replace('{TOPIC}', topic) \
                          .replace('{COMPLEXITY_LEVEL}', str(complexity_level)) \
                          .replace('{GENRE_CONTEXT}', genre) \
                          .replace('{ARCHETYPE_POOL}', archetype_descriptions) \
                          .replace('{SERIES_CONTEXT_SECTION}', series_context_section) \
                          .replace('{SERIES_TITLE}', series_context.get('series_title', '') if series_context else '') \
                          .replace('{SEASON_ARC_GOAL}', series_context.get('season_arc', {}).get('arc_goal', '') if series_context else '') \
                          .replace('{PROTAGONIST_NAME}', next((v.get('name', '') for v in series_context.get('characters', {}).values() if v.get('role') == 'protagonist'), '') if series_context else '') \
                          .replace('{EPISODE_NUMBER}', str(series_context.get('episode_number', '')) if series_context else '') \
                          .replace('{ARCHETYPES_USED}', ', '.join([a.get('archetype', '') for a in series_context.get('archetypes_used', [])]) if series_context else '')

    system_message = "You are a Story Mechanics Architect."

    # Cache key
    cache_prompt = f"{user_message}:{cache_key_suffix}" if cache_key_suffix else user_message

    # Check cache
    if use_cache:
        cached_result = get_cached_response(cache_prompt, 'gpt-4o-mini', max_age_hours=24)
        if cached_result:
            print("  ✓ Cache HIT - using cached mechanics")
            mechanics_json = json.loads(cached_result['choices'][0]['message']['content'])
            usage = cached_result.get('usage', {'total_tokens': 0, 'prompt_tokens': 0, 'completion_tokens': 0})
            return mechanics_json, usage

    print("  ⟳ Cache MISS - calling OpenAI...")

    # Call OpenAI
    result = call_openai_api(
        api_key=api_key,
        system_message=system_message,
        user_message=user_message,
        model='gpt-4o-mini',  # Always use mini for Phase 1a
        temperature=0.7,
        max_tokens=2000,
        use_json=True
    )

    # Cache result
    if use_cache:
        cache_response(cache_prompt, 'gpt-4o-mini', result, ttl_hours=168)

    # Parse mechanics
    mechanics_json = json.loads(result['choices'][0]['message']['content'])

    # Validate
    is_valid, error = validate_mechanics_json(mechanics_json)
    if not is_valid:
        raise ValueError(f"Phase 1a validation failed: {error}")

    print(f"  ✓ Mechanics generated:")
    print(f"    Archetype: {mechanics_json.get('dominant_archetype')}")
    print(f"    Secondary: {mechanics_json.get('secondary_element', 'None')}")
    print(f"    Tokens: {result['usage']['total_tokens']}")

    return mechanics_json, result['usage']


def generate_phase1b_narrative(api_key, topic, mechanics, channel_config, num_scenes=8,
                               series_context=None, use_cache=True):
    """
    Phase 1b: Narrative Generation

    Args:
        api_key (str): OpenAI API key
        topic (str): Content topic
        mechanics (dict): Mechanics JSON from Phase 1a
        channel_config (dict): Channel configuration
        num_scenes (int): Number of scenes
        series_context (dict|None): Series context for voice configuration
        use_cache (bool): Whether to use cache

    Returns:
        dict: Narrative JSON with scenes
    """
    print("\n═══ PHASE 1b: NARRATIVE GENERATION ═══")

    # Load Phase 1b prompt template
    with open('./story_prompts/phase1b-narrative-generation.txt', 'r', encoding='utf-8') as f:
        template = f.read()

    # Extract config values
    genre = channel_config.get('genre', 'general')
    tone = channel_config.get('narrative_tone', channel_config.get('tone', 'neutral'))
    language = channel_config.get('language', 'en')
    duration = int(channel_config.get('target_duration_seconds', 180))
    complexity = int(channel_config.get('complexity_level', 5))

    # Build voice instructions
    voice_instructions = build_voice_instructions(series_context)

    # Build prompt
    user_message = template.replace('{MECHANICS_JSON}', json.dumps(mechanics, indent=2)) \
                          .replace('{TOPIC}', topic) \
                          .replace('{GENRE}', genre) \
                          .replace('{TONE}', tone) \
                          .replace('{LANGUAGE}', language) \
                          .replace('{DURATION}', str(duration)) \
                          .replace('{NUM_SCENES}', str(num_scenes)) \
                          .replace('{ARCHETYPE_FROM_MECHANICS}', mechanics.get('dominant_archetype', '')) \
                          .replace('{VOICE_INSTRUCTIONS}', voice_instructions)

    system_message = "You are a Master Narrative Writer."

    # Model selection based on complexity
    model = 'gpt-4o' if complexity >= 6 else 'gpt-4o-mini'
    print(f"  Model: {model} (complexity={complexity})")

    # Check cache
    if use_cache:
        cached_result = get_cached_response(user_message, model, max_age_hours=24)
        if cached_result:
            print("  ✓ Cache HIT - using cached narrative")
            narrative_json = json.loads(cached_result['choices'][0]['message']['content'])
            return narrative_json, None

    print("  ⟳ Cache MISS - calling OpenAI...")

    # Call OpenAI
    result = call_openai_api(
        api_key=api_key,
        system_message=system_message,
        user_message=user_message,
        model=model,
        temperature=0.8,  # Higher creativity for narrative
        max_tokens=4000,
        use_json=True
    )

    # Cache result
    if use_cache:
        cache_response(user_message, model, result, ttl_hours=168)

    # Parse narrative
    narrative_json = json.loads(result['choices'][0]['message']['content'])

    print(f"  ✓ Narrative generated:")
    print(f"    Title: {narrative_json.get('story_title')}")
    print(f"    Scenes: {len(narrative_json.get('scenes', []))}")
    print(f"    Tokens: {result['usage']['total_tokens']}")

    return narrative_json, result['usage']


def generate_phase1c_prompts(api_key, narrative, mechanics, image_config, series_context=None, use_cache=True):
    """
    Phase 1c: Image/Audio Prompts Generation

    Args:
        api_key (str): OpenAI API key
        narrative (dict): Narrative JSON from Phase 1b
        mechanics (dict): Mechanics JSON from Phase 1a
        image_config (dict): Image generation config
        series_context (dict|None): Series context for visual consistency
        use_cache (bool): Whether to use cache

    Returns:
        dict: Prompts JSON with image prompts for each scene
    """
    print("\n═══ PHASE 1c: IMAGE/AUDIO PROMPTS ═══")

    # Load Phase 1c prompt template
    with open('./story_prompts/phase1c-prompts-generation.txt', 'r', encoding='utf-8') as f:
        template = f.read()

    # Extract config values
    provider = image_config.get('provider', 'ec2-zimage')
    width = image_config.get('width', 1024)
    height = image_config.get('height', 576)
    style = image_config.get('style', 'cinematic, photorealistic')

    # Get frozen strings - prefer SeriesState for visual consistency
    protagonist_frozen = mechanics.get('protagonist_frozen', '')
    mirror_frozen = mechanics.get('mirror_character_frozen', '')

    # SERIES VISUAL CONSISTENCY: Use visual_frozen from SeriesState if available
    if series_context and series_context.get('characters'):
        print("  → Series detected: checking for frozen character visuals")
        chars = series_context['characters']

        # Find protagonist by character_id or role
        for char_id, char_data in chars.items():
            if char_data.get('visual_frozen'):
                # Use frozen visual if character is protagonist or matches mechanics character
                if 'protagon' in char_id.lower() or char_data.get('role') == 'protagonist':
                    protagonist_frozen = char_data['visual_frozen']
                    print(f"  ✓ Using frozen protagonist visual from SeriesState: {protagonist_frozen[:50]}...")
                elif 'mirror' in char_id.lower() or char_data.get('role') == 'mirror':
                    mirror_frozen = char_data['visual_frozen']
                    print(f"  ✓ Using frozen mirror visual from SeriesState: {mirror_frozen[:50]}...")

    # Build prompt
    user_message = template.replace('{NARRATIVE_JSON}', json.dumps(narrative, indent=2)) \
                          .replace('{MECHANICS_JSON}', json.dumps(mechanics, indent=2)) \
                          .replace('{IMAGE_PROVIDER}', provider) \
                          .replace('{WIDTH}', str(width)) \
                          .replace('{HEIGHT}', str(height)) \
                          .replace('{STYLE}', style) \
                          .replace('{PROTAGONIST_FROZEN}', protagonist_frozen) \
                          .replace('{MIRROR_CHARACTER_FROZEN}', mirror_frozen)

    system_message = "You are a Visual Prompt Engineer."

    # Check cache
    if use_cache:
        cached_result = get_cached_response(user_message, 'gpt-4o-mini', max_age_hours=24)
        if cached_result:
            print("  ✓ Cache HIT - using cached prompts")
            prompts_json = json.loads(cached_result['choices'][0]['message']['content'])
            return prompts_json, None

    print("  ⟳ Cache MISS - calling OpenAI...")

    # Call OpenAI
    result = call_openai_api(
        api_key=api_key,
        system_message=system_message,
        user_message=user_message,
        model='gpt-4o-mini',  # Always use mini for Phase 1c
        temperature=0.7,
        max_tokens=3000,
        use_json=True
    )

    # Cache result
    if use_cache:
        cache_response(user_message, 'gpt-4o-mini', result, ttl_hours=168)

    # Parse prompts
    prompts_json = json.loads(result['choices'][0]['message']['content'])

    print(f"  ✓ Prompts generated:")
    print(f"    Scene prompts: {len(prompts_json.get('scenes', []))}")
    print(f"    Thumbnail: {bool(prompts_json.get('thumbnail'))}")
    print(f"    Tokens: {result['usage']['total_tokens']}")

    return prompts_json, result['usage']


def run_three_phase_generation(api_key, topic, channel_config, series_context=None, use_cache=True, cache_key_suffix=''):
    """
    Run complete three-phase generation

    Args:
        api_key (str): OpenAI API key
        topic (str): Content topic
        channel_config (dict): Channel configuration
        series_context (dict|None): Series context for episodic content
        use_cache (bool): Whether to use cache
        cache_key_suffix (str): Optional cache key suffix (e.g., topic_id)

    Returns:
        dict: Complete content with narrative, mechanics, and prompts
    """
    print("\n" + "="*80)
    print("THREE PHASE STORY ENGINE v4.0" + (" - SERIES MODE" if series_context else ""))
    print("="*80)

    # Get archetype pool
    genre = channel_config.get('genre', 'general')
    custom_pool = channel_config.get('archetype_pool')
    archetype_pool = get_archetype_pool(genre=genre, custom_pool=custom_pool)

    # Get complexity level
    complexity_level = channel_config.get('complexity_level', 5)

    # Phase 1a: Story Mechanics
    mechanics, usage_1a = generate_phase1a_mechanics(
        api_key=api_key,
        topic=topic,
        complexity_level=complexity_level,
        genre=genre,
        archetype_pool=archetype_pool,
        series_context=series_context,
        use_cache=use_cache,
        cache_key_suffix=cache_key_suffix
    )

    # Phase 1b: Narrative Generation
    narrative, usage_1b = generate_phase1b_narrative(
        api_key=api_key,
        topic=topic,
        mechanics=mechanics,
        channel_config=channel_config,
        num_scenes=8,
        series_context=series_context,
        use_cache=use_cache
    )

    # Phase 1c: Image/Audio Prompts
    # Build image_config from channel config fields
    image_config = {
        'provider': channel_config.get('image_provider', 'ec2-zimage'),
        'width': channel_config.get('image_width', 1024),
        'height': channel_config.get('image_height', 576),
        'style': channel_config.get('image_style', 'cinematic, photorealistic')
    }
    print(f"  Image config: {image_config['width']}x{image_config['height']}, style={image_config['style']}")

    prompts, usage_1c = generate_phase1c_prompts(
        api_key=api_key,
        narrative=narrative,
        mechanics=mechanics,
        image_config=image_config,
        series_context=series_context,
        use_cache=use_cache
    )

    # Merge all data
    scenes_with_prompts = []
    for scene_narrative, scene_prompts in zip(narrative.get('scenes', []), prompts.get('scenes', [])):
        merged_scene = {**scene_narrative, **scene_prompts}
        scenes_with_prompts.append(merged_scene)

    # Calculate total tokens
    total_usage = {
        'phase_1a_tokens': usage_1a['total_tokens'] if usage_1a else 0,
        'phase_1b_tokens': usage_1b['total_tokens'] if usage_1b else 0,
        'phase_1c_tokens': usage_1c['total_tokens'] if usage_1c else 0,
        'total_tokens': sum([
            usage_1a['total_tokens'] if usage_1a else 0,
            usage_1b['total_tokens'] if usage_1b else 0,
            usage_1c['total_tokens'] if usage_1c else 0
        ])
    }

    print("\n" + "="*80)
    print("THREE PHASE GENERATION COMPLETE")
    print(f"  Phase 1a: {total_usage['phase_1a_tokens']} tokens")
    print(f"  Phase 1b: {total_usage['phase_1b_tokens']} tokens")
    print(f"  Phase 1c: {total_usage['phase_1c_tokens']} tokens")
    print(f"  Total: {total_usage['total_tokens']} tokens")
    print("="*80)

    return {
        'story_title': narrative.get('story_title'),
        'scenes': scenes_with_prompts,
        'thumbnail': prompts.get('thumbnail'),
        'metadata': narrative.get('metadata'),
        'mechanics': mechanics,
        'usage': total_usage
    }


# ============================================================================
# MERGED PHASE 1 (Phase 1a + 1b combined)
# ============================================================================

PHYSICAL_VERBS = [
    'drops', 'grabs', 'breaks', 'hits', 'runs', 'throws', 'cuts', 'burns',
    'falls', 'cracks', 'pushes', 'pulls', 'opens', 'closes', 'smashes',
    'shatters', 'bleeds', 'screams', 'collapses', 'stabs', 'shoots',
    'explodes', 'drowns', 'chokes', 'slams', 'tears', 'rips', 'crushes'
]

def validate_physical_events(mechanics):
    """
    Validate that event fields contain physical verbs

    Returns: (is_valid, errors_list)
    """
    errors = []

    event_fields = [
        'inciting_event', 'crisis_event', 'mirror_confrontation_event',
        'revelation_event', 'resolution_event'
    ]

    for field in event_fields:
        if field not in mechanics:
            errors.append(f"Missing required field: {field}")
            continue

        event_text = mechanics[field].lower()

        # Check for physical verbs
        has_physical_verb = any(verb in event_text for verb in PHYSICAL_VERBS)

        if not has_physical_verb:
            errors.append(f"{field}: No physical verb found. Text: '{mechanics[field][:50]}...'")

        # Check for forbidden abstract words
        forbidden = ['realizes', 'understands', 'feels', 'believes', 'thinks', 'knows']
        has_forbidden = any(word in event_text for word in forbidden)

        if has_forbidden:
            errors.append(f"{field}: Contains abstract concept (realizes/understands/feels)")

    return len(errors) == 0, errors


def run_merged_phase1(api_key, topic, channel_config, series_context=None, bible_context=""):
    """
    MERGED Phase 1: Generate mechanics + narrative in single GPT-4o call

    Args:
        api_key: OpenAI API key
        topic: Video topic
        channel_config: Channel configuration
        series_context: Series context (optional)
        bible_context: Series Bible text (120-200 words max)

    Returns:
        dict: {mechanics, scenes, usage}
    """
    print("\n" + "="*80)
    print("🔀 MERGED PHASE 1: Story Mechanics + Narrative Generation")
    print("="*80)

    # Load merged prompt template
    import os
    prompt_path = os.path.join(os.path.dirname(__file__), '..', 'story_prompts', 'phase1-merged.txt')

    with open(prompt_path, 'r', encoding='utf-8') as f:
        prompt_template = f.read()

    # Build series context section
    series_section = ""
    if series_context:
        series_section = f"""
SERIES MODE ACTIVE:
- Series: {series_context.get('series_title', 'Unknown')}
- Season: {series_context.get('season_arc', {}).get('season_number', 1)}
- Episode: {series_context.get('episode_number', 1)}

This is part of ongoing series. Maintain continuity with previous episodes.
"""

    # Build voice instructions
    voice_instructions = build_voice_instructions(series_context)

    # Replace placeholders
    system_message = prompt_template.replace('{BIBLE_CONTEXT}', bible_context)
    system_message = system_message.replace('{TOPIC}', topic)
    system_message = system_message.replace('{GENRE}', channel_config.get('genre', 'Mystery'))
    system_message = system_message.replace('{TONE}', channel_config.get('narrative_tone', 'dark'))
    system_message = system_message.replace('{LANGUAGE}', channel_config.get('language', 'en'))
    system_message = system_message.replace('{DURATION}', str(channel_config.get('target_duration', 180)))
    system_message = system_message.replace('{NUM_SCENES}', str(channel_config.get('num_scenes', 8)))
    system_message = system_message.replace('{SERIES_CONTEXT_SECTION}', series_section)

    user_message = f"Generate complete narrative for: {topic}"

    # Call OpenAI (gpt-4o, higher tokens for both steps)
    complexity = channel_config.get('complexity_level', 5)
    model = 'gpt-4o' if complexity >= 6 else 'gpt-4o'  # Always gpt-4o for merged

    print(f"  Model: {model}")
    print(f"  Topic: {topic}")
    print(f"  Bible context: {len(bible_context)} chars")

    result = call_openai_api(
        api_key=api_key,
        system_message=system_message,
        user_message=user_message,
        model=model,
        temperature=0.8,
        max_tokens=6000,  # More tokens for merged response
        use_json=True
    )

    # Parse response
    content = result['choices'][0]['message']['content']
    parsed = json.loads(content)

    # Extract mechanics and scenes
    mechanics = {
        'inciting_event': parsed.get('inciting_event'),
        'crisis_event': parsed.get('crisis_event'),
        'mirror_confrontation_event': parsed.get('mirror_confrontation_event'),
        'revelation_event': parsed.get('revelation_event'),
        'resolution_event': parsed.get('resolution_event'),
        'protagonist_frozen': parsed.get('protagonist_frozen'),
        'mirror_character_frozen': parsed.get('mirror_character_frozen'),
        'dominant_archetype': parsed.get('dominant_archetype')
    }

    scenes = parsed.get('scenes', [])

    # Validate physical events
    is_valid, validation_errors = validate_physical_events(mechanics)

    if not is_valid:
        print("\n⚠️  VALIDATION WARNINGS:")
        for error in validation_errors:
            print(f"  - {error}")
        # Continue anyway but log warnings

    usage = result['usage']

    print(f"\n✅ Merged Phase 1 complete:")
    print(f"  - Mechanics generated: {len([k for k in mechanics if mechanics[k]])}/8 fields")
    print(f"  - Scenes generated: {len(scenes)}")
    print(f"  - Tokens used: {usage['total_tokens']}")
    print(f"  - Validation: {'✓ PASS' if is_valid else '⚠ WARNINGS'}")

    return {
        'mechanics': mechanics,
        'scenes': scenes,
        'story_title': parsed.get('story_title', topic),
        'usage': {
            'merged_phase1_tokens': usage['total_tokens'],
            'total_tokens': usage['total_tokens']
        }
    }
