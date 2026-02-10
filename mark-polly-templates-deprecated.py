#!/usr/bin/env python3
"""Mark AWS Polly TTS templates as deprecated in DynamoDB"""

import boto3
import json

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
table = dynamodb.Table('TTSTemplates')

def mark_polly_deprecated():
    """Mark all Polly templates with is_deprecated flag"""

    print("Scanning TTSTemplates for Polly voices...")

    response = table.scan()
    templates = response['Items']

    polly_count = 0
    qwen3_count = 0

    for template in templates:
        template_id = template['template_id']
        provider = template.get('tts_config', {}).get('provider', '')

        # Check if this is a Polly template
        is_polly = (
            provider in ['aws_polly_neural', 'aws_polly_standard', 'polly'] or
            'polly' in template_id.lower() or
            template.get('tts_config', {}).get('engine') in ['neural', 'standard']
        )

        if is_polly:
            polly_count += 1

            # Add deprecation metadata
            table.update_item(
                Key={'template_id': template_id},
                UpdateExpression='SET is_deprecated = :dep, deprecated_reason = :reason, deprecated_date = :date, recommended_alternative = :alt',
                ExpressionAttributeValues={
                    ':dep': True,
                    ':reason': 'Qwen3-TTS is now the primary provider (97% cost savings). Polly remains as fallback only.',
                    ':date': '2026-02-10',
                    ':alt': 'tts_qwen3_ryan_v1'  # Default Qwen3 voice
                }
            )

            print(f"  [DEPRECATED] {template_id}: {template.get('template_name', 'N/A')}")

        elif 'qwen3' in template_id.lower() or provider == 'qwen3_tts':
            qwen3_count += 1

            # Ensure Qwen3 templates are NOT deprecated
            table.update_item(
                Key={'template_id': template_id},
                UpdateExpression='SET is_deprecated = :dep',
                ExpressionAttributeValues={':dep': False}
            )

            print(f"  [ACTIVE] {template_id}: {template.get('template_name', 'N/A')}")

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Polly templates (deprecated): {polly_count}")
    print(f"  Qwen3 templates (active): {qwen3_count}")
    print(f"  Total: {len(templates)}")
    print(f"{'='*60}")

    print("\nNote: Polly templates are still usable but marked as deprecated.")
    print("Users will see them in UI with deprecation notice.")


def show_recommended_migration():
    """Show which Qwen3 voice to use instead of each Polly voice"""

    print("\n" + "="*60)
    print("RECOMMENDED MIGRATION MAPPING")
    print("="*60)

    # Voice migration guide
    migrations = {
        # Male voices
        'Matthew': 'tts_qwen3_ryan_v1 (Deep Male)',
        'Brian': 'tts_qwen3_ryan_v1 (Deep Male)',
        'Joey': 'tts_qwen3_mark_v1 (Neutral Male)',

        # Female voices
        'Joanna': 'tts_qwen3_lily_v1 (Soft Female)',
        'Emma': 'tts_qwen3_emily_v1 (Neutral Female)',
        'Amy': 'tts_qwen3_jane_v1 (Warm Female)',
        'Salli': 'tts_qwen3_emily_v1 (Neutral Female)',
        'Kimberly': 'tts_qwen3_jane_v1 (Warm Female)',
    }

    for polly_voice, qwen3_voice in migrations.items():
        print(f"  {polly_voice:15} → {qwen3_voice}")

    print("\nTo migrate channels:")
    print("  1. Open Channel Configuration UI")
    print("  2. Change 'TTS Template' to recommended Qwen3 voice")
    print("  3. Save - next video will use Qwen3-TTS")
    print("="*60)


if __name__ == '__main__':
    print("="*60)
    print("Mark Polly TTS Templates as Deprecated")
    print("="*60)

    try:
        mark_polly_deprecated()
        show_recommended_migration()

        print("\n[SUCCESS] Polly templates marked as deprecated!")
        print("\nNext steps:")
        print("  1. Update UI to show deprecation warnings")
        print("  2. Monitor channel migrations to Qwen3")
        print("  3. After 90 days, consider removing Polly entirely")

    except Exception as e:
        print(f"\n[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()
