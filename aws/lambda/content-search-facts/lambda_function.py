"""
content-search-facts Lambda

Searches Wikipedia for facts about a given topic.
Used in factual_mode='factual' channels before narrative generation.

Flow:
  1. Search Wikipedia for the topic
  2. Extract key facts (intro, events, people, dates)
  3. Return structured facts for injection into content-narrative prompt

Fallback: if Wikipedia returns nothing useful → returns empty facts
  (content-narrative will then generate as fictional with a note)
"""

import json
import urllib.request
import urllib.parse
import re

WIKIPEDIA_API = "https://en.wikipedia.org/api/rest_v1"
WIKIPEDIA_SEARCH_API = "https://en.wikipedia.org/w/api.php"

MAX_FACTS_CHARS = 3000  # Max chars to inject into narrative prompt


def lambda_handler(event, context):
    print(f"search-facts v1.0 - Wikipedia mode")
    print(f"Event keys: {list(event.keys())}")

    # Extract topic info
    selected_topic = event.get('selected_topic', {})
    if isinstance(selected_topic, str):
        topic_title = selected_topic
    else:
        topic_title = selected_topic.get('title', '')

    genre = event.get('genre', '')
    language = event.get('language', 'en')

    print(f"Topic: '{topic_title}' | Genre: '{genre}' | Lang: {language}")

    if not topic_title:
        print("WARNING: No topic title provided, returning empty facts")
        return build_result(event, facts=None, source=None)

    # Search Wikipedia (always in English - largest database)
    facts = search_wikipedia(topic_title, genre)

    if facts:
        print(f"Found Wikipedia facts: {len(facts.get('content', ''))} chars")
        return build_result(event, facts=facts, source='wikipedia')
    else:
        print(f"Wikipedia: no useful article found for '{topic_title}'")
        return build_result(event, facts=None, source=None)


def search_wikipedia(topic, genre):
    """
    Search Wikipedia and extract structured facts.
    Returns dict with facts or None if not found.
    """
    # Step 1: Search for the article
    search_query = build_search_query(topic, genre)
    print(f"Wikipedia search query: '{search_query}'")

    article_title = wikipedia_search(search_query)
    if not article_title:
        print(f"No Wikipedia article found for query: '{search_query}'")
        return None

    print(f"Found article: '{article_title}'")

    # Step 2: Get article summary (intro)
    summary = wikipedia_summary(article_title)
    if not summary:
        return None

    # Step 3: Get full article sections for more facts
    sections = wikipedia_sections(article_title)

    # Step 4: Structure the facts
    return structure_facts(topic, article_title, summary, sections)


def build_search_query(topic, genre):
    """Build an optimized search query based on genre."""
    genre_hints = {
        'crime': f"{topic} murder criminal",
        'mystery': f"{topic} mystery legend",
        'mythology': f"{topic} mythology legend myth",
        'history': f"{topic} history historical",
        'biography': f"{topic} biography",
        'horror': f"{topic} horror legend",
        'legend': f"{topic} legend folklore",
    }

    genre_lower = genre.lower() if genre else ''
    for key, query in genre_hints.items():
        if key in genre_lower:
            return query

    return topic  # default: just the topic title


def wikipedia_search(query):
    """Search Wikipedia API and return the best matching article title."""
    params = urllib.parse.urlencode({
        'action': 'query',
        'list': 'search',
        'srsearch': query,
        'srlimit': 3,
        'format': 'json',
        'srnamespace': 0,
    })
    url = f"{WIKIPEDIA_SEARCH_API}?{params}"

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ContentBot/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

        results = data.get('query', {}).get('search', [])
        if not results:
            return None

        # Return best match title
        return results[0]['title']

    except Exception as e:
        print(f"Wikipedia search error: {e}")
        return None


def wikipedia_summary(article_title):
    """Get article summary/intro from Wikipedia REST API."""
    encoded_title = urllib.parse.quote(article_title.replace(' ', '_'))
    url = f"{WIKIPEDIA_API}/page/summary/{encoded_title}"

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ContentBot/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

        extract = data.get('extract', '')
        if len(extract) < 100:
            print(f"Summary too short ({len(extract)} chars), skipping")
            return None

        return {
            'title': data.get('title', article_title),
            'description': data.get('description', ''),
            'extract': extract,
            'url': data.get('content_urls', {}).get('desktop', {}).get('page', '')
        }

    except Exception as e:
        print(f"Wikipedia summary error: {e}")
        return None


def wikipedia_sections(article_title):
    """Get article sections from Wikipedia API for additional facts."""
    params = urllib.parse.urlencode({
        'action': 'query',
        'titles': article_title,
        'prop': 'extracts',
        'exsectionformat': 'plain',
        'exlimit': 1,
        'explaintext': True,
        'exsentences': 30,  # First 30 sentences
        'format': 'json',
    })
    url = f"{WIKIPEDIA_SEARCH_API}?{params}"

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ContentBot/1.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))

        pages = data.get('query', {}).get('pages', {})
        for page_id, page in pages.items():
            if page_id == '-1':
                return ''
            return page.get('extract', '')

    except Exception as e:
        print(f"Wikipedia sections error: {e}")
        return ''


def structure_facts(topic, article_title, summary, full_text):
    """Structure Wikipedia data into clean facts for prompt injection."""

    # Combine summary extract + additional text
    intro = summary.get('extract', '')
    description = summary.get('description', '')
    source_url = summary.get('url', '')

    # Use full_text if available and longer
    main_content = full_text if full_text and len(full_text) > len(intro) else intro

    # Clean up the text
    main_content = clean_wikipedia_text(main_content)

    # Truncate to limit
    if len(main_content) > MAX_FACTS_CHARS:
        main_content = main_content[:MAX_FACTS_CHARS] + '...'

    return {
        'topic': topic,
        'wikipedia_title': article_title,
        'description': description,
        'content': main_content,
        'source_url': source_url,
        'source': 'wikipedia',
        'char_count': len(main_content)
    }


def clean_wikipedia_text(text):
    """Remove Wikipedia artifacts from plain text."""
    if not text:
        return ''

    # Remove section headers that look like "== Section =="
    text = re.sub(r'={2,}[^=]+=+', '', text)

    # Remove multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Remove citation markers like [1], [2]
    text = re.sub(r'\[\d+\]', '', text)

    return text.strip()


def build_result(event, facts, source):
    """Build the result dict, passing through all event data + adding facts."""
    result = dict(event)

    if facts:
        result['wikipedia_facts'] = facts
        result['has_real_facts'] = True
        result['facts_source'] = source
        print(f"Returning facts: {facts['char_count']} chars from {source}")
        print(f"Wikipedia title: {facts['wikipedia_title']}")
    else:
        result['wikipedia_facts'] = None
        result['has_real_facts'] = False
        result['facts_source'] = None
        print("Returning: no facts found, narrative will use fictional mode")

    return result
