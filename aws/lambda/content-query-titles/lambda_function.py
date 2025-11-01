import json
from datetime import datetime

def lambda_handler(event, context):
    print(f"Query Titles - Python Version")
    print(f"Event: {json.dumps(event, ensure_ascii=False)}")
    
    channel_id = event.get('channel_id')
    config_id = event.get('config_id')
    channel_name = event.get('channel_name')
    genre = event.get('genre', 'General')
    
    base_titles = [
        f"Історія про {genre} #1",
        f"Таємниця {genre} #2", 
        f"Загадка {genre} #3"
    ]
    
    result = {
        'channel_id': channel_id,
        'config_id': config_id,
        'channel_name': channel_name,
        'genre': genre,
        'titles': base_titles,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    
    print(f"Returning: {json.dumps(result, ensure_ascii=False)}")
    return result
