import boto3
import json
from datetime import datetime
from decimal import Decimal
from collections import defaultdict

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
content_table = dynamodb.Table('GeneratedContent')
cost_table = dynamodb.Table('CostTracking')

# OpenAI Pricing (USD)
OPENAI_PRICING = {
    'gpt-4o': {
        'input': 2.50 / 1_000_000,
        'output': 10.00 / 1_000_000,
    },
    'gpt-4o-mini': {
        'input': 0.150 / 1_000_000,
        'output': 0.600 / 1_000_000,
    }
}

# Polly Pricing
POLLY_PRICING = {
    'standard': 4.00 / 1_000_000,
    'neural': 16.00 / 1_000_000,
}

def backfill_costs():
    """Backfill cost data from existing GeneratedContent records"""
    
    # Scan all GeneratedContent
    response = content_table.scan()
    items = response.get('Items', [])
    
    print(f"Found {len(items)} content items")
    
    costs_added = 0
    total_openai_cost = Decimal('0')
    total_polly_cost = Decimal('0')
    
    for item in items:
        channel_id = item.get('channel_id', 'Unknown')
        created_at = item.get('created_at', '')
        content_type = item.get('type', '')
        
        if not created_at:
            continue
            
        # Parse timestamp
        try:
            dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            date_str = dt.strftime('%Y-%m-%d')
            timestamp = created_at
        except:
            continue
        
        content_id = timestamp.replace(':', '').replace('-', '').replace('.', '')[:20]
        
        # Calculate OpenAI cost if narrative generation
        if content_type == 'narrative_generation':
            # Try to get tokens from record or estimate
            tokens_used = item.get('tokens_used')
            
            if tokens_used:
                # Use actual token count
                input_tokens = int(tokens_used * 0.6)  # Estimate 60% input
                output_tokens = int(tokens_used * 0.4)  # 40% output
            else:
                # Estimate from character count
                character_count = item.get('character_count', 0)
                if character_count:
                    # Rough estimate: 1 token ≈ 4 characters
                    estimated_tokens = int(character_count / 4)
                    input_tokens = int(estimated_tokens * 0.3)  # 30% input (prompt)
                    output_tokens = int(estimated_tokens * 0.7)  # 70% output
                else:
                    continue
            
            model = item.get('model', 'gpt-4o')
            model_key = model if model in OPENAI_PRICING else 'gpt-4o'
            pricing = OPENAI_PRICING[model_key]
            
            input_cost = input_tokens * pricing['input']
            output_cost = output_tokens * pricing['output']
            total_cost = Decimal(str(input_cost + output_cost))
            
            # Add to CostTracking
            try:
                cost_table.put_item(
                    Item={
                        'date': date_str,
                        'timestamp': timestamp,
                        'service': 'OpenAI',
                        'operation': 'narrative_generation',
                        'channel_id': channel_id,
                        'content_id': content_id,
                        'cost_usd': total_cost,
                        'units': input_tokens + output_tokens,
                        'details': {
                            'model': model,
                            'input_tokens': input_tokens,
                            'output_tokens': output_tokens,
                            'input_cost_usd': round(input_cost, 6),
                            'output_cost_usd': round(output_cost, 6),
                            'estimated': not bool(tokens_used)
                        }
                    }
                )
                costs_added += 1
                total_openai_cost += total_cost
                print(f"✅ OpenAI cost: ${float(total_cost):.6f} ({date_str})")
            except Exception as e:
                print(f"❌ Failed to add cost: {str(e)}")
        
        # Calculate Polly cost if has audio
        if item.get('has_audio') or item.get('audio_files'):
            # Estimate characters from narrative text
            narrative_text = item.get('narrative_text', '')
            character_count = len(narrative_text) if narrative_text else item.get('character_count', 0)
            
            if character_count:
                # Use neural pricing by default
                cost = Decimal(str(character_count * POLLY_PRICING['neural']))
                
                try:
                    cost_table.put_item(
                        Item={
                            'date': date_str,
                            'timestamp': timestamp + '_polly',
                            'service': 'AWS Polly',
                            'operation': 'audio_generation',
                            'channel_id': channel_id,
                            'content_id': content_id,
                            'cost_usd': cost,
                            'units': character_count,
                            'details': {
                                'characters': character_count,
                                'engine': 'neural',
                                'estimated': True
                            }
                        }
                    )
                    costs_added += 1
                    total_polly_cost += cost
                    print(f"✅ Polly cost: ${float(cost):.6f} ({date_str})")
                except Exception as e:
                    print(f"❌ Failed to add Polly cost: {str(e)}")
    
    print(f"\n{'='*60}")
    print(f"✅ Backfill complete!")
    print(f"Total costs added: {costs_added}")
    print(f"Total OpenAI cost: ${float(total_openai_cost):.2f}")
    print(f"Total Polly cost: ${float(total_polly_cost):.2f}")
    print(f"Grand total: ${float(total_openai_cost + total_polly_cost):.2f}")
    print(f"{'='*60}")

def lambda_handler(event, context):
    """Lambda handler for backfilling costs"""
    backfill_costs()

    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Backfill completed successfully'})
    }
