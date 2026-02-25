#!/usr/bin/env python3
"""
Generate example narrative prompt for testing different AI models
"""

import sys
sys.path.insert(0, 'E:/youtube-content-automation/aws/lambda/content-narrative/shared')

from mega_prompt_builder import build_mega_prompt
from mega_config_merger import merge_mega_configuration
import json

# Simulate BeastCodex channel config
channel_config = {
    'channel_id': 'UCq4jkW2gvAq_qUPcWzSgEig',
    'channel_name': 'BeastCodex',
    'language': 'ru',
    'genre': 'Fantasy / Mythology/Game',
    'visual_style': 'anime style, Japanese animation, vibrant colors, dramatic shading',
    'color_palette': 'vibrant anime colors, cel-shaded',
    'lighting_style': 'anime lighting, dramatic shadows, vibrant highlights',
    'tone': 'Mysterious, adventurous, darkly majestic',
    'target_character_count': '9350',
    'scene_count_target': '9',
    'video_duration_target': '10',
    'max_tokens': '16000',
    'factual_mode': 'False',
    'tts_voice_speaker': 'Emily',
    'tts_service': 'aws_polly_neural'
}

# Build mega config
mega_config = merge_mega_configuration(channel_config)

# Build prompt
selected_topic = "Тэнгу: Крылатый демон-ворон из японских гор"
wikipedia_facts = None

system_msg, user_msg = build_mega_prompt(mega_config, selected_topic, wikipedia_facts)

# Write to file with UTF-8 encoding
with open('narrative-prompt-full.txt', 'w', encoding='utf-8') as f:
    f.write("="*80 + "\n")
    f.write("SYSTEM MESSAGE:\n")
    f.write("="*80 + "\n")
    f.write(system_msg + "\n\n")
    f.write("="*80 + "\n")
    f.write("USER MESSAGE:\n")
    f.write("="*80 + "\n")
    f.write(user_msg + "\n\n")
    f.write("="*80 + "\n")
    f.write(f"\nTotal prompt length: ~{len(system_msg) + len(user_msg)} characters\n")
    f.write(f"Estimated tokens: ~{(len(system_msg) + len(user_msg)) // 4}\n")

print("Prompt saved to: narrative-prompt-full.txt")
