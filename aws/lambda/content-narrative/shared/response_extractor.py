"""
Response Extractor

Splits MEGA OpenAI response into separate components for parallel processing.

Components extracted:
- narrative_data (text with SSML)
- image_data (image prompts)
- sfx_data (SFX cues + music)
- cta_data (CTA segments)
- thumbnail_data (thumbnail prompt)
- description_data (video description)
- metadata (stats)
"""

import json


def extract_mega_response(openai_response_json, mega_config):
    """
    Split mega OpenAI response into components

    Args:
        openai_response_json (dict): Parsed JSON from OpenAI
        mega_config (dict): Original mega_config (for validation)

    Returns:
        dict: {
            "narrative_data": {...},
            "image_data": {...},
            "sfx_data": {...},
            "cta_data": {...},
            "thumbnail_data": {...},
            "description_data": {...},
            "metadata": {...},
            "validation_errors": [...]
        }
    """

    # Validation errors list
    validation_errors = []

    # Extract each component
    try:
        narrative_data = extract_narrative_data(openai_response_json, mega_config, validation_errors)
        image_data = extract_image_data(openai_response_json, validation_errors)
        sfx_data = extract_sfx_data(openai_response_json, mega_config, validation_errors)
        cta_data = extract_cta_data(openai_response_json, validation_errors)
        thumbnail_data = extract_thumbnail_data(openai_response_json, validation_errors)
        description_data = extract_description_data(openai_response_json, validation_errors)
        metadata = extract_metadata(openai_response_json)

    except Exception as e:
        validation_errors.append(f"Critical error during extraction: {str(e)}")
        # Return empty structures if extraction fails
        return {
            "narrative_data": {},
            "image_data": {},
            "sfx_data": {},
            "cta_data": {},
            "thumbnail_data": {},
            "description_data": {},
            "metadata": {},
            "validation_errors": validation_errors
        }

    return {
        "narrative_data": narrative_data,
        "image_data": image_data,
        "sfx_data": sfx_data,
        "cta_data": cta_data,
        "thumbnail_data": thumbnail_data,
        "description_data": description_data,
        "metadata": metadata,
        "validation_errors": validation_errors
    }


def extract_narrative_data(response, config, errors):
    """Extract narrative text with SSML"""

    scenes = response.get('scenes', [])

    # Extract scenes (plain text, no SSML for Qwen3-TTS)
    narrative_scenes = []
    for scene in scenes:
        scene_narration = scene.get('scene_narration', '')

        narrative_scenes.append({
            "scene_number": scene.get('scene_number'),
            "scene_title": scene.get('scene_title', ''),
            "text_with_ssml": scene_narration,  # Keep field name for backward compatibility
            "variation_used": scene.get('variation_used', 'normal')
        })

    # Voice selection
    selected_voice = response.get('selected_voice')
    tts_inst = config.get('tts_instructions', {})
    voice_mode = tts_inst.get('voice_selection_mode', 'manual')

    # Validate voice selection
    if voice_mode == 'auto':
        if not selected_voice:
            errors.append("Voice selection mode is AUTO but no voice selected")
        else:
            # Check if selected voice is in available list
            available_voices = tts_inst.get('available_voices', [])
            available_ids = [v.get('voice_id') for v in available_voices]
            if selected_voice not in available_ids:
                errors.append(f"Selected voice '{selected_voice}' not in available voices: {available_ids}")
    else:
        # Manual mode - use fixed voice
        selected_voice = tts_inst.get('voice_id', 'Matthew')

    return {
        "story_title": response.get('story_title', ''),
        "selected_voice": selected_voice,
        "hook": response.get('hook', ''),
        "scenes": narrative_scenes
    }


def extract_image_data(response, errors):
    """Extract image prompts for each scene"""

    scenes = response.get('scenes', [])

    image_scenes = []
    for scene in scenes:
        image_prompt = scene.get('image_prompt', '')

        if not image_prompt:
            errors.append(f"Scene {scene.get('scene_number')} missing image_prompt")

        image_scenes.append({
            "scene_number": scene.get('scene_number'),
            "image_prompt": image_prompt,
            "negative_prompt": scene.get('negative_prompt', '')
        })

    return {
        "scenes": image_scenes
    }


