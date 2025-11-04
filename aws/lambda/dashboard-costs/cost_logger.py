import boto3
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
cost_table = dynamodb.Table('CostTracking')

# Pricing (USD) - November 2025
PRICING = {
    'openai': {
        'gpt-4o-input': 2.50 / 1_000_000,  # $2.50 per 1M input tokens
        'gpt-4o-output': 10.00 / 1_000_000,  # $10.00 per 1M output tokens
        'gpt-4o-mini-input': 0.150 / 1_000_000,
        'gpt-4o-mini-output': 0.600 / 1_000_000,
    },
    'polly': {
        'standard': 4.00 / 1_000_000,  # $4 per 1M characters
        'neural': 16.00 / 1_000_000,  # $16 per 1M characters
    },
    's3': {
        'storage': 0.023 / 1024,  # $0.023 per GB per month
        'put': 0.005 / 1000,  # $0.005 per 1000 PUT requests
        'get': 0.0004 / 1000,  # $0.0004 per 1000 GET requests
    },
    'lambda': {
        'requests': 0.20 / 1_000_000,  # $0.20 per 1M requests
        'duration_gb_second': 0.0000166667,  # $0.0000166667 per GB-second
    }
}

def log_openai_cost(channel_id, content_id, model, input_tokens, output_tokens, operation='narrative_generation'):
    """Log OpenAI API cost"""
    
    # Calculate cost
    model_key = model.replace('gpt-', '').replace('-', '-')
    input_cost = input_tokens * PRICING['openai'].get(f'{model_key}-input', PRICING['openai']['gpt-4o-input'])
    output_cost = output_tokens * PRICING['openai'].get(f'{model_key}-output', PRICING['openai']['gpt-4o-output'])
    total_cost = Decimal(str(input_cost + output_cost))
    
    _log_cost(
        service='OpenAI',
        operation=operation,
        channel_id=channel_id,
        content_id=content_id,
        cost_usd=total_cost,
        units=input_tokens + output_tokens,
        details={
            'model': model,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'input_cost': float(input_cost),
            'output_cost': float(output_cost)
        }
    )
    
    return float(total_cost)

def log_polly_cost(channel_id, content_id, characters, engine='neural', operation='audio_generation'):
    """Log AWS Polly cost"""
    
    cost_per_char = PRICING['polly'].get(engine, PRICING['polly']['neural'])
    total_cost = Decimal(str(characters * cost_per_char))
    
    _log_cost(
        service='AWS Polly',
        operation=operation,
        channel_id=channel_id,
        content_id=content_id,
        cost_usd=total_cost,
        units=characters,
        details={
            'characters': characters,
            'engine': engine
        }
    )
    
    return float(total_cost)

def log_s3_cost(channel_id, content_id, size_bytes, operation_type='put', operation='file_storage'):
    """Log S3 storage/operation cost"""
    
    if operation_type == 'storage':
        # Monthly storage cost
        size_gb = size_bytes / (1024 ** 3)
        total_cost = Decimal(str(size_gb * PRICING['s3']['storage']))
    else:
        # PUT/GET request cost
        total_cost = Decimal(str(PRICING['s3'][operation_type]))
    
    _log_cost(
        service='AWS S3',
        operation=operation,
        channel_id=channel_id,
        content_id=content_id,
        cost_usd=total_cost,
        units=size_bytes if operation_type == 'storage' else 1,
        details={
            'size_bytes': size_bytes,
            'operation_type': operation_type
        }
    )
    
    return float(total_cost)

def _log_cost(service, operation, channel_id, content_id, cost_usd, units, details):
    """Internal function to log cost to DynamoDB"""
    
    now = datetime.utcnow()
    date_str = now.strftime('%Y-%m-%d')
    timestamp = now.isoformat() + 'Z'
    
    try:
        cost_table.put_item(
            Item={
                'date': date_str,
                'timestamp': timestamp,
                'service': service,
                'operation': operation,
                'channel_id': channel_id,
                'content_id': content_id,
                'cost_usd': cost_usd,
                'units': units,
                'details': details
            }
        )
        print(f"✅ Logged cost: {service} - ${float(cost_usd):.6f}")
    except Exception as e:
        print(f"❌ Failed to log cost: {str(e)}")
