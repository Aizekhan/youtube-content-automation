"""
Temporary Lambda: content-theme-agent
Selects a topic from the provided titles array
"""
import random

def lambda_handler(event, context):
    """Select a topic from titles array"""

    titles = event.get('titles', [])

    if not titles:
        return {
            'error': 'No titles provided',
            'generated_titles': ['Default Test Topic']
        }

    # Select first title for now (can add random selection later)
    selected_title = titles[0] if isinstance(titles, list) else titles

    return {
        'generated_titles': [selected_title],
        'selected_topic': selected_title,
        'total_titles': len(titles) if isinstance(titles, list) else 1
    }
