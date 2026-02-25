"""
MEGA Configuration Merger

Merges ALL templates (Narrative, Image, CTA, Thumbnail, TTS, SFX, Description)
into a single mega_config for MEGA-GENERATION mode.

Philosophy:
- ONE OpenAI request generates ALL components
- Each template contributes its ai_config (role_definition, core_rules)
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
    narrative_template=None,
    image_template=None,
    cta_template=None,
    thumbnail_template=None,
    tts_template=None,
    sfx_template=None,
    description_template=None,
    story_blueprint=None
):
    """
    Build mega_config for content generation

    UPDATED 2026-02-20: Templates system removed
    All template parameters now optional (default None)
    Returns minimal config - New Story Engine will provide full configuration

    Args:
        channel_config (dict): ChannelConfig from DynamoDB
        All template params: DEPRECATED, kept for backward compatibility

    Returns:
        dict: mega_config with minimal defaults
    """

    # Templates deprecated - use empty dicts
    narrative_template = narrative_template or {}
    image_template = image_template or {}
    cta_template = cta_template or {}
    thumbnail_template = thumbnail_template or {}
    tts_template = tts_template or {}
    sfx_template = sfx_template or {}
    description_template = description_template or {}

    # Extract ai_config from each template (will be empty)
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

        # Model config
        'model': narrative_ai.get('model', 'gpt-4o-mini'),  # WEEK 5: Changed to gpt-4o-mini (16x cheaper)
        'temperature': float(narrative_ai.get('temperature', 0.8)),  # From template (default)
        'max_tokens': int(channel_config.get('max_tokens', 16000)),  # GPT-4o-mini max: 128k tokens

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

        # Story Blueprint (retention template engine)
        'story_blueprint': story_blueprint,

        # Constraints
        'constraints': {
            'target_character_count': int(channel_config.get('target_character_count', 8000)),
            'scene_count_target': int(channel_config.get('scene_count_target', 18)),
            'video_duration_target': int(channel_config.get('video_duration_target', 10))
        }
    }

    return mega_config


def extract_channel_context(channel):
    """
    Extract channel context from ChannelConfig.

    UPDATED 2026-02-20: Added Story Engine parameters
    """
    return {
        'channel_name': channel.get('channel_name', ''),
        'language': channel.get('language', 'en'),
        'genre': channel.get('genre', 'General'),
        'factual_mode': channel.get('factual_mode', 'fictional'),

        # Story Engine - Story Mode
        'story_mode': channel.get('story_mode', 'fiction'),  # fiction / real_events / hybrid

        # Story Engine - Story DNA
        'world_type': channel.get('world_type', 'realistic'),
        'tone': channel.get('tone', 'dark'),
        'psychological_depth': int(channel.get('psychological_depth', 3)),
        'plot_intensity': int(channel.get('plot_intensity', 4)),

        # Story Engine - Character Engine
        'character_mode': channel.get('character_mode', 'auto_generate'),
        'character_archetype': channel.get('character_archetype', 'anti_hero'),
        'enable_internal_conflict': channel.get('enable_internal_conflict') in ['true', True, '1', 1],
        'enable_secret': channel.get('enable_secret') in ['true', True, '1', 1],
        'moral_dilemma_level': int(channel.get('moral_dilemma_level', 3)),

        # Story Engine - Story Structure
        'story_structure_mode': channel.get('story_structure_mode', 'one_shot'),
        'story_structure_template': channel.get('story_structure_template', ''),

        # Story Engine - Logic & Consistency
        'generate_plan_before_writing': channel.get('generate_plan_before_writing') in ['true', True, '1', 1, None],  # Default true
        'auto_consistency_check': channel.get('auto_consistency_check') in ['true', True, '1', 1, None],  # Default true
        'character_motivation_validation': channel.get('character_motivation_validation') in ['true', True, '1', 1, None],  # Default true
        'no_cliches_mode': channel.get('no_cliches_mode') in ['true', True, '1', 1],
        'surprise_injection_level': int(channel.get('surprise_injection_level', 3)),
    }


def extract_narrative_instructions(template, channel):
    """Extract narrative generation instructions"""
    ai_config = template.get('ai_config', {})
    sections = ai_config.get('sections', {})

    return {
        'role_definition': sections.get('role_definition', ''),
        'core_rules': sections.get('core_rules', []),
    }


def extract_image_instructions(template, channel):
    """
    Extract image generation instructions - Simplified version

    NOTE: Templates system removed. This returns minimal defaults.
    New Story Engine will provide image instructions dynamically.
    """
    ai_config = template.get('ai_config', {})
    sections = ai_config.get('sections', {})

    # Return minimal defaults (Templates & Variation Sets removed)
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


def extract_cta_instructions(template, channel):
    """Extract CTA generation instructions"""
    ai_config = template.get('ai_config', {})
    sections = ai_config.get('sections', {})

    # Get CTA config from template
    cta_config = template.get('cta_config', {})

    return {
        'role_definition': sections.get('role_definition', ''),
        'core_rules': sections.get('core_rules', []),

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

        # SSML generation rules
        'scene_variations': scene_variations,

        # Voice selection
        'voice_selection_mode': voice_selection_mode,
        'voice_id': tts_config.get('voice_id', 'Matthew'),  # used if mode=manual
        'available_voices': tts_config.get('available_voices', []),  # used if mode=auto
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

        # SFX/Music libraries (GPT can ONLY use these)
        'sfx_library': sfx_library,
        'music_library': music_library,
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

        # Description settings
        'seo_keywords': channel.get('seo_keywords', '') or channel.get('example_keywords_for_youtube', ''),
    }


def get_mega_output_schema():
    """
    Returns the expected output schema for MEGA-GENERATION

    This is the structure OpenAI should return
    """
    return {
        "type": "object",
        "required": ["story_title", "scenes", "cta_segments", "thumbnail", "description", "metadata"],
        "properties": {
            "story_title": {"type": "string"},
            "selected_voice": {"type": "string", "description": "Voice ID if auto mode, otherwise omitted"},
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
