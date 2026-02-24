"""
Archetype Mechanics System
Defines 8 story archetypes and default archetype pools per genre
"""

# 8 Core Archetypes
ARCHETYPES = {
    'inversion_of_source': {
        'name': 'Inversion of Source',
        'name_uk': 'Інверсія джерела',
        'description': 'What appears to solve the problem IS the problem',
        'description_uk': 'Рішення проблеми стає проблемою',
        'pattern': 'Solution → Dependency → Hidden Cost → Realization',
        'best_for': ['tech_addiction', 'medication', 'productivity_tools', 'lifestyle_solutions']
    },
    'mistaken_identity_of_evil': {
        'name': 'Mistaken Identity of Evil',
        'name_uk': 'Помилкова ідентифікація зла',
        'description': 'The thing protagonist fights IS the thing they need',
        'description_uk': 'Ворог насправді потрібен герою',
        'pattern': 'Enemy Identification → Battle → Self-Recognition → Integration',
        'best_for': ['internal_struggles', 'addiction_recovery', 'accepting_change', 'self_acceptance']
    },
    'cost_of_winning': {
        'name': 'Cost of Winning',
        'name_uk': 'Ціна перемоги',
        'description': 'Victory requires becoming what you opposed',
        'description_uk': 'Успіх перетворює на ворога',
        'pattern': 'Noble Goal → Escalating Means → Moral Compromise → Hollow Victory',
        'best_for': ['competition', 'ambition', 'justice_pursuit', 'success_stories']
    },
    'inherited_sin': {
        'name': 'Inherited Sin',
        'name_uk': 'Успадкований гріх',
        'description': 'Trying to fix past creates identical pattern',
        'description_uk': 'Виправлення минулого повторює помилку',
        'pattern': 'Discovery of Past → Correction Attempt → Repetition → Breaking Cycle',
        'best_for': ['generational_patterns', 'family_dynamics', 'historical_repetition']
    },
    'catalyst_sacrifice': {
        'name': 'Catalyst Sacrifice',
        'name_uk': 'Жертва каталізатора',
        'description': 'The guide must destroy what they\'re teaching',
        'description_uk': 'Вчитель жертвує тим чому навчає',
        'pattern': 'Mentorship → Student Growth → Teacher\'s Paradox → Necessary Loss',
        'best_for': ['teaching', 'mentorship', 'leadership_transition', 'passing_torch']
    },
    'reluctant_transformation': {
        'name': 'Reluctant Transformation',
        'name_uk': 'Небажана трансформація',
        'description': 'The change you resist is the change you are',
        'description_uk': 'Зміна якій опираєшся вже відбулась',
        'pattern': 'Resistance → Forced Proximity → Gradual Adoption → Identity Shift',
        'best_for': ['career_changes', 'relationship_evolution', 'lifestyle_shifts']
    },
    'protector_paradox': {
        'name': 'Protector Paradox',
        'name_uk': 'Парадокс захисника',
        'description': 'Safety creates the danger it prevents',
        'description_uk': 'Безпека створює небезпеку',
        'pattern': 'Protection → Isolation → Vulnerability → Controlled Exposure',
        'best_for': ['parenting', 'security', 'risk_management', 'overprotection']
    },
    'delayed_consequence': {
        'name': 'Delayed Consequence',
        'name_uk': 'Відкладені наслідки',
        'description': 'The price appears long after the choice',
        'description_uk': 'Ціна з\'являється набагато пізніше',
        'pattern': 'Innocent Decision → Gradual Accumulation → Trigger Event → Reckoning',
        'best_for': ['long_term_decisions', 'compound_effects', 'delayed_gratification']
    }
}

