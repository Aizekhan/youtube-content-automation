"""
SSML Generator for AWS Polly TTS

Converts plain text narrative to SSML markup based on TTS template configuration.

Architecture: Narrative Lambda generates clean text, TTS Lambda adds SSML markup.
This allows different TTS services with different SSML specifications.
"""

import re


def detect_scene_mood(scene_text, scene_data):
    """
    Detect mood of a scene based on text and metadata

    Returns: 'dramatic', 'action', 'whisper', 'normal'
    """
    # Check if mood is explicitly provided
    if isinstance(scene_data, dict):
        if 'mood' in scene_data:
            return scene_data['mood'].lower()
        if 'scene_visuals' in scene_data and 'mood' in scene_data['scene_visuals']:
            return scene_data['scene_visuals']['mood'].lower()

    # Keyword-based mood detection
    text_lower = scene_text.lower()

    # Dramatic indicators
    dramatic_keywords = ['suddenly', 'horror', 'terror', 'scream', 'death', 'blood', 'fear', 'darkness']
    if any(kw in text_lower for kw in dramatic_keywords):
        return 'dramatic'

    # Action indicators
    action_keywords = ['ran', 'fight', 'battle', 'chase', 'escape', 'attack', 'jumped']
    if any(kw in text_lower for kw in action_keywords):
        return 'action'

    # Whisper indicators
    whisper_keywords = ['whisper', 'quietly', 'softly', 'secret', 'silence']
    if any(kw in text_lower for kw in whisper_keywords):
        return 'whisper'

    # Default to normal
    return 'normal'


def map_mood_to_scene_variation(mood, scene_variations):
    """
    Map detected mood to available scene variation in TTS template

    Args:
        mood: detected mood (string)
        scene_variations: dict from TTS template

    Returns: variation_name (string)
    """
    # Direct match
    if mood in scene_variations:
        return mood

    # Fuzzy matching
    mood_mappings = {
        'mysterious': 'dramatic',
        'suspense': 'dramatic',
        'tense': 'dramatic',
        'intense': 'action',
        'exciting': 'action',
        'fast': 'action',
        'quiet': 'whisper',
        'soft': 'whisper',
        'calm': 'normal',
        'neutral': 'normal'
    }

    mapped_mood = mood_mappings.get(mood, 'normal')

    # Return mapped mood if exists, otherwise 'normal'
    return mapped_mood if mapped_mood in scene_variations else 'normal'


def generate_ssml_for_scene(plain_text, scene_variation):
    """
    Generate SSML markup for a scene based on variation parameters

    Args:
        plain_text: clean text without markup
        scene_variation: dict with SSML parameters (rate, pitch, volume, etc.)

    Returns: SSML-wrapped text
    """
    # Extract parameters
    rate = scene_variation.get('rate', 'medium')
    pitch = scene_variation.get('pitch', '+0%')
    volume = scene_variation.get('volume', 'medium')
    emphasis = scene_variation.get('emphasis', 'moderate')
    pause_before = scene_variation.get('pause_before', '0ms')
    pause_after = scene_variation.get('pause_after', '0ms')

    # Start SSML
    ssml = '<speak>'

    # Add pause before if specified
    if pause_before and pause_before != '0ms':
        ssml += f'<break time="{pause_before}"/>'

    # Add prosody wrapper for rate, pitch, volume
    prosody_attrs = []
    if rate and rate != 'medium':
        prosody_attrs.append(f'rate="{rate}"')
    if pitch and pitch != '+0%':
        prosody_attrs.append(f'pitch="{pitch}"')
    if volume and volume != 'medium':
        prosody_attrs.append(f'volume="{volume}"')

    if prosody_attrs:
        ssml += f'<prosody {" ".join(prosody_attrs)}>'

    # Process text - add emphasis to key words
    processed_text = add_emphasis_to_text(plain_text, emphasis)

    ssml += processed_text

    # Close prosody if opened
    if prosody_attrs:
        ssml += '</prosody>'

    # Add pause after if specified
    if pause_after and pause_after != '0ms':
        ssml += f'<break time="{pause_after}"/>'

    # Close SSML
    ssml += '</speak>'

    return ssml


