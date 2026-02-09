"""
MEGA Configuration Merger

Merges ALL templates (Narrative, Image, CTA, Thumbnail, TTS, SFX, Description)
into a single mega_config for MEGA-GENERATION mode.

Philosophy:
- ONE OpenAI request generates ALL components
- Each template contributes its ai_config (role_definition, core_rules, output_schema)
- ChannelConfig provides WHAT (constraints, identity)
- Templates provide HOW (AI instructions for each component)

Usage:
    mega_config = merge_mega_configuration(
        channel_config,
        narrative_template,
        image_template,
        cta_template,
        thumbnail_template,
        tts_template,
        sfx_template,
        description_template
    )
"""

import json
import random

def merge_mega_configuration(
    channel_config,
    narrative_template,
    image_template,
    cta_template,
    thumbnail_template,
    tts_template,
    sfx_template,
    description_template
):
    """
    Merge ALL templates + ChannelConfig into mega_config

    Args:
        channel_config (dict): ChannelConfig from DynamoDB
        narrative_template (dict): NarrativeTemplate
        image_template (dict): ImageTemplate
        cta_template (dict): CTATemplate
        thumbnail_template (dict): ThumbnailTemplate
        tts_template (dict): TTSTemplate
        sfx_template (dict): SFXTemplate
        description_template (dict): DescriptionTemplate

    Returns:
        dict: Merged mega_config with all instructions
    """

    # Extract ai_config from each template
    narrative_ai = narrative_template.get('ai_config', {})
    image_ai = image_template.get('ai_config', {})
    cta_ai = cta_template.get('ai_config', {})
    thumbnail_ai = thumbnail_template.get('ai_config', {})
    tts_ai = tts_template.get('ai_config', {})
    sfx_ai = sfx_template.get('ai_config', {})
    description_ai = description_template.get('ai_config', {})

    # Base config (from narrative template - it's the main generator)
    mega_config = {
        # Channel identity
        'channel_id': channel_config.get('channel_id'),
        'channel_name': channel_config.get('channel_name', 'Unnamed Channel'),
        'channel_theme': channel_config.get('channel_theme'),

        # Model config
        'model': narrative_ai.get('model', 'gpt-4o-mini'),  # From template (default)
        'temperature': float(narrative_ai.get('temperature', 0.8)),  # From template (default)
        'max_tokens': int(channel_config.get('max_tokens', 16000)),  # ONLY from ChannelConfig (GPT-4o max: 16384)

        # Channel context (WHAT to generate about)
        'channel_context': extract_channel_context(channel_config),

        # Template instructions (HOW to generate each component)
        'narrative_instructions': extract_narrative_instructions(narrative_template, channel_config),
        'image_instructions': extract_image_instructions(image_template, channel_config),
        'cta_instructions': extract_cta_instructions(cta_template, channel_config),
        'thumbnail_instructions': extract_thumbnail_instructions(thumbnail_template, channel_config),
        'tts_instructions': extract_tts_instructions(tts_template, channel_config),
        'sfx_instructions': extract_sfx_instructions(sfx_template, channel_config),
        'description_instructions': extract_description_instructions(description_template, channel_config),

        # Constraints
        'constraints': {
            'target_character_count': int(channel_config.get('target_character_count', 5000)),
            'scene_count_target': int(channel_config.get('scene_count_target', 10)),
            'video_duration_target': int(channel_config.get('video_duration_target', 5))
        }
    }

    return mega_config


def extract_channel_context(channel):
    """
    Extract channel context (WHAT) from ChannelConfig

    NEW (2025-11-21): Parses content_focus and narrative_keywords for variety
    """
    import random

    generation_count = int(channel.get('generation_count', 0))

    # Helper: Parse and select variant (same as in extract_image_instructions)
    def pick_content_variant(field_value, seed_offset):
        """Parse comma-separated content variants and select one"""
        if not field_value:
            return ''

        variants = [v.strip() for v in str(field_value).split(',') if v.strip()]

        if not variants:
            return ''
        if len(variants) == 1:
            return variants[0]

        random.seed(int(generation_count) + seed_offset)
        selected = random.choice(variants)

        return selected

    # Parse content_focus if comma-separated
    content_focus_raw = channel.get('content_focus', '')
    content_focus_parsed = pick_content_variant(content_focus_raw, 100)

    # Parse narrative_keywords if comma-separated (optional field)
    narrative_keywords_raw = channel.get('narrative_keywords', '')
    narrative_keywords_parsed = pick_content_variant(narrative_keywords_raw, 101)

    # Log selected content variants
    if ',' in str(content_focus_raw) or ',' in str(narrative_keywords_raw):
        print(f"   📝 Selected content variants:")
        if content_focus_parsed:
            print(f"      Content focus: {content_focus_parsed}")
        if narrative_keywords_parsed:
            print(f"      Narrative keywords: {narrative_keywords_parsed}")

    return {
        'channel_name': channel.get('channel_name', ''),
        'genre': channel.get('genre', 'General'),
        'tone': channel.get('tone', 'Neutral'),
        'factual_mode': channel.get('factual_mode', 'fictional'),
        'target_audience': channel.get('target_audience', ''),
        'content_focus': content_focus_parsed if content_focus_parsed else content_focus_raw,  # ← PARSED!
        'narrative_keywords': narrative_keywords_parsed if narrative_keywords_parsed else narrative_keywords_raw,  # ← NEW + PARSED!
        'meta_theme': channel.get('meta_theme', ''),
        'narration_style': channel.get('narration_style', 'Third-person'),
        'emotional_temperature': channel.get('emotional_temperature', ''),
        'narrative_pace': channel.get('narrative_pace', 'medium'),
    }


