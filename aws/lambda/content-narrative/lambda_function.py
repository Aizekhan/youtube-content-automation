import json
from datetime import datetime

def lambda_handler(event, context):
    print(f"Narrative Architect - Python Version")
    print(f"Event: {json.dumps(event, ensure_ascii=False)}")
    
    channel_id = event.get('channel_id')
    selected_topic = event.get('selected_topic', 'Default Topic')
    
    # Тестовий наратив
    narrative_content = f"Це історія про '{selected_topic}'. Дуже захоплююча розповідь..."
    
    result = {
        'channel_id': channel_id,
        'selected_topic': selected_topic,
        'narrative_content': narrative_content,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    
    print(f"Returning: {json.dumps(result, ensure_ascii=False)}")
    return result
