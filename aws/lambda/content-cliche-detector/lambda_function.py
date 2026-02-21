"""
Content Cliché Detector Lambda
Sprint 3 - Quality Feedback Loop

Rule-based detector for common storytelling clichés.
Returns cliché score (0-100) and detected patterns.
"""

import json
import re

# Cliché patterns database
CLICHE_PATTERNS = {
    "it_was_all_a_dream": {
        "phrases": ["it was all a dream", "woke up suddenly", "just a nightmare", "only dreaming"],
        "weight": 15
    },
    "chosen_one": {
        "phrases": ["chosen one", "prophecy foretold", "destined hero", "only you can save"],
        "weight": 12
    },
    "love_triangle": {
        "phrases": ["torn between two", "choose between", "caught between", "love triangle"],
        "weight": 10
    },
    "evil_twin": {
        "phrases": ["evil twin", "identical twin", "doppelganger", "secret twin"],
        "weight": 8
    },
    "deus_ex_machina": {
        "phrases": ["suddenly appeared", "out of nowhere", "miraculous", "convenient solution"],
        "weight": 15
    },
    "misunderstanding_plot": {
        "phrases": ["if only they talked", "simple misunderstanding", "could have been avoided"],
        "weight": 10
    },
    "damsel_in_distress": {
        "phrases": ["damsel in distress", "helpless woman", "rescued by hero", "needs saving"],
        "weight": 10
    },
    "last_minute_rescue": {
        "phrases": ["nick of time", "just in time", "at the last second", "barely made it"],
        "weight": 8
    },
    "magic_solution": {
        "phrases": ["magical cure", "ancient spell", "mystical power", "enchanted object"],
        "weight": 10
    },
    "amnesia": {
        "phrases": ["lost memory", "can't remember", "amnesia", "forgotten past"],
        "weight": 12
    }
}

# Additional generic patterns
OVERUSED_PHRASES = [
    "little did they know",
    "dark and stormy night",
    "love at first sight",
    "happily ever after",
    "twist of fate",
    "against all odds",
    "time was running out"
]

def detect_cliches(narrative_text):
    """
    Detect clichés in narrative text
    Returns score (0-100) and list of detected patterns
    """
    if not narrative_text:
        return {
            "cliche_score": 0,
            "detected_patterns": [],
            "is_clean": True,
            "overused_phrases": []
        }

    text_lower = narrative_text.lower()
    total_score = 0
    detected = []

    # Check main cliché patterns
    for pattern_name, data in CLICHE_PATTERNS.items():
        for phrase in data["phrases"]:
            if phrase in text_lower:
                total_score += data["weight"]
                detected.append({
                    "pattern": pattern_name,
                    "phrase_matched": phrase,
                    "weight": data["weight"]
                })
                break  # Only count once per pattern

    # Check overused phrases
    overused_found = []
    for phrase in OVERUSED_PHRASES:
        if phrase in text_lower:
            overused_found.append(phrase)
            total_score += 5  # Lower weight for generic phrases

    # Calculate final score (capped at 100)
    final_score = min(total_score, 100)

    return {
        "cliche_score": final_score,
        "detected_patterns": detected,
        "overused_phrases": overused_found,
        "is_clean": final_score < 20,  # Consider clean if score < 20
        "severity": _get_severity(final_score)
    }

def _get_severity(score):
    """Get severity level based on score"""
    if score >= 50:
        return "high"
    elif score >= 30:
        return "medium"
    elif score >= 15:
        return "low"
    else:
        return "minimal"

def calculate_story_metrics(narrative_data):
    """Calculate additional story quality metrics"""
    if isinstance(narrative_data, str):
        text = narrative_data
    elif isinstance(narrative_data, dict):
        # Extract text from scenes if narrative is structured
        scenes = narrative_data.get('scenes', [])
        text = ' '.join([
            scene.get('voiceover', '') + ' ' + scene.get('description', '')
            for scene in scenes
        ])
    else:
        text = str(narrative_data)

    # Basic metrics
    word_count = len(text.split())
    unique_words = len(set(text.lower().split()))

    # Count "twist" indicators
    twist_indicators = ['unexpected', 'surprise', 'suddenly', 'shocking', 'twist', 'reveal']
    twist_count = sum(1 for word in twist_indicators if word in text.lower())

    # Vocabulary richness (Unique words / Total words)
    vocabulary_richness = round(unique_words / word_count, 2) if word_count > 0 else 0

    return {
        "word_count": word_count,
        "unique_words": unique_words,
        "vocabulary_richness": vocabulary_richness,
        "twist_count": twist_count,
        "has_strong_narrative": twist_count >= 2 and vocabulary_richness > 0.5
    }

def lambda_handler(event, context):
    """Main handler for cliché detection"""
    print(f"Event: {json.dumps(event)}")

    try:
        narrative_data = event.get('narrative_data')

        if not narrative_data:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'success': False,
                    'error': 'narrative_data required'
                })
            }

        # Extract text
        if isinstance(narrative_data, dict):
            scenes = narrative_data.get('scenes', [])
            narrative_text = ' '.join([
                scene.get('voiceover', '') + ' ' + scene.get('description', '')
                for scene in scenes
            ])
        else:
            narrative_text = str(narrative_data)

        # Run detection
        cliche_results = detect_cliches(narrative_text)
        story_metrics = calculate_story_metrics(narrative_data)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'cliche_detection': cliche_results,
                'story_metrics': story_metrics,
                'text_length': len(narrative_text)
            })
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'body': json.dumps({
                'success': False,
                'error': f'Cliché detection failed: {str(e)}'
            })
        }
