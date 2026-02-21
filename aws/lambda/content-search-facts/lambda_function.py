"""
Content Wikipedia Facts Search Lambda
Sprint 2 - Task 2.2
"""

import json
import urllib.request
import urllib.parse
from datetime import datetime


def search_wikipedia(query, limit=5):
    base_url = "https://en.wikipedia.org/w/api.php"
    params = {
        'action': 'query',
        'list': 'search',
        'srsearch': query,
        'srlimit': limit,
        'format': 'json',
        'utf8': 1
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    print(f"Searching Wikipedia: {query}")

    # Wikipedia requires User-Agent header
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'YouTubeContentBot/1.0 (Sprint2; +https://github.com)')

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            if 'query' in data and 'search' in data['query']:
                results = data['query']['search']
                print(f"Found {len(results)} Wikipedia articles")
                return results
            return []
    except Exception as e:
        print(f"Wikipedia API error: {str(e)}")
        return []


def get_page_content(page_id):
    """Get Wikipedia page content by page ID"""
    base_url = "https://en.wikipedia.org/w/api.php"
    params = {
        'action': 'query',
        'pageids': page_id,
        'prop': 'extracts|info',
        'exintro': True,
        'explaintext': True,
        'inprop': 'url',
        'format': 'json',
        'utf8': 1
    }
    url = f"{base_url}?{urllib.parse.urlencode(params)}"

    # Wikipedia requires User-Agent header
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'YouTubeContentBot/1.0 (Sprint2; +https://github.com)')

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            if 'query' in data and 'pages' in data['query']:
                page = data['query']['pages'][str(page_id)]
                return {
                    'title': page.get('title', ''),
                    'extract': page.get('extract', ''),
                    'url': page.get('fullurl', '')
                }
            return None
    except Exception as e:
        print(f"Page content error: {str(e)}")
        return None


def extract_facts_from_text(text, max_facts=15):
    """Extract key facts from Wikipedia text"""
    import re
    if not text:
        return []
    facts = []
    sentences = text.split('. ')
    date_pattern = r'\b(January|February|March|April|May|June|July|August|September|October|November|December|\d{4})\b'
    number_pattern = r'\b\d{1,3}(,\d{3})*(\.\d+)?\b'

    for i, sentence in enumerate(sentences[:30]):
        sentence = sentence.strip()
        if not sentence or len(sentence) < 20:
            continue
        confidence = 'medium'
        category = 'general'
        if re.search(date_pattern, sentence):
            category = 'historical_date'
            confidence = 'high'
        elif re.search(number_pattern, sentence):
            category = 'numerical_detail'
            confidence = 'medium'
        elif i < 3:
            category = 'key_information'
            confidence = 'high'
        fact_text = sentence
        if not fact_text.endswith('.'):
            fact_text += '.'
        facts.append({'fact': fact_text, 'confidence': confidence, 'category': category})
        if len(facts) >= max_facts:
            break
    return facts


def lambda_handler(event, context):
    """Main handler for Wikipedia facts search"""
    print(f"Event: {json.dumps(event)}")
    try:
        topic_text = event.get('topic_text')
        search_depth = event.get('search_depth', 'basic')
        if not topic_text:
            return {'statusCode': 400, 'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}, 'body': json.dumps({'success': False, 'error': 'topic_text required'})}

        search_results = search_wikipedia(topic_text, limit=3 if search_depth == 'basic' else 5)
        if not search_results:
            return {'statusCode': 200, 'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}, 'body': json.dumps({'success': True, 'facts_found': 0, 'key_facts': [], 'references': [], 'fact_check_status': 'no_data_found'})}

        top_result = search_results[0]
        page_content = get_page_content(top_result['pageid'])
        if not page_content:
            return {'statusCode': 200, 'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}, 'body': json.dumps({'success': True, 'facts_found': 0, 'key_facts': [], 'references': [], 'fact_check_status': 'content_unavailable'})}

        max_facts = 10 if search_depth == 'basic' else 20
        raw_facts = extract_facts_from_text(page_content['extract'], max_facts=max_facts)
        key_facts = [{'fact': f['fact'], 'source': f"Wikipedia: {page_content['title']}", 'confidence': f['confidence'], 'category': f['category']} for f in raw_facts]
        references = [page_content['url']]
        if search_depth == 'detailed':
            for result in search_results[1:3]:
                references.append(f"https://en.wikipedia.org/?curid={result['pageid']}")

        response_data = {'success': True, 'facts_found': len(key_facts), 'key_facts': key_facts, 'references': references, 'fact_check_status': 'verified', 'primary_source': page_content['title'], 'search_query': topic_text, 'timestamp': datetime.utcnow().isoformat() + 'Z'}
        return {'statusCode': 200, 'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}, 'body': json.dumps(response_data)}
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'statusCode': 500, 'headers': {'Content-Type': 'application/json', 'Access-Control-Allow-Origin': '*'}, 'body': json.dumps({'success': False, 'error': f'Failed: {str(e)}'})}
