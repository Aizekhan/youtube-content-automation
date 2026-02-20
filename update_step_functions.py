#!/usr/bin/env python3
"""
Update Step Functions - Remove QueryTitles and ThemeAgent states
Date: 2026-02-20
"""

import json

# Load current definition
with open('sfn_def.json', 'r', encoding='utf-8') as f:
    sfn = json.load(f)

print("[INFO] Loaded Step Functions definition")

# Find Phase1ContentGeneration Iterator
phase1 = sfn['States']['Phase1ContentGeneration']['Iterator']

print(f"[INFO] Current StartAt: {phase1['StartAt']}")
print(f"[INFO] Current states: {list(phase1['States'].keys())}")

# Change StartAt from QueryTitles to CheckFactualMode
phase1['StartAt'] = 'CheckFactualMode'

# Remove QueryTitles state
if 'QueryTitles' in phase1['States']:
    del phase1['States']['QueryTitles']
    print("[DELETE] Removed QueryTitles state")

# Remove ThemeAgent state
if 'ThemeAgent' in phase1['States']:
    del phase1['States']['ThemeAgent']
    print("[DELETE] Removed ThemeAgent state")

# Update MegaNarrativeGenerator to use a placeholder selected_topic
# Since we don't have QueryTitles and ThemeAgent anymore, we need to get topic from somewhere else
# For now, use a placeholder - will be replaced by Topics Queue later

# Find MegaNarrativeGenerator in both SearchWikipediaFacts and SetNoFacts paths
for state_name in ['SearchWikipediaFacts', 'SetNoFacts']:
    if state_name in phase1['States']:
        state = phase1['States'][state_name]
        if 'Next' in state and state['Next'] == 'MegaNarrativeGenerator':
            print(f"[INFO] {state_name} -> MegaNarrativeGenerator (OK)")

# Update MegaNarrativeGenerator Payload to use placeholder
mega_narrative = phase1['States']['MegaNarrativeGenerator']
if 'Parameters' in mega_narrative and 'Payload' in mega_narrative['Parameters']:
    payload = mega_narrative['Parameters']['Payload']

    # Remove reference to themeResult.data.generated_titles[0]
    # Use channel_name as placeholder topic for now
    if 'selected_topic.$' in payload and payload['selected_topic.$'] == '$.themeResult.data.generated_titles[0]':
        # Temporary placeholder until Topics Queue is implemented
        payload['selected_topic.$'] = '$.channel_name'
        print("[UPDATE] MegaNarrativeGenerator: changed selected_topic to use channel_name (placeholder)")

# Update PreparePhase3WithoutImages to remove themeResult reference
if 'PreparePhase3WithoutImages' in sfn['States']['Phase2Parallel']['Branches'][0]['States']:
    prep_state = sfn['States']['Phase2Parallel']['Branches'][0]['States']['PreparePhase3WithoutImages']
    if 'Iterator' in prep_state:
        add_empty = prep_state['Iterator']['States']['AddEmptySceneImages']
        if 'Parameters' in add_empty:
            params = add_empty['Parameters']

            # Remove queryResult and themeResult
            if 'queryResult.$' in params:
                del params['queryResult.$']
                print("[DELETE] Removed queryResult from PreparePhase3WithoutImages")

            if 'themeResult.$' in params:
                del params['themeResult.$']
                print("[DELETE] Removed themeResult from PreparePhase3WithoutImages")

# Update SaveFinalContent to remove themeResult reference
if 'Phase3SaveAndVideo' in sfn['States']:
    save_content = sfn['States']['Phase3SaveAndVideo']['Iterator']['States']['SaveFinalContent']
    if 'Parameters' in save_content and 'Payload' in save_content['Parameters']:
        save_payload = save_content['Parameters']['Payload']

        # Remove selected_topic reference to themeResult
        if 'selected_topic' in save_payload and isinstance(save_payload['selected_topic'], dict):
            if 'title.$' in save_payload['selected_topic'] and save_payload['selected_topic']['title.$'] == '$.themeResult.data.generated_titles[0]':
                # Change to narrativeResult.data.story_title
                save_payload['selected_topic']['title.$'] = '$.narrativeResult.data.story_title'
                print("[UPDATE] SaveFinalContent: changed selected_topic to use story_title")

# Save updated definition
with open('sfn_def.json', 'w', encoding='utf-8') as f:
    json.dump(sfn, f, ensure_ascii=False)

print("\n[SUCCESS] Updated Step Functions definition")
print(f"[INFO] New StartAt: {phase1['StartAt']}")
print(f"[INFO] Remaining states: {list(phase1['States'].keys())}")
