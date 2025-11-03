import json
import boto3
from datetime import datetime, timedelta
from decimal import Decimal

ce_client = boto3.client('ce', region_name='us-east-1')  # Cost Explorer is only in us-east-1
lambda_client = boto3.client('lambda', region_name='eu-central-1')

def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def lambda_handler(event, context):
    """
    Dashboard Costs API
    Endpoints:
    - GET /costs/summary - Overall cost summary
    """

    print(f"Event: {json.dumps(event, default=str)}")

    # Parse request
    http_method = event.get('httpMethod', 'GET')
    path = event.get('path', '')
    query_params = event.get('queryStringParameters') or {}

    try:
        # Get cost data
        response_data = get_cost_summary()

        response = {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'GET,OPTIONS'
            },
            'body': json.dumps(response_data, default=str)
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

def get_cost_summary():
    """Get cost summary from AWS Cost Explorer"""

    try:
        # Calculate date ranges
        today = datetime.now().date()
        month_start = today.replace(day=1)
        yesterday = today - timedelta(days=1)
        last_month_end = month_start - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)

        # Get month-to-date costs
        mtd_response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': month_start.strftime('%Y-%m-%d'),
                'End': today.strftime('%Y-%m-%d')
            },
            Granularity='MONTHLY',
            Metrics=['UnblendedCost']
        )

        mtd_cost = 0
        if mtd_response['ResultsByTime']:
            mtd_cost = float(mtd_response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount'])

        # Get yesterday's cost
        yesterday_response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': yesterday.strftime('%Y-%m-%d'),
                'End': today.strftime('%Y-%m-%d')
            },
            Granularity='DAILY',
            Metrics=['UnblendedCost']
        )

        yesterday_cost = 0
        if yesterday_response['ResultsByTime']:
            yesterday_cost = float(yesterday_response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount'])

        # Get last month cost
        last_month_response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': last_month_start.strftime('%Y-%m-%d'),
                'End': month_start.strftime('%Y-%m-%d')
            },
            Granularity='MONTHLY',
            Metrics=['UnblendedCost']
        )

        last_month_cost = 0
        if last_month_response['ResultsByTime']:
            last_month_cost = float(last_month_response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount'])

        # Forecast for month
        days_in_month = 30  # Approximate
        days_elapsed = (today - month_start).days + 1
        if days_elapsed > 0 and mtd_cost > 0:
            forecast = (mtd_cost / days_elapsed) * days_in_month
        else:
            forecast = mtd_cost

        # Get cost by service
        service_response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': month_start.strftime('%Y-%m-%d'),
                'End': today.strftime('%Y-%m-%d')
            },
            Granularity='MONTHLY',
            Metrics=['UnblendedCost'],
            GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
        )

        services = []
        if service_response['ResultsByTime']:
            for group in service_response['ResultsByTime'][0]['Groups']:
                service_name = group['Keys'][0]
                cost = float(group['Metrics']['UnblendedCost']['Amount'])
                if cost > 0:
                    services.append({
                        'name': service_name,
                        'cost': cost
                    })

        # Sort by cost descending
        services.sort(key=lambda x: x['cost'], reverse=True)

        # Get daily costs for last 30 days
        thirty_days_ago = today - timedelta(days=30)
        daily_response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': thirty_days_ago.strftime('%Y-%m-%d'),
                'End': today.strftime('%Y-%m-%d')
            },
            Granularity='DAILY',
            Metrics=['UnblendedCost']
        )

        daily_costs = []
        for result in daily_response['ResultsByTime']:
            daily_costs.append({
                'date': result['TimePeriod']['Start'],
                'cost': float(result['Total']['UnblendedCost']['Amount'])
            })

        # Mock OpenAI data (as OpenAI costs are not in AWS Cost Explorer)
        openai_data = {
            'totalCost': mtd_cost * 0.3,  # Assume 30% of costs
            'requests': 1250,
            'tokens': 4500000,
            'avgCost': (mtd_cost * 0.3) / 1250 if mtd_cost > 0 else 0,
            'daily': [
                {'date': (today - timedelta(days=i)).strftime('%Y-%m-%d'), 'cost': yesterday_cost * 0.3}
                for i in range(30, 0, -1)
            ]
        }

        return {
            'summary': {
                'monthToDate': mtd_cost,
                'yesterday': yesterday_cost,
                'forecast': forecast,
                'lastMonth': last_month_cost
            },
            'services': services,
            'daily': daily_costs,
            'openai': openai_data
        }

    except ce_client.exceptions.DataUnavailableException:
        # Cost data might not be available yet
        print("Cost data not available")
        return {
            'summary': {
                'monthToDate': 0,
                'yesterday': 0,
                'forecast': 0,
                'lastMonth': 0
            },
            'services': [],
            'daily': [],
            'openai': {
                'totalCost': 0,
                'requests': 0,
                'tokens': 0,
                'avgCost': 0,
                'daily': []
            }
        }
    except Exception as e:
        print(f"Error getting cost data: {str(e)}")
        raise
