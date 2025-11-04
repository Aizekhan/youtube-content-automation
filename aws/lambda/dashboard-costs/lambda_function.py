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
    Dashboard Costs API
    Endpoints:
    - GET /costs/summary - Get cost summary with breakdown by service
    """

    print(f"Event: {json.dumps(event, default=str)}")

    # Parse request
    query_params = event.get('queryStringParameters') or {}
    days = int(query_params.get('days', 7))  # Default: last 7 days

    try:
        # Get costs for the last N days
        costs_data = get_costs_summary(days)

        response = {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
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
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': str(e),
                'type': 'InternalError'
            })
        }

def get_costs_summary(days=7):
    """Get cost summary for the last N days"""

    # Calculate date range (use UTC)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    print(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Current datetime (UTC): {end_date}")

    # Query costs by date
    daily_costs = defaultdict(lambda: Decimal('0'))
    service_costs = defaultdict(lambda: Decimal('0'))
    operation_costs = defaultdict(lambda: Decimal('0'))
    channel_costs = defaultdict(lambda: Decimal('0'))

    total_cost = Decimal('0')
    total_items = 0

    try:
        # Use scan to get all items (simpler and more reliable for now)
        print("Scanning CostTracking table...")
        response = cost_table.scan()
        all_items = response.get('Items', [])

        print(f"Total items in table: {len(all_items)}")

        # Filter by date range
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')

        for item in all_items:
            item_date = item.get('date', '')

            # Check if item is in date range
            if start_date_str <= item_date <= end_date_str:
                total_items += 1

                cost = Decimal(str(item.get('cost_usd', 0)))
                service = item.get('service', 'Unknown')
                operation = item.get('operation', 'Unknown')
                channel_id = item.get('channel_id', 'Unknown')

                daily_costs[item_date] += cost
                service_costs[service] += cost
                operation_costs[operation] += cost
                channel_costs[channel_id] += cost
                total_cost += cost

        print(f"Items in date range: {total_items}")
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
            'percentage': float((cost / total_cost * 100) if total_cost > 0 else 0)
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
