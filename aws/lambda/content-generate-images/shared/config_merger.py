"""
Configuration Merger Utility (Python version)

Merges channel configuration with AI prompt template
based on Lambda function requirements

Philosophy:
- AIPromptConfigs = HOW the AI thinks (reusable templates)
- ChannelConfigs = WHAT the channel is about (identity + constraints)
- Final Config = Template (HOW) + Channel (WHAT)
"""

def merge_configuration(channel_config, prompt_template, lambda_function):
    """
    Merge channel config with prompt template for specific Lambda function

    Args:
        channel_config (dict): Full ChannelConfig record from DynamoDB
        prompt_template (dict): Full AIPromptConfig record from DynamoDB
        lambda_function (str): Lambda function name:
            'content-theme-agent', 'content-narrative', 'content-audio-tts', 'content-save-result'

    Returns:
        dict: Merged configuration for the Lambda function
    """
    # Get sections from template
    sections = prompt_template.get('sections', {})

    # Base config from template (HOW AI thinks)
    merged = {
        # Channel identity (always included)
        'channel_id': channel_config.get('channel_id'),
        'channel_name': channel_config.get('channel_name', 'Unnamed Channel'),
        'channel_theme': channel_config.get('channel_theme'),

        # AI behavior from template
        'role_definition': sections.get('role_definition', ''),
        'core_rules': sections.get('core_rules', []),
        'output_schema': sections.get('output_schema', {}),
        'variation_logic': sections.get('variation_logic', {}),

        # Model parameters from template
        'model': prompt_template.get('model', 'gpt-4o'),
        'temperature': float(prompt_template.get('temperature', 0.8)),
        'max_tokens': int(prompt_template.get('max_tokens', 4000)),
    }

    # Add function-specific fields from channel config
    if lambda_function == 'content-theme-agent':
        return merge_for_theme_agent(merged, channel_config, prompt_template)
    elif lambda_function == 'content-narrative':
        return merge_for_narrative(merged, channel_config, prompt_template)
    elif lambda_function == 'content-audio-tts':
        return merge_for_audio_tts(merged, channel_config, prompt_template)
    elif lambda_function == 'content-save-result':
        return merge_for_save_result(merged, channel_config, prompt_template)
    elif lambda_function == 'content-generate-images':
        return merge_for_image_generation(merged, channel_config, prompt_template)
    else:
        print(f"Warning: Unknown lambda function: {lambda_function}, returning base merge")
        return merged


def merge_for_theme_agent(base, channel, template):
    """Merge config for theme-agent Lambda"""
    sections = template.get('sections', {})

    return {
        **base,
        # Channel identity (WHAT to generate themes about)
        'content_focus': channel.get('content_focus'),
        'meta_theme': channel.get('meta_theme'),
        'genre': channel.get('genre'),
        'tone': channel.get('tone'),
        'target_audience': channel.get('target_audience'),
        'narrative_keywords': channel.get('narrative_keywords'),
        'factual_mode': channel.get('factual_mode'),
        'example_keywords_for_youtube': channel.get('example_keywords_for_youtube'),

        # Template-specific (HOW to generate themes)
        'hook_rules': sections.get('hook_rules', {})
    }


