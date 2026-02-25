"""
Narrative Parser for Multi-Voice TTS
Парсить narrative text з тегами [NARRATOR], [CHARACTER_ID] і розбиває на репліки з різними голосами
"""
import re

# Qwen3-TTS Voice Mapping
QWEN3_VOICES = {
    'ryan': {'gender': 'M', 'age': 'Young', 'description': 'Young male protagonist'},
    'eric': {'gender': 'M', 'age': 'Middle', 'description': 'Adult male'},
    'dylan': {'gender': 'M', 'age': 'Young', 'description': 'Teen/young male'},
    'aiden': {'gender': 'M', 'age': 'Young', 'description': 'Child/young boy'},
    'uncle_fu': {'gender': 'M', 'age': 'Old', 'description': 'Wise elder/mentor'},
    'serena': {'gender': 'F', 'age': 'Young', 'description': 'Young female'},
    'vivian': {'gender': 'F', 'age': 'Young', 'description': 'Young female (alt)'},
    'ono_anna': {'gender': 'F', 'age': 'Middle', 'description': 'Adult female'},
    'sohee': {'gender': 'F', 'age': 'Young', 'description': 'Teen/young female'}
}


def parse_narrative_for_tts(scene_text, scene_id, default_speaker='ryan', character_voices=None):
    """
    Парсить narrative text з тегами і розбиває на окремі репліки з різними голосами

    Args:
        scene_text (str): Текст сцени з тегами [NARRATOR], [CHARACTER_ID], [break], Scene X:
        scene_id (str): ID сцени
        default_speaker (str): Голос за замовчуванням для narrator
        character_voices (dict): Mapping {character_id: speaker_voice} з SeriesState

    Returns:
        list: [{
            'text': 'Cleaned text',
            'speaker': 'ryan',
            'character_id': 'NARRATOR' or character_id,
            'segment_index': 0
        }]
    """
    if not character_voices:
        character_voices = {}

    # Step 1: Видалити Scene markers
    text = re.sub(r'Scene \d+:[^\n]*\n', '', scene_text)

    # Step 2: Розбити на сегменти по тегам [NARRATOR], [CHARACTER_ID]
    # Pattern: [TAG] text [optional break] [NEXT_TAG]
    segments = []

    # Знайти всі теги і текст між ними
    pattern = r'\[([A-Z_]+)\]\s*(.*?)(?=\[[A-Z_]+\]|$)'
    matches = re.findall(pattern, text, re.DOTALL)

    for idx, (tag, content) in enumerate(matches):
        # Видалити [break] теги і "Break time:" artifacts з content
        cleaned_content = re.sub(r'\[break[^\]]*\]', '', content)
        cleaned_content = re.sub(r'Break time:\s*\d+m?s', '', cleaned_content, flags=re.IGNORECASE)
        # Видалити зайві пробіли і порожні рядки
        cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content)
        cleaned_content = re.sub(r'  +', ' ', cleaned_content)
        cleaned_content = cleaned_content.strip()

        if not cleaned_content:
            continue

        # Визначити speaker
        if tag == 'NARRATOR':
            speaker = default_speaker
            character_id = 'NARRATOR'
        else:
            # Це персонаж — шукаємо голос з character_voices
            speaker = character_voices.get(tag, default_speaker)
            character_id = tag

        segments.append({
            'text': cleaned_content,
            'speaker': speaker,
            'character_id': character_id,
            'segment_index': idx,
            'scene_id': scene_id
        })

    # Якщо не знайшли жодного тегу — весь текст як NARRATOR
    if not segments:
        # Fallback: просто очистити текст від усіх тегів
        cleaned = re.sub(r'\[break[^\]]*\]', '', scene_text)
        cleaned = re.sub(r'Scene \d+:[^\n]*\n', '', cleaned)
        cleaned = re.sub(r'\[[A-Z_]+\]\s*', '', cleaned)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = re.sub(r'  +', ' ', cleaned)
        cleaned = cleaned.strip()

        if cleaned:
            segments.append({
                'text': cleaned,
                'speaker': default_speaker,
                'character_id': 'NARRATOR',
                'segment_index': 0,
                'scene_id': scene_id
            })

    return segments


def get_character_voices_from_series_state(series_state):
    """
    Витягує mapping {character_id: speaker} з SeriesState

    Args:
        series_state (dict): SeriesState з DynamoDB

    Returns:
        dict: {character_id: speaker_voice}
    """
    character_voices = {}
    characters = series_state.get('characters', {})

    for char_id, char_data in characters.items():
        # FIX: Extract speaker from voice_config, not root
        voice_config = char_data.get('voice_config', {})
        speaker = voice_config.get('speaker')
        if speaker:
            # Convert to uppercase for tag matching: yui -> YUI
            character_voices[char_id.upper()] = speaker
            print(f"  Character voice: {char_id.upper()} -> {speaker}")

    return character_voices
