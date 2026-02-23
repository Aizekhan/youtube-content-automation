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


def generate_phase1a_mechanics(api_key, topic, complexity_level, genre, archetype_pool,
                               use_cache=True, cache_key_suffix=''):
    """
    Phase 1a: Story Mechanics Generation

    Args:
        api_key (str): OpenAI API key
        topic (str): Content topic
        complexity_level (int): 1-10 complexity
        genre (str): Channel genre
        archetype_pool (list): List of allowed archetypes
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

    # Build prompt
    user_message = template.replace('{TOPIC}', topic) \
                          .replace('{COMPLEXITY_LEVEL}', str(complexity_level)) \
                          .replace('{GENRE_CONTEXT}', genre) \
                          .replace('{ARCHETYPE_POOL}', archetype_descriptions)

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
                               use_cache=True):
    """
    Phase 1b: Narrative Generation

    Args:
        api_key (str): OpenAI API key
        topic (str): Content topic
        mechanics (dict): Mechanics JSON from Phase 1a
        channel_config (dict): Channel configuration
        num_scenes (int): Number of scenes
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
    duration = channel_config.get('target_duration_seconds', 180)
    complexity = channel_config.get('complexity_level', 5)

    # Build prompt
    user_message = template.replace('{MECHANICS_JSON}', json.dumps(mechanics, indent=2)) \
                          .replace('{TOPIC}', topic) \
                          .replace('{GENRE}', genre) \
                          .replace('{TONE}', tone) \
                          .replace('{LANGUAGE}', language) \
                          .replace('{DURATION}', str(duration)) \
                          .replace('{NUM_SCENES}', str(num_scenes)) \
                          .replace('{ARCHETYPE_FROM_MECHANICS}', mechanics.get('dominant_archetype', ''))

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


def generate_phase1c_prompts(api_key, narrative, mechanics, image_config, use_cache=True):
    """
    Phase 1c: Image/Audio Prompts Generation

    Args:
        api_key (str): OpenAI API key
        narrative (dict): Narrative JSON from Phase 1b
        mechanics (dict): Mechanics JSON from Phase 1a
        image_config (dict): Image generation config
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

    # Build prompt
    user_message = template.replace('{NARRATIVE_JSON}', json.dumps(narrative, indent=2)) \
                          .replace('{MECHANICS_JSON}', json.dumps(mechanics, indent=2)) \
                          .replace('{IMAGE_PROVIDER}', provider) \
                          .replace('{WIDTH}', str(width)) \
                          .replace('{HEIGHT}', str(height)) \
                          .replace('{STYLE}', style) \
                          .replace('{PROTAGONIST_FROZEN}', mechanics.get('protagonist_frozen', '')) \
                          .replace('{MIRROR_CHARACTER_FROZEN}', mechanics.get('mirror_character_frozen', ''))

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


def run_three_phase_generation(api_key, topic, channel_config, use_cache=True, cache_key_suffix=''):
    """
    Run complete three-phase generation

    Args:
        api_key (str): OpenAI API key
        topic (str): Content topic
        channel_config (dict): Channel configuration
        use_cache (bool): Whether to use cache
        cache_key_suffix (str): Optional cache key suffix (e.g., topic_id)

    Returns:
        dict: Complete content with narrative, mechanics, and prompts
    """
    print("\n" + "="*80)
    print("THREE PHASE STORY ENGINE v4.0")
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
        use_cache=use_cache
    )

    # Phase 1c: Image/Audio Prompts
    image_config = channel_config.get('image_generation', {})
    if isinstance(image_config, str):
        image_config = json.loads(image_config)

    prompts, usage_1c = generate_phase1c_prompts(
        api_key=api_key,
        narrative=narrative,
        mechanics=mechanics,
        image_config=image_config,
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