def extract_narrative_instructions(template, channel):
    """Extract narrative generation instructions"""
    ai_config = template.get('ai_config', {})
    sections = ai_config.get('sections', {})

    return {
        'role_definition': sections.get('role_definition', ''),
        'core_rules': sections.get('core_rules', []),
        'hook_rules': sections.get('hook_rules', {}),
        'hook_enabled': channel.get('hook_enabled', sections.get('hook_rules', {}).get('enabled', True)),
        'output_schema': sections.get('output_schema', {}),
        'variation_logic': sections.get('variation_logic', {}),
        'story_structure_pattern': channel.get('story_structure_pattern', 'Hook → Build → Twist → Resolution'),
        'preferred_ending_tone': channel.get('preferred_ending_tone', ''),
        'story_setting_variants': channel.get('story_setting_variants', ''),
        'story_character_types': channel.get('story_character_types', ''),
        'story_point_of_view_variants': channel.get('story_point_of_view_variants', '')
    }


def extract_image_instructions(template, channel):
    """
    Extract image generation instructions

    ARCHITECTURE (2025-11-21 UPDATED):
    - General rules (role_definition, core_rules) from ImageTemplate
    - Visual style from Variation Sets with VARIANT PARSING
    - Priority: Variation Set → Template fallback (NO root-level fallback)
    - Variant Parsing: Comma-separated values → random selection per generation
    """
    import random
    ai_config = template.get('ai_config', {})
    sections = ai_config.get('sections', {})

    # VARIATION SETS SUPPORT (UPDATED 2025-11-21)
    variation_sets = channel.get('variation_sets', [])

    # Parse JSON if stored as string (PHP backend compatibility)
    if isinstance(variation_sets, str):
        try:
            variation_sets = json.loads(variation_sets)
            print(f"🔧 Parsed variation_sets from JSON string")
        except json.JSONDecodeError as e:
            print(f"⚠️ Failed to parse variation_sets JSON: {e}")
            variation_sets = []

    # DEEP PARSE: Each item in array might also be a JSON string
    if isinstance(variation_sets, list):
        parsed_sets = []
        for idx, item in enumerate(variation_sets):
            if isinstance(item, str):
                try:
                    parsed_sets.append(json.loads(item))
                    print(f"   🔧 Parsed variation set {idx} from JSON string")
                except json.JSONDecodeError:
                    parsed_sets.append(item)  # Keep as-is if can't parse
            else:
                parsed_sets.append(item)
        variation_sets = parsed_sets

    generation_count = int(channel.get('generation_count', 0))

    # Helper function: Parse comma-separated variants and select one
    def pick_variant(field_value, seed_offset):
        """
        Parse comma-separated variants and randomly select ONE.
        Uses generation_count + offset as seed for deterministic selection.
        """
        if not field_value:
            return ''

        # Split by comma and clean
        variants = [v.strip() for v in str(field_value).split(',') if v.strip()]

        if not variants:
            return ''

        if len(variants) == 1:
            return variants[0]

        # Deterministic random selection
        random.seed(int(generation_count) + seed_offset)
        selected = random.choice(variants)

        return selected

    # Determine visual source
    if variation_sets and len(variation_sets) > 0:
        # Use active variation set
        rotation_mode = channel.get('rotation_mode', 'sequential')

        if rotation_mode == 'sequential':
            active_set_index = generation_count % len(variation_sets)
        elif rotation_mode == 'random':
            random.seed(int(generation_count))
            active_set_index = random.randint(0, len(variation_sets) - 1)
        else:  # manual
            active_set_index = channel.get('manual_set_index', 0)

        if active_set_index >= len(variation_sets):
            active_set_index = 0

        active_set = variation_sets[active_set_index]

        # CRITICAL FIX: Parse active_set if it's still a JSON string
        if isinstance(active_set, str):
            try:
                active_set = json.loads(active_set)
                print(f"   🔧 PARSED active_set from JSON string")
            except json.JSONDecodeError as e:
                print(f"   ⚠️ WARNING: active_set is string but can't parse: {e}")
                active_set = {}  # Fallback to empty dict

        print(f"🔄 VARIATION SETS: Using Set {active_set_index}/{len(variation_sets)-1}: '{active_set.get('set_name', 'Unnamed')}'")
        print(f"   Generation count: {generation_count}, Rotation mode: {rotation_mode}")

        visual_source = active_set
        use_template_fallback = True
    else:
        # No variation sets - use template defaults only (NO root-level fallback)
        print(f"⚠️ NO VARIATION SETS: Using template defaults only")
        visual_source = {}
        use_template_fallback = True

    # Parse and select variants (with template fallback)
    def get_field(field_name, seed_offset, template_default=''):
        value = visual_source.get(field_name)
        if not value and use_template_fallback:
            value = sections.get(field_name, template_default)
        return pick_variant(value, seed_offset) if value else template_default

    # Extract with variant parsing
    selected_composition = get_field('composition_variants', 1, 'Rule of thirds, depth of field')
    selected_lighting = get_field('lighting_variants', 2, 'Dramatic shadows, golden hour')
    selected_colors = get_field('color_palettes', 3, 'Warm tones, cool shadows')
    selected_style = get_field('image_style_variants', 4, 'Cinematic photography, photorealistic')

    # Log selected variants
    print(f"   🎨 Selected variants:")
    print(f"      Composition: {selected_composition}")
    print(f"      Lighting: {selected_lighting}")
    print(f"      Colors: {selected_colors}")
    print(f"      Style: {selected_style}")

    return {
        # General rules from Template
        'role_definition': sections.get('role_definition', ''),
        'core_rules': sections.get('core_rules', []),
        'output_schema': sections.get('output_schema', {}),

        # Visual style with VARIANT PARSING (NEW!)
        'visual_keywords': visual_source.get('visual_keywords') or sections.get('visual_keywords', 'cinematic, atmospheric, detailed'),
        'visual_atmosphere': visual_source.get('visual_atmosphere') or sections.get('visual_atmosphere', 'Mysterious, dramatic, immersive'),
        'image_style_variants': selected_style,  # ← PARSED!
        'color_palettes': selected_colors,  # ← PARSED!
        'lighting_variants': selected_lighting,  # ← PARSED!
        'composition_variants': selected_composition,  # ← PARSED!
        'visual_reference_type': visual_source.get('visual_reference_type') or sections.get('visual_reference_type', 'Cinematic / Photorealistic'),
        'negative_prompt': visual_source.get('negative_prompt') or sections.get('negative_prompt', 'blurry, low quality, distorted, ugly, text, watermark, deformed')
    }