def extract_sfx_data(response, config, errors):
    """Extract SFX cues and music tracks"""

    scenes = response.get('scenes', [])
    sfx_inst = config.get('sfx_instructions', {})
    sfx_library = sfx_inst.get('sfx_library', {})
    music_library = sfx_inst.get('music_library', {})

    # Build flat list of all available SFX files
    all_sfx_files = get_all_sfx_files(sfx_library)
    all_music_files = get_all_music_files(music_library)

    sfx_scenes = []
    for scene in scenes:
        sfx_cues = scene.get('sfx_cues', [])
        music_track = scene.get('music_track', '')
        timing_estimates = scene.get('timing_estimates', [])

        # Validate SFX cues (must be from library)
        for cue in sfx_cues:
            if cue not in all_sfx_files:
                errors.append(f"Scene {scene.get('scene_number')}: Invalid SFX cue '{cue}' (not in library)")

        # Validate music track (must be from library)
        if music_track and music_track not in all_music_files:
            errors.append(f"Scene {scene.get('scene_number')}: Invalid music track '{music_track}' (not in library)")

        # Validate max 3 SFX per scene
        if len(sfx_cues) > 3:
            errors.append(f"Scene {scene.get('scene_number')}: Too many SFX cues ({len(sfx_cues)}, max 3)")

        sfx_scenes.append({
            "scene_number": scene.get('scene_number'),
            "sfx_cues": sfx_cues,
            "music_track": music_track,
            "timing_estimates": timing_estimates
        })

    return {
        "scenes": sfx_scenes
    }


def extract_cta_data(response, errors):
    """Extract CTA segments"""

    cta_segments = response.get('cta_segments', [])

    # Validate CTA text has SSML
    for cta in cta_segments:
        cta_text = cta.get('cta_text', '')
        if not cta_text:
            errors.append(f"CTA at position {cta.get('position')} missing cta_text")

    return {
        "cta_segments": cta_segments
    }


def extract_thumbnail_data(response, errors):
    """Extract thumbnail data"""

    thumbnail = response.get('thumbnail', {})

    if not thumbnail.get('thumbnail_prompt'):
        errors.append("Thumbnail missing thumbnail_prompt")

    return thumbnail


def extract_description_data(response, errors):
    """Extract video description data"""

    description = response.get('description', {})

    if not description.get('description'):
        errors.append("Description missing description field")

    return description


def extract_metadata(response):
    """Extract metadata"""

    metadata = response.get('metadata', {})

    # Add scene count if not present
    if 'total_scenes' not in metadata:
        metadata['total_scenes'] = len(response.get('scenes', []))

    return metadata


# Helper functions

def get_all_sfx_files(sfx_library):
    """Flatten SFX library to get all available filenames"""
    all_files = []

    for category, subcategories in sfx_library.items():
        if isinstance(subcategories, dict):
            for subcat, files in subcategories.items():
                if isinstance(files, list):
                    all_files.extend(files)
                elif isinstance(files, str):
                    all_files.append(files)
        elif isinstance(subcategories, list):
            all_files.extend(subcategories)
        elif isinstance(subcategories, str):
            all_files.append(subcategories)

    return all_files


def get_all_music_files(music_library):
    """Flatten music library to get all available filenames"""
    all_files = []

    for genre, moods in music_library.items():
        if isinstance(moods, dict):
            for mood, tracks in moods.items():
                if isinstance(tracks, list):
                    all_files.extend(tracks)
                elif isinstance(tracks, str):
                    all_files.append(tracks)
        elif isinstance(moods, list):
            all_files.extend(moods)
        elif isinstance(moods, str):
            all_files.append(moods)

    return all_files


def validate_ssml_basic(text):
    """
    Basic SSML validation (check for required tags)

    Returns: (is_valid, errors)
    """
    errors = []

    # Check for <speak> tags
    if not text.strip().startswith('<speak>'):
        errors.append("Missing opening <speak> tag")

    if not text.strip().endswith('</speak>'):
        errors.append("Missing closing </speak> tag")

    # Check for unclosed tags (basic)
    open_tags = text.count('<prosody')
    close_tags = text.count('</prosody>')
    if open_tags != close_tags:
        errors.append(f"Mismatched <prosody> tags ({open_tags} open, {close_tags} close)")

    is_valid = len(errors) == 0

    return is_valid, errors


def format_validation_report(validation_errors):
    """Format validation errors for display"""
    if not validation_errors:
        return " All validations passed"

    return f"  {len(validation_errors)} validation errors:\n" + "\n".join([f"  - {err}" for err in validation_errors])