# Default Archetype Pools by Genre
DEFAULT_POOLS = {
    'psychology': ['mistaken_identity_of_evil', 'reluctant_transformation', 'inherited_sin'],
    'business': ['cost_of_winning', 'catalyst_sacrifice', 'delayed_consequence'],
    'history': ['inherited_sin', 'cost_of_winning', 'delayed_consequence'],
    'science': ['inversion_of_source', 'delayed_consequence', 'reluctant_transformation'],
    'science fiction': ['inversion_of_source', 'delayed_consequence', 'reluctant_transformation'],  # Alias for sci-fi
    'sci-fi': ['inversion_of_source', 'delayed_consequence', 'reluctant_transformation'],
    'technology': ['inversion_of_source', 'cost_of_winning', 'delayed_consequence'],
    'personal_growth': ['reluctant_transformation', 'mistaken_identity_of_evil', 'protector_paradox'],
    'motivational': ['reluctant_transformation', 'mistaken_identity_of_evil', 'protector_paradox'],  # Alias for motivation
    'motivational / parables': ['reluctant_transformation', 'mistaken_identity_of_evil', 'protector_paradox'],
    'philosophy': ['mistaken_identity_of_evil', 'inherited_sin', 'catalyst_sacrifice'],
    'entertainment': ['cost_of_winning', 'reluctant_transformation', 'catalyst_sacrifice'],
    'education': ['catalyst_sacrifice', 'reluctant_transformation', 'inversion_of_source'],
    'health': ['inversion_of_source', 'mistaken_identity_of_evil', 'protector_paradox'],
    'finance': ['cost_of_winning', 'delayed_consequence', 'inversion_of_source'],
    'relationships': ['reluctant_transformation', 'mistaken_identity_of_evil', 'protector_paradox'],
    'crime': ['cost_of_winning', 'inherited_sin', 'mistaken_identity_of_evil'],
    'mystery': ['mistaken_identity_of_evil', 'delayed_consequence', 'inherited_sin'],
    'horror': ['inversion_of_source', 'protector_paradox', 'delayed_consequence'],
    'general': ['mistaken_identity_of_evil', 'cost_of_winning', 'reluctant_transformation']
}

def get_archetype_pool(genre=None, custom_pool=None):
    """
    Get archetype pool for a channel

    Args:
        genre (str): Channel genre (e.g., 'psychology', 'business')
        custom_pool (list): Custom archetype list if manually configured

    Returns:
        list: List of archetype IDs
    """
    # Priority 1: Custom pool from channel config
    if custom_pool and isinstance(custom_pool, list) and len(custom_pool) > 0:
        return custom_pool

    # Priority 2: Default pool by genre
    if genre:
        genre_lower = genre.lower()
        if genre_lower in DEFAULT_POOLS:
            return DEFAULT_POOLS[genre_lower]

    # Fallback: general pool
    return DEFAULT_POOLS['general']


def get_archetype_info(archetype_id):
    """
    Get archetype information

    Args:
        archetype_id (str): Archetype ID (e.g., 'cost_of_winning')

    Returns:
        dict or None: Archetype info dict
    """
    return ARCHETYPES.get(archetype_id)


def format_archetype_pool_for_prompt(archetype_pool):
    """
    Format archetype pool for Phase 1a prompt

    Args:
        archetype_pool (list): List of archetype IDs

    Returns:
        str: Formatted archetype descriptions for prompt
    """
    formatted = []
    for idx, archetype_id in enumerate(archetype_pool, 1):
        info = ARCHETYPES.get(archetype_id)
        if info:
            formatted.append(f"{idx}. {archetype_id.upper()}\n"
                           f"   {info['description']}\n"
                           f"   Pattern: {info['pattern']}\n")

    return '\n'.join(formatted)


def validate_mechanics_json(mechanics):
    """
    Validate mechanics JSON from Phase 1a

    Args:
        mechanics (dict): Mechanics JSON

    Returns:
        tuple: (is_valid, error_message)
    """
    required_fields = ['dominant_archetype', 'surface_truth', 'hidden_truth',
                      'mirror_character', 'recontextualization_moment',
                      'protagonist_frozen', 'mirror_character_frozen']

    for field in required_fields:
        if field not in mechanics:
            return False, f"Missing required field: {field}"

    # Validate mirror_character structure
    mirror = mechanics.get('mirror_character', {})
    mirror_required = ['role', 'visual_contrast', 'represents', 'key_dialogue']
    for field in mirror_required:
        if field not in mirror:
            return False, f"Missing mirror_character.{field}"

    # Validate archetype exists (normalize to lowercase)
    archetype = mechanics.get('dominant_archetype', '').lower()
    if archetype not in ARCHETYPES:
        return False, f"Invalid archetype: {archetype}"

    # Normalize archetype in mechanics dict
    mechanics['dominant_archetype'] = archetype

    # Also normalize secondary_element if present
    if 'secondary_element' in mechanics and mechanics['secondary_element']:
        mechanics['secondary_element'] = mechanics['secondary_element'].lower()

    return True, None
