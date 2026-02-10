#!/usr/bin/env python3
"""Create Auto Voice Selection template with Qwen3-TTS voices"""

import boto3
import json
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
table = dynamodb.Table('TTSTemplates')

# Delete all individual Qwen3 templates
print("Deleting individual Qwen3 templates...")
individual_templates = [
    'tts_qwen3_emily_v1',
    'tts_qwen3_mark_v1',
    'tts_qwen3_lily_v1',
    'tts_qwen3_ryan_v1',
    'tts_qwen3_jane_v1'
]

for template_id in individual_templates:
    try:
        table.delete_item(Key={'template_id': template_id})
        print(f"  Deleted: {template_id}")
    except Exception as e:
        print(f"  Error deleting {template_id}: {e}")

# Create new Auto Voice Selection template with Qwen3 voices
print("\nCreating Auto Voice Selection template with Qwen3 voices...")

template = {
    "template_id": "tts_auto_voice_qwen3",
    "template_name": "Auto Voice Selection - Qwen3-TTS",
    "template_type": "tts",
    "type": "tts",
    "genre": "Universal",
    "description": "Auto voice selection with Qwen3-TTS voices (97% cost savings vs Polly)",
    "is_active": True,
    "is_default": True,
    "enabled": True,
    "created_at": "2026-02-10T05:10:00Z",
    "updated_at": "2026-02-10T05:10:00Z",
    "created_by": "admin",
    "usage_count": 0,
    "version": 1,

    # TTS Configuration
    "tts_config": {
        "service": "qwen3_tts",
        "provider": "qwen3_tts",
        "tts_service": "qwen3_tts",
        "voice_engine": "neural",
        "voice_language": "en-US",
        "voice_selection_mode": "auto",
        "available_voices": [
            {
                "voice_id": "Ryan",
                "gender": "male",
                "style": "deep",
                "description": "Deep, authoritative male voice for serious content",
                "language": "en-US"
            },
            {
                "voice_id": "Mark",
                "gender": "male",
                "style": "neutral",
                "description": "Neutral, professional male voice for documentary-style content",
                "language": "en-US"
            },
            {
                "voice_id": "Lily",
                "gender": "female",
                "style": "soft",
                "description": "Soft, gentle female voice for calm, soothing content",
                "language": "en-US"
            },
            {
                "voice_id": "Emily",
                "gender": "female",
                "style": "neutral",
                "description": "Neutral, clear female voice for informational content",
                "language": "en-US"
            },
            {
                "voice_id": "Jane",
                "gender": "female",
                "style": "warm",
                "description": "Warm, friendly female voice for conversational content",
                "language": "en-US"
            }
        ]
    },

    # TTS Settings
    "tts_settings": {
        "tts_service": "qwen3_tts",
        "language_code": "en-US",
        "output_format": "wav",
        "sample_rate": "24000",
        "prosody_rate": "medium",
        "prosody_pitch": "medium",
        "prosody_volume": "medium",
        "emphasis_level": "moderate",
        "break_strength": "medium",
        "break_sentence": "300ms",
        "break_paragraph": "600ms",
        "break_scene": "1000ms",
        "break_dramatic": "1500ms",
        "narrative_pace": "medium",
        "auto_fix_ssml": True,
        "validate_strict": False,
        "tts_voice_profile": "ryan_male"
    },

    # AI Configuration for voice selection
    "ai_config": {
        "model": "gpt-4o",
        "temperature": Decimal("0.7"),
        "sections": {
            "role_definition": "You are a TTS Director responsible for selecting the best voice for content.",
            "core_rules": [
                "Select ONE voice from available_voices that best fits the channel tone",
                "Consider content type (documentary, storytelling, educational)",
                "Match voice gender/style to channel demographics",
                "Return selected voice_id in output"
            ],
            "output_schema": {
                "selected_voice": "string (voice_id from available_voices)",
                "selection_reason": "string (brief explanation)"
            }
        }
    },

    # Metadata
    "metadata": {
        "cost_per_video": Decimal("0.02"),
        "languages_supported": [
            "English", "Chinese", "Japanese", "Korean",
            "German", "French", "Arabic", "Spanish", "Russian", "Dutch"
        ],
        "features": [
            "auto_voice_selection",
            "multi_language",
            "natural_voice",
            "cost_effective",
            "gpu_accelerated"
        ],
        "category": "open_source",
        "provider_type": "self_hosted_ec2"
    }
}

# Put item to DynamoDB
print(f"\nCreating template: {template['template_id']}")
table.put_item(Item=template)
print(f"[SUCCESS] Template created: {template['template_name']}")

# Verify
print("\nVerifying templates in database...")
response = table.scan()
print(f"\nTotal TTS templates: {len(response['Items'])}")
for item in response['Items']:
    print(f"  - {item['template_id']}: {item.get('template_name', 'N/A')}")

print("\n[DONE] Auto Voice Selection template with Qwen3-TTS created!")
print("\nNow only 1 TTS template exists:")
print("  - Auto Voice Selection - Qwen3-TTS (with 5 voices: Ryan, Mark, Lily, Emily, Jane)")
