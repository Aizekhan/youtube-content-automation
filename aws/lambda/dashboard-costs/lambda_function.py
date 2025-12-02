import json
import boto3
from datetime import datetime, timedelta
from decimal import Decimal
from collections import defaultdict

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
cost_table = dynamodb.Table('CostTracking')

def decimal_default(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def lambda_handler(event, context):
    """
    Dashboard Costs API - Multi-Tenant Version
    Endpoints:
    - GET /costs/summary - Get cost summary with breakdown by service

    Filters costs by user_id to ensure data isolation.
    """

    print(f"Event: {json.dumps(event, default=str)}")

    # Extract user_id from event (supports both API Gateway and Function URL formats)
    user_id = None

    # Try Function URL format (body is JSON string)
    if 'body' in event and event['body']:
        try:
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            user_id = body.get('user_id')
            print(f"📦 Extracted user_id from body: {user_id}")
        except json.JSONDecodeError:
            print("⚠️ Failed to parse body as JSON")

    # Try API Gateway format (direct user_id in event)
    if not user_id:
        user_id = event.get('user_id')
        if user_id:
            print(f"📦 Extracted user_id from event: {user_id}")

    # If no user_id provided, check for legacy admin mode
    if not user_id:
        print("WARNING: No user_id provided")
        # For backward compatibility during migration
        raise ValueError('SECURITY ERROR: user_id is required for all requests')
        

    # Parse request
    query_params = event.get('queryStringParameters') or {}
    days = int(query_params.get('days', 7))  # Default: last 7 days

    try:
        # Get costs for the last N days filtered by user_id
        print(f"Getting costs for user {user_id}, last {days} days")
        costs_data = get_costs_summary(user_id, days)

        response = {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
                # CORS headers removed - handled by Lambda Function URL
            },
            'body': json.dumps(costs_data, default=decimal_default)
        }

        return response

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json'
                # CORS headers removed - handled by Lambda Function URL
            },
            'body': json.dumps({
                'error': str(e),
                'type': 'InternalError'
            })
        }

def get_costs_summary(user_id, days=7):
    """
    Get cost summary for the last N days filtered by user_id

    Uses user_id-date-index for efficient queries.
    """

    # Calculate date range (use UTC)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    start_date_str = start_date.strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    print(f"Date range: {start_date_str} to {end_date_str}")
    print(f"Querying costs for user_id: {user_id}")

    # Query costs by date
    daily_costs = defaultdict(lambda: Decimal('0'))
    service_costs = defaultdict(lambda: Decimal('0'))
    operation_costs = defaultdict(lambda: Decimal('0'))
    operation_units = defaultdict(lambda: 0)  # Track units (images, tokens, etc)
    channel_costs = defaultdict(lambda: Decimal('0'))

    total_cost = Decimal('0')
    total_items = 0

    try:
        # Query by user_id and date range using GSI (much more efficient than scan)
        from boto3.dynamodb.conditions import Key

        response = cost_table.query(
            IndexName='user_id-date-index',
            KeyConditionExpression=Key('user_id').eq(user_id) & Key('date').between(start_date_str, end_date_str)
        )

        all_items = response.get('Items', [])

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = cost_table.query(
                IndexName='user_id-date-index',
                KeyConditionExpression=Key('user_id').eq(user_id) & Key('date').between(start_date_str, end_date_str),
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            all_items.extend(response.get('Items', []))

        print(f"Found {len(all_items)} cost records for user {user_id}")

        # Defense in depth - verify user_id matches
        for item in all_items:
            if item.get('user_id') != user_id:
                print(f"WARNING: Security - skipping cost record with wrong user_id")
                continue

            total_items += 1

            cost = Decimal(str(item.get('cost_usd', 0)))
            service = item.get('service', 'Unknown')
            operation = item.get('operation', 'Unknown')
            channel_id = item.get('channel_id', 'Unknown')
            item_date = item.get('date', '')

            daily_costs[item_date] += cost
            service_costs[service] += cost
            operation_costs[operation] += cost
            operation_units[operation] += int(item.get('units', 0))  # Track units
            channel_costs[channel_id] += cost
            total_cost += cost

        print(f"Processed {total_items} items")
        print(f"Total cost: ${float(total_cost):.2f}")

    except Exception as e:
        print(f"ERROR scanning table: {str(e)}")
        import traceback
        traceback.print_exc()

    # Build summary
    summary = {
        'total_usd': float(total_cost),
        'period_days': days,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'total_records': total_items,
        'avg_daily_usd': float(total_cost / days) if days > 0 else 0,
        'forecast_monthly_usd': float(total_cost / days * 30) if days > 0 else 0
    }

    # Convert to list format for charts
    services = [
        {
            'name': service,
            'cost_usd': float(cost),
            'percentage': float((cost / total_cost * 100) if total_cost > 0 else 0)
        }
        for service, cost in sorted(service_costs.items(), key=lambda x: x[1], reverse=True)
    ]

    operations = [
        {
            'name': operation,
            'cost_usd': float(cost),
            'percentage': float((cost / total_cost * 100) if total_cost > 0 else 0),
            'units': operation_units.get(operation, 0)
        }
        for operation, cost in sorted(operation_costs.items(), key=lambda x: x[1], reverse=True)
    ]

    daily_trend = [
        {
            'date': date,
            'cost_usd': float(cost)
        }
        for date, cost in sorted(daily_costs.items())
    ]

    top_channels = [
        {
            'channel_id': channel_id,
            'cost_usd': float(cost),
            'percentage': float((cost / total_cost * 100) if total_cost > 0 else 0)
        }
        for channel_id, cost in sorted(channel_costs.items(), key=lambda x: x[1], reverse=True)[:5]
    ]

    return {
        'summary': summary,
        'services': services,
        'operations': operations,
        'daily_trend': daily_trend,
        'top_channels': top_channels
    }
