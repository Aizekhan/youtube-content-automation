"""
Temporary Lambda: content-query-titles
Returns test topics for testing purposes
"""

def lambda_handler(event, context):
    """Return test topics"""

    return {
        'titles': [
            'The Mystery of the Vanishing Lighthouse',
            'The Cursed Forest of Eternal Night',
            'The Ancient Gods Awakening'
        ],
        'topic_source': 'manual_test',
        'total_available': 3
    }
