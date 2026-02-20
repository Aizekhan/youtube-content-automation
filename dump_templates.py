#!/usr/bin/env python3
"""
Dump All Templates - Extract content from Template tables
Date: 2026-02-20
"""

import boto3
import json

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')

# Template IDs that actually exist in database
templates_to_dump = {
    'NarrativeTemplates': 'narrative_architect_v2',
    'ImageGenerationTemplates': 'image_template_1762366799272_n643wy',
    'CTATemplates': 'cta_template_1762366857242_3zx29p',
    'ThumbnailTemplates': 'thumbnail_universal_v1',
    'TTSTemplates': 'tts_auto_voice_1762573009',
    'SFXTemplates': 'sfx_universal_v1',
    'DescriptionTemplates': 'description_universal_v1'
}

def convert_decimal(obj):
    """Convert Decimal to float for JSON serialization"""
    from decimal import Decimal
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: convert_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimal(item) for item in obj]
    return obj

for table_name, template_id in templates_to_dump.items():
    print(f"\n{'='*60}")
    print(f"[{table_name}] template_id: {template_id}")
    print('='*60)

    try:
        table = dynamodb.Table(table_name)
        response = table.get_item(Key={'template_id': template_id})

        if 'Item' not in response:
            print(f"[ERROR] Template '{template_id}' not found!")
            continue

        item = convert_decimal(response['Item'])

        # Extract key fields
        print(f"\ntemplate_name: {item.get('template_name', 'N/A')}")
        print(f"is_default: {item.get('is_default', False)}")
        print(f"is_active: {item.get('is_active', 0)}")

        # Check ai_config
        ai_config = item.get('ai_config', {})
        if ai_config:
            print(f"\nai_config.model: {ai_config.get('model', 'N/A')}")
            print(f"ai_config.temperature: {ai_config.get('temperature', 'N/A')}")

            sections = ai_config.get('sections', {})
            if sections:
                print(f"\nai_config.sections keys: {list(sections.keys())}")

                role_def = sections.get('role_definition', '')
                if role_def:
                    print(f"\nrole_definition ({len(role_def)} chars):")
                    print(f"  {role_def[:200]}...")

                core_rules = sections.get('core_rules', [])
                if core_rules:
                    print(f"\ncore_rules ({len(core_rules)} rules):")
                    for i, rule in enumerate(core_rules[:3], 1):
                        print(f"  {i}. {rule[:100]}...")

        # Save full template to file
        filename = f"backups/20260220_cleanup/{table_name}_content.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(item, f, indent=2, ensure_ascii=False)
        print(f"\n[SAVED] Full template → {filename}")

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

print(f"\n\n{'='*60}")
print("[SUCCESS] All templates dumped")
print('='*60)