def extract_cta_instructions(template, channel):
    """Extract CTA generation instructions"""
    ai_config = template.get('ai_config', {})
    sections = ai_config.get('sections', {})

    # Get CTA config from template
    cta_config = template.get('cta_config', {})

    return {
        'role_definition': sections.get('role_definition', ''),
        'core_rules': sections.get('core_rules', []),
        'output_schema': sections.get('output_schema', {}),

        # CTA settings - read from channel config (MEGA mode supports scene-based placements)
        'enabled': channel.get('cta_enabled', cta_config.get('enabled', False)),
        'placements': channel.get('cta_placements', cta_config.get('placements', [
            {'relative_to': 'after_scene', 'scene_number': 5, 'type': 'subscribe'},
            {'relative_to': 'before_scene', 'scene_number': 12, 'type': 'like'}
        ])),
        'style': cta_config.get('style', 'creative'),
        'max_duration_seconds': cta_config.get('max_duration_seconds', 12)
    }


def extract_thumbnail_instructions(template, channel):
    """Extract thumbnail generation instructions"""
    ai_config = template.get('ai_config', {})
    sections = ai_config.get('sections', {})

    # Get thumbnail config from template
    thumbnail_config = template.get('thumbnail_config', {})

    return {
        'role_definition': sections.get('role_definition', ''),
        'core_rules': sections.get('core_rules', []),
        'output_schema': sections.get('output_schema', {}),

        # Thumbnail settings
        'aspect_ratio': thumbnail_config.get('aspect_ratio', '16:9'),
        'resolution': thumbnail_config.get('resolution', '1280x720'),
        'text_overlay_enabled': thumbnail_config.get('text_overlay_enabled', True),
        'style': channel.get('image_style_variants', thumbnail_config.get('style', 'cinematic'))
    }


