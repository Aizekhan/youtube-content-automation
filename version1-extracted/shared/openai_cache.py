"""
OpenAI Response Caching - Week 5 Cost Optimization
Caches OpenAI API responses to reduce duplicate API calls and save costs
"""

import hashlib
import json
import boto3
from datetime import datetime, timedelta
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
cache_table = dynamodb.Table('OpenAIResponseCache')


def get_cache_key(prompt, model):
    """
    Generate cache key from prompt + model

    Uses MD5 hash to create compact, consistent key

    Args:
        prompt: The full prompt (system + user messages)
        model: Model name (e.g., 'gpt-4o-mini')

    Returns:
        str: MD5 hash as cache key
    """
    cache_string = f"{prompt}:{model}"
    return hashlib.md5(cache_string.encode('utf-8')).hexdigest()


def get_cached_response(prompt, model, max_age_hours=24):
    """
    Check cache for recent response

    Args:
        prompt: The prompt to check
        model: Model name
        max_age_hours: Maximum age of cached response (default: 24 hours)

    Returns:
        dict or None: Cached response if found and not expired, None otherwise
    """
    key = get_cache_key(prompt, model)

    try:
        response = cache_table.get_item(Key={'cache_key': key})

        if 'Item' not in response:
            return None

        item = response['Item']

        # Check age
        cached_at = datetime.fromisoformat(item['cached_at'].replace('Z', '+00:00'))
        age = datetime.now(cached_at.tzinfo) - cached_at

        if age > timedelta(hours=max_age_hours):
            print(f"  Cache expired (age: {age})")
            return None

        print(f" Cache HIT! (age: {age}, saved API call)")
        return item['response']

    except Exception as e:
        print(f"  Cache read error: {e}")
        return None


def cache_response(prompt, model, response, ttl_hours=168):
    """
    Store response in cache

    Args:
        prompt: The prompt that was used
        model: Model name
        response: The OpenAI API response to cache
        ttl_hours: Time-to-live in hours (default: 168 = 7 days)
    """
    key = get_cache_key(prompt, model)
    now = datetime.utcnow()
    ttl_timestamp = int((now + timedelta(hours=ttl_hours)).timestamp())

    try:
        # Extract relevant parts from response for caching
        if isinstance(response, dict):
            # Cache the full response
            cached_data = response
        else:
            # If it's a string, wrap it
            cached_data = {'content': response}

        cache_table.put_item(Item={
            'cache_key': key,
            'prompt_hash': key,  # For debugging
            'model': model,
            'response': cached_data,
            'cached_at': now.isoformat() + 'Z',
            'ttl': ttl_timestamp  # DynamoDB will auto-delete after this
        })

        print(f" Cached response (key: {key[:8]}..., TTL: {ttl_hours}h)")

    except Exception as e:
        # Cache errors shouldn't break the main flow
        print(f"  Cache write error (non-fatal): {e}")


def clear_cache(model=None):
    """
    Clear cache entries (for testing/debugging)

    Args:
        model: If specified, only clear cache for this model
    """
    try:
        if model:
            # Scan for specific model
            response = cache_table.scan(
                FilterExpression='#m = :model',
                ExpressionAttributeNames={'#m': 'model'},
                ExpressionAttributeValues={':model': model}
            )
        else:
            # Scan all
            response = cache_table.scan()

        items = response.get('Items', [])

        for item in items:
            cache_table.delete_item(Key={'cache_key': item['cache_key']})

        print(f"  Cleared {len(items)} cache entries")
        return len(items)

    except Exception as e:
        print(f"  Cache clear error: {e}")
        return 0


def get_cache_stats():
    """
    Get cache statistics (for monitoring)

    Returns:
        dict: Cache statistics
    """
    try:
        response = cache_table.scan(
            ProjectionExpression='cache_key,model,cached_at'
        )

        items = response['Items']

        # Count by model
        model_counts = {}
        for item in items:
            model = item.get('model', 'unknown')
            model_counts[model] = model_counts.get(model, 0) + 1

        # Count by age
        now = datetime.utcnow()
        age_buckets = {
            'less_than_1h': 0,
            '1h_to_6h': 0,
            '6h_to_24h': 0,
            'more_than_24h': 0
        }

        for item in items:
            cached_at = datetime.fromisoformat(item['cached_at'].replace('Z', '+00:00'))
            age_hours = (now.replace(tzinfo=cached_at.tzinfo) - cached_at).total_seconds() / 3600

            if age_hours < 1:
                age_buckets['less_than_1h'] += 1
            elif age_hours < 6:
                age_buckets['1h_to_6h'] += 1
            elif age_hours < 24:
                age_buckets['6h_to_24h'] += 1
            else:
                age_buckets['more_than_24h'] += 1

        return {
            'total_entries': len(items),
            'by_model': model_counts,
            'by_age': age_buckets
        }

    except Exception as e:
        print(f"  Cache stats error: {e}")
        return {'error': str(e)}