def merge_for_narrative(base, channel, template):
    """Merge config for narrative Lambda"""
    sections = template.get('sections', {})

    return {
        **base,
        # Content identity
        'tone': channel.get('tone'),
        'narration_style': channel.get('narration_style'),
        'emotional_temperature': channel.get('emotional_temperature'),
        'story_structure_pattern': channel.get('story_structure_pattern'),
        'preferred_ending_tone': channel.get('preferred_ending_tone'),
        'factual_mode': channel.get('factual_mode'),

        # Constraints (technical limits)
        'target_character_count': int(channel.get('target_character_count', 8000)),
        'scene_count_target': int(channel.get('scene_count_target', 18)),
        'video_duration_target': int(channel.get('video_duration_target', 10)),
        'narrative_pace': channel.get('narrative_pace', 'medium'),

        # Visual guidance for scene descriptions (also used by image generation)
        'visual_keywords': channel.get('visual_keywords'),
        'visual_atmosphere': channel.get('visual_atmosphere') or channel.get('image_generation', {}).get('image_visual_atmosphere', ''),
        'image_style_variants': channel.get('image_style_variants') or channel.get('image_generation', {}).get('image_style_variants', ''),
        'color_palettes': channel.get('color_palettes') or channel.get('image_generation', {}).get('image_color_palettes', ''),
        'lighting_variants': channel.get('lighting_variants') or channel.get('image_generation', {}).get('image_lighting_variants', ''),
        'composition_variants': channel.get('composition_variants') or channel.get('image_generation', {}).get('image_composition_variants', ''),
        'visual_reference_type': channel.get('visual_reference_type'),

        # Story elements
        'story_setting_variants': channel.get('story_setting_variants'),
        'story_character_types': channel.get('story_character_types'),
        'story_point_of_view_variants': channel.get('story_point_of_view_variants'),

        # Template-specific (with channel override support)
        'hook_rules': sections.get('hook_rules', {}),
        'hook_enabled': channel.get('hook_enabled', sections.get('hook_rules', {}).get('enabled', True)),
        'ssml_settings': sections.get('ssml_settings', {
            'enabled': True,
            'style': 'emotional',
            'default_pace': 'medium',
            'guidelines': 'Add emotional pauses after important moments.\nUse <emphasis level=\'strong\'> on key words.\nSlow down during tense moments.',
            'pause_after_intro': '800ms',
            'pause_dramatic': '1500ms'
        }),

        # Additional metadata
        'content_focus': channel.get('content_focus'),
        'meta_theme': channel.get('meta_theme')
    }


def merge_for_audio_tts(base, channel, template):
    """Merge config for audio-tts Lambda"""
    sections = template.get('sections', {})

    return {
        **base,
        # TTS implementation (from channel)
        'tts_service': channel.get('tts_service', 'aws_polly_neural'),
        'tts_voice_profile': channel.get('tts_voice_profile', 'neutral_male'),
        'tts_mood_variants': channel.get('tts_mood_variants', ''),

        # SSML rules (from template - technical rules for pauses, prosody)
        'ssml_rules': sections.get('ssml_rules', {}),

        # Additional audio guidance
        'recommended_music_variants': channel.get('recommended_music_variants'),
        'music_tempo_variants': channel.get('music_tempo_variants'),

        # Pace affects TTS speed
        'narrative_pace': channel.get('narrative_pace', 'medium')
    }


def merge_for_save_result(base, channel, template):
    """Merge config for save-result Lambda"""
    return {
        **base,
        # Publishing schedule
        'publish_times': channel.get('publish_times'),
        'publish_days': channel.get('publish_days'),
        'daily_upload_count': int(channel.get('daily_upload_count', 1)),
        'timezone': channel.get('timezone', 'Europe/Kyiv'),

        # YouTube metadata
        'subtitles_language': channel.get('subtitles_language') or channel.get('auto_caption_language', 'uk'),
        'example_keywords_for_youtube': channel.get('example_keywords_for_youtube'),
        'seo_keywords': channel.get('seo_keywords'),

        # YouTube settings
        'format': channel.get('format'),
        'monetization_enabled': channel.get('monetization_enabled') in ['true', True],
        'adsense_enabled': channel.get('adsense_enabled') in ['true', True],
        'adsense_account_id': channel.get('adsense_account_id'),
        'license_type': channel.get('license_type') or channel.get('default_license', 'standard'),
        'embedding_allowed': channel.get('embedding_allowed') in ['true', True] or channel.get('allow_embedding') in ['true', True],

        # Channel branding
        'channel_description': channel.get('channel_description'),
        'thumbnail_url': channel.get('thumbnail_url'),
        'banner_url': channel.get('banner_url'),
        'channel_watermark_url': channel.get('channel_watermark_url'),
        'featured_video_id': channel.get('featured_video_id'),

        # Content metadata
        'genre': channel.get('genre'),
        'content_focus': channel.get('content_focus')
    }


