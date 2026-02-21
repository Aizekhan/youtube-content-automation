"""
SSML Generator Lambda
Converts plain text narratives to TTS-specific markup (SSML, plain text, etc.)
Applies genre-specific rules and optimizations
"""

import json
import re
from typing import Dict, List, Any


# Genre-specific SSML rules
GENRE_RULES = {
    'Horror': {
        'default_rate': 'slow',
        'default_pitch': 'low',
        'pause_multiplier': 1.5,  # Longer pauses for tension
        'use_whisper': True,
        'variation_effects': {
            'whisper': {'phonation': 'soft', 'rate': 'slow'},
            'dramatic': {'volume': 'loud', 'rate': 'medium'},
            'normal': {'rate': 'medium'}
        }
    },
    'Action': {
        'default_rate': 'fast',
        'default_pitch': 'medium',
        'pause_multiplier': 0.7,  # Shorter pauses for urgency
        'use_whisper': False,
        'variation_effects': {
            'fast': {'rate': 'fast', 'volume': 'loud'},
            'slow': {'rate': 'medium'},
            'normal': {'rate': 'fast'}
        }
    },
    'Mystery': {
        'default_rate': 'medium',
        'default_pitch': 'medium',
        'pause_multiplier': 1.2,
        'use_whisper': False,
        'variation_effects': {
            'whisper': {'phonation': 'soft', 'rate': 'slow'},
            'dramatic': {'volume': 'medium', 'rate': 'slow'},
            'normal': {'rate': 'medium'}
        }
    },
    'Default': {
        'default_rate': 'medium',
        'default_pitch': 'medium',
        'pause_multiplier': 1.0,
        'use_whisper': False,
        'variation_effects': {
            'normal': {'rate': 'medium'}
        }
    }
}


class SSMLGenerator:
    """Base SSML generator for AWS Polly"""

    def __init__(self, genre: str = 'Default'):
        self.genre = genre
        self.rules = GENRE_RULES.get(genre, GENRE_RULES['Default'])

    def generate(self, text: str, variation: str = 'normal') -> str:
        """Generate SSML from plain text"""
        # Remove any existing SSML tags (in case they're present)
        text = self._strip_ssml(text)

        # Add pauses at sentence boundaries
        text = self._add_pauses(text)

        # Apply variation-specific effects
        text = self._apply_variation(text, variation)

        # Wrap in <speak> tag
        return f"<speak>{text}</speak>"

    def _strip_ssml(self, text: str) -> str:
        """Remove any existing SSML tags"""
        # Remove <speak> wrapper
        text = re.sub(r'<speak>|</speak>', '', text)
        # Remove all other tags
        text = re.sub(r'<[^>]+>', '', text)
        return text.strip()

    def _add_pauses(self, text: str) -> str:
        """Add <break> tags at sentence boundaries"""
        pause_time = int(300 * self.rules['pause_multiplier'])

        # Long pause after sentence end (. ! ?)
        text = re.sub(r'([.!?])\s+', f'\\1 <break time="{pause_time}ms"/> ', text)

        # Medium pause after ellipsis
        text = re.sub(r'(\.\.\.)(\s+)', f'\\1 <break time="{int(pause_time * 1.5)}ms"/> ', text)

        # Short pause after comma
        short_pause = int(pause_time * 0.5)
        text = re.sub(r'(,)\s+', f'\\1 <break time="{short_pause}ms"/> ', text)

        return text

    def _apply_variation(self, text: str, variation: str) -> str:
        """Apply genre-specific variation effects"""
        effects = self.rules['variation_effects'].get(variation, {})

        if not effects:
            return text

        # Build prosody attributes
        prosody_attrs = []
        if 'rate' in effects:
            prosody_attrs.append(f'rate="{effects["rate"]}"')
        if 'pitch' in effects:
            prosody_attrs.append(f'pitch="{effects["pitch"]}"')
        if 'volume' in effects:
            prosody_attrs.append(f'volume="{effects["volume"]}"')

        result = text

        # Apply prosody
        if prosody_attrs:
            attrs = ' '.join(prosody_attrs)
            result = f'<prosody {attrs}>{result}</prosody>'

        # Apply phonation effect (whisper) for Polly
        if effects.get('phonation'):
            result = f'<amazon:effect phonation="{effects["phonation"]}">{result}</amazon:effect>'

        return result


class ElevenLabsGenerator:
    """Generator for ElevenLabs (no SSML, just plain text)"""

    def generate(self, text: str, variation: str = 'normal') -> str:
        """ElevenLabs doesn't support SSML, return plain text"""
        # Strip any SSML tags
        text = re.sub(r'<[^>]+>', '', text)
        return text.strip()


class KokoroGenerator:
    """Generator for Kokoro TTS (future implementation)"""

    def generate(self, text: str, variation: str = 'normal') -> str:
        """Kokoro format (placeholder for now)"""
        # TODO: Implement Kokoro-specific markup when we know the format
        return text


def lambda_handler(event, context):
    """
    Generate TTS-specific markup from plain text

    Input:
    {
        "scenes": [
            {
                "scene_number": 1,
                "scene_narration": "Plain text without SSML",
                "variation_used": "whisper"
            }
        ],
        "tts_service": "aws_polly_neural",
        "genre": "Horror"
    }

    Output:
    {
        "scenes": [
            {
                "scene_number": 1,
                "scene_narration_ssml": "<speak>...</speak>",
                "scene_narration_plain": "Plain text",
                "variation_used": "whisper"
            }
        ],
        "ssml_generated": true
    }
    """

    print(f"SSML Generator Lambda - v1.0")
    print(f"Event: {json.dumps(event, default=str)}")

    try:
        scenes = event.get('scenes', [])
        tts_service = event.get('tts_service', 'aws_polly_neural')
        genre = event.get('genre', 'Default')

        if not scenes:
            return {
                'error': 'No scenes provided',
                'scenes': [],
                'ssml_generated': False
            }

        print(f"OK Processing {len(scenes)} scenes for {tts_service} ({genre} genre)")

        # Select generator based on TTS service
        if 'polly' in tts_service.lower():
            generator = SSMLGenerator(genre)
        elif 'elevenlabs' in tts_service.lower():
            generator = ElevenLabsGenerator()
        elif 'kokoro' in tts_service.lower():
            generator = KokoroGenerator()
        else:
            generator = SSMLGenerator(genre)  # Default to Polly

        # Process each scene
        processed_scenes = []
        for scene in scenes:
            plain_text = scene.get('scene_narration', '')
            variation = scene.get('variation_used', 'normal')

            if not plain_text:
                print(f"WARNING  Scene {scene.get('scene_number')} has no narration, skipping")
                processed_scenes.append(scene)
                continue

            # Generate markup
            markup = generator.generate(plain_text, variation)

            # Create new scene with both plain and SSML versions
            processed_scene = scene.copy()
            processed_scene['scene_narration_plain'] = plain_text
            processed_scene['scene_narration_ssml'] = markup

            processed_scenes.append(processed_scene)

            print(f"   OK Scene {scene.get('scene_number')}: {len(plain_text)} chars -> {len(markup)} chars SSML")

        print(f"\nOK Generated SSML for {len(processed_scenes)} scenes")

        return {
            'scenes': processed_scenes,
            'ssml_generated': True,
            'tts_service': tts_service,
            'genre': genre,
            'scene_count': len(processed_scenes)
        }

    except Exception as e:
        print(f"ERROR Error: {str(e)}")
        import traceback
        traceback.print_exc()

        return {
            'error': str(e),
            'scenes': event.get('scenes', []),
            'ssml_generated': False
        }
