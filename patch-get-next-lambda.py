#!/usr/bin/env python3
"""
Patch content-topics-get-next Lambda to support series_metadata structure
"""
import re

lambda_file = 'aws/lambda/content-topics-get-next/lambda_function.py'

with open(lambda_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Patch 1: Line 308 - topic_text field
content = content.replace(
    "            'topic_text': next_topic.get('topic_text'),",
    "            'topic_text': next_topic.get('topic') or next_topic.get('topic_text'),  # Support both field names"
)

# Patch 2: Lines 317-322 - Extract series_metadata before using
old_block = """        # Add series metadata if present
        if next_topic.get('series_id'):
            topic_response['series_id'] = next_topic.get('series_id')
            topic_response['season'] = int(next_topic.get('season', 1))
            if next_topic.get('episode_number'):
                topic_response['episode_number'] = int(next_topic.get('episode_number'))

            # Sprint 4: Load SeriesState and add series_context for Phase 1a/1b
            print(f"\\n  Loading SeriesState for series {next_topic.get('series_id')}...")
            series_state = get_series_state(next_topic.get('series_id'), user_id)"""

new_block = """        # Add series metadata if present (support both old and new structure)
        series_metadata = next_topic.get('series_metadata', {})
        series_id = series_metadata.get('series_id') or next_topic.get('series_id')

        if series_id:
            topic_response['series_id'] = series_id
            topic_response['season'] = int(series_metadata.get('season') or next_topic.get('season', 1))
            episode_number = series_metadata.get('episode_number') or next_topic.get('episode_number')
            if episode_number:
                topic_response['episode_number'] = int(episode_number)

            # Sprint 4: Load SeriesState and add series_context for Phase 1a/1b
            print(f"\\n  Loading SeriesState for series {series_id}...")
            series_state = get_series_state(series_id, user_id)"""

content = content.replace(old_block, new_block)

# Patch 3: Line 282 - Logging series_id
content = content.replace(
    "        if next_topic.get('series_id'):",
    "        series_metadata = next_topic.get('series_metadata', {})\n        series_id_check = series_metadata.get('series_id') or next_topic.get('series_id')\n        if series_id_check:"
)
content = content.replace(
    "            print(f\"    series_id: {next_topic.get('series_id')}\")",
    "            print(f\"    series_id: {series_id_check}\")"
)
content = content.replace(
    "            print(f\"    season: {next_topic.get('season', 1)}\")",
    "            print(f\"    season: {series_metadata.get('season') or next_topic.get('season', 1)}\")"
)
content = content.replace(
    "            print(f\"    episode_number: {next_topic.get('episode_number', 'N/A')}\")",
    "            print(f\"    episode_number: {series_metadata.get('episode_number') or next_topic.get('episode_number', 'N/A')}\")"
)

# Patch 4: Line 337 - get_previous_episodes call
content = content.replace(
    "                    next_topic.get('series_id'),",
    "                    series_id,"
)

# Patch 5: Line 378 - Warning message
content = content.replace(
    "                print(f\"    WARNING: SeriesState not found for {next_topic.get('series_id')}\")",
    "                print(f\"    WARNING: SeriesState not found for {series_id}\")"
)

# Write patched file
with open(lambda_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Patched content-topics-get-next Lambda")
print("Changes:")
print("  1. topic_text: Support both 'topic' and 'topic_text' fields")
print("  2. series_id: Extract from series_metadata.series_id or fallback to series_id")
print("  3. episode_number: Extract from series_metadata.episode_number or fallback")
print("  4. All references updated to use extracted series_id variable")
