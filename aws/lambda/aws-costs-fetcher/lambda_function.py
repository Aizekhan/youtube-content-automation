"""
AWS Cost Explorer Integration Lambda
Fetches real AWS costs from Cost Explorer API

Features:
- Daily cost breakdown by service
- Monthly totals
- Cost trends
- Caches results for 1 hour

Usage:
- Called daily by CloudWatch Event
- Can be called manually for real-time data
- Results cached in DynamoDB
"""

import json
import boto3
from datetime import datetime, timedelta
from decimal import Decimal

# Cost Explorer only available in us-east-1
ce = boto3.client('ce', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
cache_table = dynamodb.Table('AWSCostCache')

def decimal_default(obj):
    """JSON serializer for Decimal objects"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def lambda_handler(event, context):
    """
    Fetch AWS costs from Cost Explorer API

    Query Parameters:
    - days: Number of days to fetch (default: 7, max: 30)
    - force_refresh: Force refresh cache (default: false)

    Returns:
    - daily_costs: List of daily costs by service
    - monthly_total: Current month total
    - summary: Aggregated summary
    """

    print(f"Event: {json.dumps(event, default=str)}")

    # Parse parameters
    query_params = event.get('queryStringParameters') or {}
    days = min(int(query_params.get('days', 7)), 30)  # Max 30 days
    force_refresh = query_params.get('force_refresh', 'false').lower() == 'true'

    try:
        # Check cache first (unless force refresh)
        if not force_refresh:
            cached_data = get_cached_costs()
            if cached_data:
                print("Returning cached data")
                return {
                    'statusCode': 200,
                    'headers': {'Content-Type': 'application/json'},
                    'body': json.dumps({
                        **cached_data,
                        'cached': True
                    }, default=decimal_default)
                }

        # Fetch fresh data from Cost Explorer
        print(f"Fetching fresh data for last {days} days")
        costs_data = fetch_costs_from_explorer(days)

        # Cache the results
        cache_costs(costs_data)

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                **costs_data,
                'cached': False
            }, default=decimal_default)
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'error': str(e),
                'type': 'CostExplorerError'
            })
        }

def fetch_costs_from_explorer(days=7):
    """
    Fetch costs from AWS Cost Explorer API

    Returns structured cost data:
    - daily_breakdown: Costs per day per service
    - service_totals: Total cost per service
    - monthly_total: Current month total
    - summary: High-level metrics
    """

    # Calculate date ranges
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    # Also get month-to-date
    month_start = datetime.now().replace(day=1).date()

    print(f"Fetching costs from {start_date} to {end_date}")

    # Fetch daily costs by service
    daily_response = ce.get_cost_and_usage(
        TimePeriod={
            'Start': str(start_date),
            'End': str(end_date)
        },
        Granularity='DAILY',
        Metrics=['UnblendedCost'],
        GroupBy=[
            {'Type': 'DIMENSION', 'Key': 'SERVICE'}
        ]
    )

    # Fetch month-to-date total
    monthly_response = ce.get_cost_and_usage(
        TimePeriod={
            'Start': str(month_start),
            'End': str(end_date)
        },
        Granularity='MONTHLY',
        Metrics=['UnblendedCost']
    )

    # Parse daily data
    daily_breakdown = []
    service_totals = {}

    for result in daily_response['ResultsByTime']:
        date_str = result['TimePeriod']['Start']

        daily_services = []
        for group in result['Groups']:
            service_name = group['Keys'][0]
            cost = float(group['Metrics']['UnblendedCost']['Amount'])

            if cost > 0.0001:  # Filter out tiny costs
                daily_services.append({
                    'service': service_name,
                    'cost_usd': cost
                })

                # Aggregate service totals
                if service_name not in service_totals:
                    service_totals[service_name] = 0
                service_totals[service_name] += cost

        if daily_services:
            daily_breakdown.append({
                'date': date_str,
                'services': daily_services,
                'total': sum(s['cost_usd'] for s in daily_services)
            })

    # Parse monthly total
    month_total = 0
    if monthly_response['ResultsByTime']:
        month_total = float(
            monthly_response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount']
        )

    # Calculate summary metrics
    period_total = sum(day['total'] for day in daily_breakdown)
    avg_daily = period_total / days if days > 0 else 0

    # Build structured response
    response_data = {
        'daily_breakdown': daily_breakdown,
        'service_totals': [
            {
                'service': service,
                'cost_usd': cost,
                'percentage': (cost / period_total * 100) if period_total > 0 else 0
            }
            for service, cost in sorted(service_totals.items(), key=lambda x: x[1], reverse=True)
        ],
        'summary': {
            'period_total_usd': period_total,
            'period_days': days,
            'avg_daily_usd': avg_daily,
            'month_to_date_usd': month_total,
            'month_forecast_usd': month_total + (avg_daily * (30 - (end_date - month_start).days)),
            'start_date': str(start_date),
            'end_date': str(end_date)
        },
        'fetched_at': datetime.utcnow().isoformat()
    }

    print(f"Fetched costs: ${period_total:.2f} over {days} days")
    print(f"Month-to-date: ${month_total:.2f}")

    return response_data

def get_cached_costs():
    """
    Get cached costs from DynamoDB
    Returns None if cache is expired or missing
    """
    try:
        response = cache_table.get_item(
            Key={'cache_key': 'aws_costs_latest'}
        )

        if 'Item' not in response:
            print("No cached data found")
            return None

        item = response['Item']

        # Check if cache is fresh (< 1 hour old)
        cached_at = datetime.fromisoformat(item['cached_at'])
        age_minutes = (datetime.utcnow() - cached_at).total_seconds() / 60

        if age_minutes > 60:
            print(f"Cache expired ({age_minutes:.0f} minutes old)")
            return None

        print(f"Cache hit ({age_minutes:.0f} minutes old)")
        return item['data']

    except Exception as e:
        print(f"Error reading cache: {str(e)}")
        return None

def cache_costs(costs_data):
    """
    Cache costs data in DynamoDB
    """
    try:
        cache_table.put_item(
            Item={
                'cache_key': 'aws_costs_latest',
                'cached_at': datetime.utcnow().isoformat(),
                'data': costs_data,
                'ttl': int((datetime.utcnow() + timedelta(hours=2)).timestamp())
            }
        )
        print("Costs cached successfully")
    except Exception as e:
        print(f"Error caching costs: {str(e)}")
        # Don't fail the request if caching fails