def merge_for_image_generation(base, channel, template):
    """Merge config for image-generation Lambda"""
    # Get image generation settings from channel config
    image_gen = channel.get('image_generation', {})

    # Default settings if not configured
    if not image_gen or not image_gen.get('enabled'):
        image_gen = {
            'enabled': False,
            'provider': 'aws-bedrock-sdxl',
            'quality': 'standard',
            'width': 1024,
            'height': 1024,
            'cfg_scale': 7,
            'steps': 50
        }

    return {
        **base,
        # Image generation provider settings
        'image_generation': image_gen,

        # Visual guidance from channel config (for prompt enhancement)
        'visual_keywords': channel.get('visual_keywords', ''),
        'visual_atmosphere': channel.get('visual_atmosphere', '') or image_gen.get('image_visual_atmosphere', ''),
        'image_style_variants': channel.get('image_style_variants', '') or image_gen.get('image_style_variants', ''),
        'color_palettes': channel.get('color_palettes', '') or image_gen.get('image_color_palettes', ''),
        'lighting_variants': channel.get('lighting_variants', '') or image_gen.get('image_lighting_variants', ''),
        'composition_variants': channel.get('composition_variants', '') or image_gen.get('image_composition_variants', ''),

        # Genre for style guidance
        'genre': channel.get('genre', ''),
        'tone': channel.get('tone', ''),
        'content_focus': channel.get('content_focus', '')
    }


def map_voice_profile_to_actual_voice(voice_profile, tts_service):
    """
    Map abstract voice profile to actual TTS voice based on TTS service

    Args:
        voice_profile (str): Abstract profile (e.g., 'authoritative_male')
        tts_service (str): TTS service (e.g., 'aws_polly_neural')

    Returns:
        str: Actual voice name for the service
    """
    voice_mapping = {
        'deep_male': {
            'aws_polly_neural': 'Matthew',
            'aws_polly_standard': 'Matthew',
            'elevenlabs': 'Adam',
            'google_tts': 'en-US-Neural2-D'
        },
        'authoritative_male': {
            'aws_polly_neural': 'Matthew',
            'aws_polly_standard': 'Matthew',
            'elevenlabs': 'Josh',
            'google_tts': 'en-US-Neural2-D'
        },
        'neutral_male': {
            'aws_polly_neural': 'Joey',
            'aws_polly_standard': 'Joey',
            'elevenlabs': 'Sam',
            'google_tts': 'en-US-Neural2-A'
        },
        'young_male': {
            'aws_polly_neural': 'Justin',
            'aws_polly_standard': 'Justin',
            'elevenlabs': 'Antoni',
            'google_tts': 'en-US-Neural2-A'
        },
        'soft_female': {
            'aws_polly_neural': 'Joanna',
            'aws_polly_standard': 'Joanna',
            'elevenlabs': 'Bella',
            'google_tts': 'en-US-Neural2-C'
        },
        'gentle_female': {
            'aws_polly_neural': 'Salli',
            'aws_polly_standard': 'Salli',
            'elevenlabs': 'Rachel',
            'google_tts': 'en-US-Neural2-E'
        },
        'neutral_female': {
            'aws_polly_neural': 'Kendra',
            'aws_polly_standard': 'Kendra',
            'elevenlabs': 'Domi',
            'google_tts': 'en-US-Neural2-F'
        }
    }

    service_mapping = voice_mapping.get(voice_profile)
    if not service_mapping:
        print(f"Warning: Unknown voice profile: {voice_profile}, using default")
        return 'Matthew'  # Default fallback

    actual_voice = service_mapping.get(tts_service)
    if not actual_voice:
        print(f"Warning: Voice profile '{voice_profile}' not mapped for service '{tts_service}', using default")
        return service_mapping.get('aws_polly_neural', 'Matthew')  # Fallback

    return actual_voice


def calculate_character_count_for_duration(duration_minutes, pace='medium'):
    """
    Calculate character count target based on video duration and pace

    Formula based on TTS reading speed:
    - Slow: ~128 chars/minute
    - Medium: ~147 chars/minute
    - Fast: ~165 chars/minute

    Args:
        duration_minutes (int): Target video duration in minutes
        pace (str): 'slow', 'medium', or 'fast'

    Returns:
        int: Recommended character count
    """
    chars_per_minute = {
        'slow': 128,
        'medium': 147,
        'fast': 165
    }

    rate = chars_per_minute.get(pace, chars_per_minute['medium'])
    return round(duration_minutes * rate * 60)  # Convert to seconds