def add_emphasis_to_text(text, emphasis_level):
    """
    Add <emphasis> tags to important words based on emphasis level

    Args:
        text: plain text
        emphasis_level: 'none', 'moderate', 'strong'

    Returns: text with emphasis tags
    """
    if emphasis_level == 'none' or not emphasis_level:
        return text

    # Words that deserve emphasis (capitalized, quoted, etc.)
    # For now, keep it simple - just return text as-is
    # Can be enhanced with NLP to detect key phrases

    # Add natural pauses at sentence boundaries
    text = re.sub(r'\. ', '. <break time="300ms"/>', text)
    text = re.sub(r'\! ', '! <break time="400ms"/>', text)
    text = re.sub(r'\? ', '? <break time="400ms"/>', text)
    text = re.sub(r', ', ', <break time="200ms"/>', text)

    return text


def generate_ssml_timeline(scenes, tts_template):
    """
    Generate SSML for all scenes in narrative

    Args:
        scenes: list of scene dicts with plain text
        tts_template: TTS template with scene_variations

    Returns: list of scenes with ssml_text added
    """
    scene_variations = tts_template.get('scene_variations', {})

    # If no scene_variations, use default
    if not scene_variations:
        scene_variations = {
            'normal': {
                'rate': 'medium',
                'pitch': '+0%',
                'volume': 'medium',
                'emphasis': 'moderate'
            }
        }

    ssml_scenes = []

    for scene in scenes:
        # Get plain text
        plain_text = scene.get('scene_narration', '') or scene.get('paragraph_text', '')

        if not plain_text:
            print(f"Warning: Scene {scene.get('id', '?')} has no text")
            continue

        # Strip any existing SSML tags (just in case)
        plain_text = strip_ssml_tags(plain_text)

        # Detect mood
        mood = detect_scene_mood(plain_text, scene)

        # Map to scene variation
        variation_name = map_mood_to_scene_variation(mood, scene_variations)
        scene_variation = scene_variations.get(variation_name, scene_variations.get('normal', {}))

        print(f"Scene {scene.get('id', '?')}: mood={mood}, variation={variation_name}")

        # Generate SSML
        ssml_text = generate_ssml_for_scene(plain_text, scene_variation)

        # Create new scene dict
        ssml_scene = {
            'id': scene.get('id', scene.get('scene_number', 0)),
            'scene_number': scene.get('scene_number', scene.get('id', 0)),
            'paragraph_text': plain_text,
            'ssml_text': ssml_text,
            'mood': mood,
            'variation_used': variation_name
        }

        ssml_scenes.append(ssml_scene)

    return ssml_scenes


def strip_ssml_tags(text):
    """Remove any SSML tags from text"""
    text = re.sub(r'<speak>', '', text)
    text = re.sub(r'</speak>', '', text)
    text = re.sub(r'<break[^>]*/?>', '', text)
    text = re.sub(r'<emphasis[^>]*>', '', text)
    text = re.sub(r'</emphasis>', '', text)
    text = re.sub(r'<prosody[^>]*>', '', text)
    text = re.sub(r'</prosody>', '', text)
    text = re.sub(r'<[^>]+>', '', text)  # Remove any other tags
    return text.strip()


# Example usage
if __name__ == '__main__':
    # Test
    test_scenes = [
        {
            'id': 1,
            'scene_narration': 'Long before the sun knew its own name, there was darkness.',
            'scene_visuals': {'mood': 'mysterious'}
        },
        {
            'id': 2,
            'scene_narration': 'Suddenly, a scream pierced the silence! Terror gripped the village.',
            'scene_visuals': {'mood': 'horror'}
        }
    ]

    test_template = {
        'scene_variations': {
            'normal': {'rate': 'medium', 'pitch': '+0%', 'volume': 'medium'},
            'dramatic': {'rate': 'slow', 'pitch': '-10%', 'volume': 'soft', 'pause_before': '500ms', 'pause_after': '800ms'}
        }
    }

    result = generate_ssml_timeline(test_scenes, test_template)

    for scene in result:
        print(f"\nScene {scene['id']}: {scene['mood']} -> {scene['variation_used']}")
        print(f"SSML: {scene['ssml_text'][:100]}...")
