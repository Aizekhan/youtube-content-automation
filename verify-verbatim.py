#!/usr/bin/env python3
"""
Verify VERBATIM mechanics in generated content
Checks:
1. Do scenes contain mechanics VERBATIM?
2. Are there fake character mentions (Alexei/Elena/Maya)?
3. Which engine was used (MERGED or OLD)?
"""

import json
import sys

def check_verbatim_mechanics(content_file):
    print("=" * 80)
    print("VERBATIM MECHANICS VERIFICATION")
    print("=" * 80)

    with open(content_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    item = data.get('Item', {})

    # Check if narrative_data exists
    narrative_data = item.get('narrative_data', {}).get('M', {})
    if not narrative_data:
        print("\n[ERROR] No narrative_data found!")
        return

    scenes = narrative_data.get('scenes', {}).get('L', [])

    print(f"\nContent ID: {item.get('content_id', {}).get('S', 'unknown')}")
    print(f"Total Scenes: {len(scenes)}")
    print(f"Topic: {item.get('selected_topic', {}).get('M', {}).get('title', {}).get('S', 'unknown')}")

    # Check for mechanics fields (merged engine has these at root level)
    has_mechanics = False
    mechanics_fields = ['inciting_event', 'crisis_event', 'mirror_confrontation_event',
                       'revelation_event', 'resolution_event']

    # Look for mechanics in narrative_data or at item level
    print("\n" + "=" * 80)
    print("CHECKING FOR MECHANICS FIELDS")
    print("=" * 80)

    for field in mechanics_fields:
        found = False
        value = None

        # Check in narrative_data
        if field in narrative_data:
            found = True
            value = narrative_data[field].get('S', '')
            has_mechanics = True

        # Check at item level
        elif field in item:
            found = True
            value = item[field].get('S', '')
            has_mechanics = True

        status = "[OK]" if found else "[MISSING]"
        print(f"{status} {field:30} {'Found' if found else 'Not found'}")
        if value:
            print(f"      Value: {value[:80]}...")

    if has_mechanics:
        print("\n[OK] MERGED ENGINE detected (mechanics fields present)")
    else:
        print("\n[WARNING] OLD ENGINE detected (no mechanics fields)")

    # Check scene narrations
    print("\n" + "=" * 80)
    print("CHECKING SCENE NARRATIONS")
    print("=" * 80)

    fake_characters = ['alexei', 'elena', 'maya', 'dmitri', 'misha']
    fake_char_mentions = []

    for i, scene in enumerate(scenes):
        scene_data = scene.get('M', {})
        scene_num = scene_data.get('scene_number', {}).get('N', str(i+1))
        narration = scene_data.get('scene_narration', {}).get('S', '')

        # Check for fake characters
        narration_lower = narration.lower()
        for char in fake_characters:
            if char in narration_lower:
                fake_char_mentions.append({
                    'scene': scene_num,
                    'character': char,
                    'narration': narration[:100]
                })

        print(f"\nScene {scene_num}:")
        print(f"  Narration: {narration[:150]}...")

    # Report fake characters
    print("\n" + "=" * 80)
    print("CHECKING FOR FAKE CHARACTERS")
    print("=" * 80)

    if fake_char_mentions:
        print(f"[ERROR] Found {len(fake_char_mentions)} mentions of fake characters:")
        for mention in fake_char_mentions:
            print(f"  Scene {mention['scene']}: {mention['character']}")
            print(f"    {mention['narration']}...")
    else:
        print("[OK] No fake character mentions found!")

    # Final summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Engine: {'MERGED' if has_mechanics else 'OLD'}")
    print(f"Fake Characters: {'FOUND' if fake_char_mentions else 'CLEAN'}")
    print(f"Total Scenes: {len(scenes)}")

    if has_mechanics and not fake_char_mentions:
        print("\n[SUCCESS] Test PASSED! MERGED engine with clean content.")
    elif has_mechanics:
        print("\n[PARTIAL] MERGED engine detected but has fake characters.")
    else:
        print("\n[FAILED] OLD engine used instead of MERGED.")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        check_verbatim_mechanics(sys.argv[1])
    else:
        check_verbatim_mechanics('response-verbatim-test.json')
