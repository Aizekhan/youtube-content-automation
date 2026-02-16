"""
Lambda: save-final-content
Flexible data extraction for SaveFinalContent - handles ANY context structure
Replaces 34 hardcoded Parameters lines with dynamic extraction
"""

import json


def lambda_handler(event, context):
    """
    Dynamically extract data from context regardless of structure

    Handles both scenarios:
    1. Full pipeline (with images, audio, EC2)
    2. Partial pipeline (no images, no EC2, empty audio)
    """

    # Helper function to safely get nested values
    def safe_get(data, *keys, default=None):
        """Navigate nested dict/list structure safely"""
        result = data
        for key in keys:
            if isinstance(result, dict):
                result = result.get(key, default)
            elif isinstance(result, list) and isinstance(key, int) and len(result) > key:
                result = result[key]
            else:
                return default
            if result is None:
                return default
        return result

    print(f"Input context keys: {list(event.keys())}")

    # Extract narrative data (ALWAYS present)
    narrative = safe_get(event, 'narrativeResult', 'Payload', default={})
    print(f"Narrative keys: {list(narrative.keys())}")

    # Extract audio data (may be in audioResult or at top level)
    audio_files = (
        safe_get(event, 'audioResult', 'Payload', 'audio_files') or
        safe_get(event, 'audio_files') or
        []
    )
    print(f"Audio files count: {len(audio_files)}")

    # Extract CTA audio (may be missing if error)
    cta_segments = safe_get(event, 'ctaAudioResult', 'Payload', 'cta_segments', default=[])
    if safe_get(event, 'ctaAudioError'):
        print("CTA audio failed - using empty segments")
        cta_segments = []

    # Extract channel data
    channel_item = safe_get(event, 'channel_item', default={})
    channel_id = safe_get(channel_item, 'channel_id', default='unknown')
    config_id = safe_get(channel_item, 'config_id', default='unknown')
    genre = safe_get(channel_item, 'genre', default='unknown')

    # Extract theme data
    theme = safe_get(event, 'themeResult', 'Payload', default={})
    selected_title = safe_get(theme, 'generated_titles', 0, default='Untitled')

    # Extract images (may be empty if EC2 failed)
    scene_images = safe_get(event, 'scene_images', default=[])
    print(f"Scene images count: {len(scene_images)}")

    # Build payload for content-save-result
    payload = {
        "channel_id": channel_id,
        "content_id": safe_get(narrative, 'narrative_id', default='unknown'),
        "selected_topic": {
            "title": selected_title
        },
        "narrative_data": {
            "story_title": safe_get(narrative, 'story_title', default=''),
            "scenes": safe_get(narrative, 'scenes', default=[]),
            "model": safe_get(narrative, 'model', default='unknown'),
            "total_word_count": safe_get(narrative, 'character_count', default=0),
            "total_scenes": safe_get(narrative, 'scene_count', default=0)
        },
        "image_data": {},
        "sfx_data": {},
        "cta_data": {
            "cta_segments": cta_segments
        },
        "thumbnail_data": {},
        "description_data": {},
        "metadata": {
            "total_scenes": safe_get(narrative, 'scene_count', default=0),
            "total_word_count": safe_get(narrative, 'character_count', default=0)
        },
        "validation_errors": [],
        "audio_files": audio_files,
        "generated_images": scene_images,
        "config_id": config_id,
        "model": safe_get(narrative, 'model', default='unknown'),
        "genre": genre,
        "user_id": safe_get(event, 'user_id', default='unknown')
    }

    print(f"Built payload for content-save-result:")
    print(f"  - content_id: {payload['content_id']}")
    print(f"  - audio_files: {len(payload['audio_files'])}")
    print(f"  - images: {len(payload['generated_images'])}")
    print(f"  - scenes: {len(payload['narrative_data']['scenes'])}")

    return payload
