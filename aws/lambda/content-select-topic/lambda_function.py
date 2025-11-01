import json
import random
from datetime import datetime

def lambda_handler(event, context):
    print(f"Select Topic - Python Version")
    print(f"Event: {json.dumps(event, ensure_ascii=False)}")
    
    channel_id = event.get('channel_id')
    titles = event.get('generated_titles', [])
    
    if not titles:
        titles = ["Дефолтна тема"]
    
    selected = random.choice(titles)
    
    result = {
        'channel_id': channel_id,
        'selected_topic': selected,
        'all_titles': titles,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    
    print(f"Returning: {json.dumps(result, ensure_ascii=False)}")
    return result