def extract_tts_instructions(template, channel):
    """Extract TTS/SSML generation instructions"""
    ai_config = template.get('ai_config', {})
    sections = ai_config.get('sections', {})

    # Get TTS config
    tts_config = template.get('tts_config', {})
    scene_variations = template.get('scene_variations', {})

    # Voice selection mode
    voice_selection_mode = tts_config.get('voice_selection_mode', 'manual')

    return {
        'role_definition': sections.get('role_definition', ''),
        'core_rules': sections.get('core_rules', []),
        'output_schema': sections.get('output_schema', {}),

        # SSML generation rules
        'scene_variations': scene_variations,

        # Voice selection
        'voice_selection_mode': voice_selection_mode,
        'voice_id': tts_config.get('voice_id', 'Matthew'),  # used if mode=manual
        'available_voices': tts_config.get('available_voices', []),  # used if mode=auto

        # TTS settings (for reference, not used in generation)
        'service': tts_config.get('service', 'aws-polly'),
        'voice_engine': tts_config.get('voice_engine', 'neural'),
        'voice_language': tts_config.get('voice_language', 'en-US')
    }


def extract_sfx_instructions(template, channel):
    """Extract SFX generation instructions"""
    ai_config = template.get('ai_config', {})
    sections = ai_config.get('sections', {})

    # Get SFX libraries
    sfx_library = template.get('sfx_library', {})
    music_library = template.get('music_library', {})

    return {
        'role_definition': sections.get('role_definition', ''),
        'core_rules': sections.get('core_rules', []),
        'output_schema': sections.get('output_schema', {}),

        # SFX/Music libraries (GPT can ONLY use these)
        'sfx_library': sfx_library,
        'music_library': music_library,

        # Timing rules
        'timing_rules': template.get('timing_rules', {})
    }


def extract_description_instructions(template, channel):
    """Extract description generation instructions"""
    ai_config = template.get('ai_config', {})
    sections = ai_config.get('sections', {})

    # Get description config
    description_config = template.get('description_config', {})

    return {
        'role_definition': sections.get('role_definition', ''),
        'core_rules': sections.get('core_rules', []),
        'output_schema': sections.get('output_schema', {}),

        # Description settings
        'include_timestamps': description_config.get('include_timestamps', True),
        'include_hashtags': description_config.get('include_hashtags', True),
        'include_social_links': description_config.get('include_social_links', True),
        'seo_keywords': channel.get('seo_keywords', '') or channel.get('example_keywords_for_youtube', ''),

        # Channel info (for placeholders)
        'channel_description': channel.get('channel_description', ''),
        'channel_watermark_url': channel.get('channel_watermark_url', ''),
        'banner_url': channel.get('banner_url', '')
    }


def get_mega_output_schema():
    """
    Returns the expected output schema for MEGA-GENERATION

    This is the structure OpenAI should return
    """
    return {
        "type": "object",
        "required": ["story_title", "hook", "scenes", "cta_segments", "thumbnail", "description", "metadata"],
        "properties": {
            "story_title": {"type": "string"},
            "selected_voice": {"type": "string", "description": "Voice ID if auto mode, otherwise omitted"},
            "hook": {"type": "string", "description": "Opening hook with SSML markup"},
            "scenes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["scene_number", "scene_title", "scene_narration", "image_prompt", "sfx_cues", "music_track"],
                    "properties": {
                        "scene_number": {"type": "integer"},
                        "scene_title": {"type": "string"},
                        "scene_narration": {"type": "string", "description": "Plain text with SSML tags"},
                        "image_prompt": {"type": "string", "description": "Detailed image generation prompt"},
                        "negative_prompt": {"type": "string"},
                        "sfx_cues": {"type": "array", "items": {"type": "string"}, "description": "SFX filenames from library"},
                        "music_track": {"type": "string", "description": "Music filename from library"},
                        "timing_estimates": {"type": "array", "items": {"type": "number"}, "description": "Timestamps in seconds"},
                        "variation_used": {"type": "string", "enum": ["normal", "dramatic", "action", "whisper"]}
                    }
                }
            },
            "cta_segments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "position": {"type": "string", "description": "Percentage or scene_number"},
                        "cta_text": {"type": "string", "description": "CTA text with SSML"},
                        "type": {"type": "string", "enum": ["subscribe", "like", "comment", "sponsor"]},
                        "style_note": {"type": "string", "description": "How it fits narrative"}
                    }
                }
            },
            "thumbnail": {
                "type": "object",
                "properties": {
                    "thumbnail_prompt": {"type": "string"},
                    "text_overlay": {"type": "string"},
                    "style_notes": {"type": "string"}
                }
            },
            "description": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "hashtags": {"type": "array", "items": {"type": "string"}},
                    "timestamps": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "time": {"type": "string"},
                                "label": {"type": "string"}
                            }
                        }
                    }
                }
            },
            "metadata": {
                "type": "object",
                "properties": {
                    "total_word_count": {"type": "integer"},
                    "total_scenes": {"type": "integer"},
                    "estimated_duration_seconds": {"type": "integer"}
                }
            }
        }
    }
