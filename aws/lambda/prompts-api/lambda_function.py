import json
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
table = dynamodb.Table('AIPromptConfigs')

def lambda_handler(event, context):
    """
    API Gateway Lambda для управління AIPromptConfigs

    Methods:
    - GET    /prompts         - List all agents
    - GET    /prompts/{id}    - Get specific agent
    - PUT    /prompts/{id}    - Update agent
    - POST   /prompts         - Create agent (if needed)
    """

    print(f"Event: {json.dumps(event)}")

    # CORS headers
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }

    try:
        http_method = event.get('httpMethod', event.get('requestContext', {}).get('http', {}).get('method'))
        path = event.get('path', event.get('rawPath', ''))

        # Handle OPTIONS (CORS preflight)
        if http_method == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps({'message': 'OK'})
            }

        # Extract agent_id from path if present
        path_parts = path.strip('/').split('/')
        agent_id = path_parts[1] if len(path_parts) > 1 and path_parts[1] else None

        # Route requests
        if http_method == 'GET' and not agent_id:
            # List all agents
            response = list_agents()

        elif http_method == 'GET' and agent_id:
            # Get specific agent
            response = get_agent(agent_id)

        elif http_method == 'PUT' and agent_id:
            # Update agent
            body = json.loads(event.get('body', '{}'))
            response = update_agent(agent_id, body)

        elif http_method == 'POST':
            # Create new agent
            body = json.loads(event.get('body', '{}'))
            response = create_agent(body)

        else:
            response = {
                'statusCode': 400,
                'body': {'error': 'Invalid request'}
            }

        return {
            'statusCode': response.get('statusCode', 200),
            'headers': headers,
            'body': json.dumps(response.get('body', response), ensure_ascii=False)
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

        return {
            'statusCode': 500,
            'headers': headers,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }


def list_agents():
    """Get all AI agents"""
    try:
        response = table.scan()
        items = response.get('Items', [])

        # Sort by agent_id
        items.sort(key=lambda x: x.get('agent_id', ''))

        return {
            'statusCode': 200,
            'body': {
                'agents': items,
                'count': len(items)
            }
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': {'error': str(e)}
        }


def get_agent(agent_id):
    """Get specific agent by ID"""
    try:
        response = table.get_item(Key={'agent_id': agent_id})

        if 'Item' not in response:
            return {
                'statusCode': 404,
                'body': {'error': f'Agent {agent_id} not found'}
            }

        return {
            'statusCode': 200,
            'body': response['Item']
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': {'error': str(e)}
        }


def update_agent(agent_id, data):
    """Update agent configuration"""
    try:
        # Validate required fields
        if 'system_instructions' not in data:
            return {
                'statusCode': 400,
                'body': {'error': 'system_instructions is required'}
            }

        # Build update expression
        update_expr = 'set '
        expr_values = {}
        expr_names = {}

        # Allowed fields to update
        allowed_fields = ['system_instructions', 'model', 'temperature', 'max_tokens', 'version']

        updates = []
        for field in allowed_fields:
            if field in data:
                # Use expression attribute names for reserved words
                attr_name = f'#{field}'
                attr_value = f':{field}'
                updates.append(f'{attr_name} = {attr_value}')
                expr_names[attr_name] = field
                expr_values[attr_value] = data[field]

        if not updates:
            return {
                'statusCode': 400,
                'body': {'error': 'No valid fields to update'}
            }

        update_expr += ', '.join(updates)

        # Add last_updated timestamp
        update_expr += ', #last_updated = :last_updated'
        expr_names['#last_updated'] = 'last_updated'
        expr_values[':last_updated'] = datetime.utcnow().isoformat() + 'Z'

        # Update item
        response = table.update_item(
            Key={'agent_id': agent_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
            ReturnValues='ALL_NEW'
        )

        return {
            'statusCode': 200,
            'body': {
                'message': 'Agent updated successfully',
                'agent': response['Attributes']
            }
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': {'error': str(e)}
        }


def create_agent(data):
    """Create new agent (optional - only if you want to add agents via UI)"""
    try:
        # Validate required fields
        required_fields = ['agent_id', 'agent_name', 'system_instructions', 'model']
        for field in required_fields:
            if field not in data:
                return {
                    'statusCode': 400,
                    'body': {'error': f'{field} is required'}
                }

        # Check if agent already exists
        existing = table.get_item(Key={'agent_id': data['agent_id']})
        if 'Item' in existing:
            return {
                'statusCode': 409,
                'body': {'error': f'Agent {data["agent_id"]} already exists'}
            }

        # Create item
        item = {
            'agent_id': data['agent_id'],
            'agent_name': data['agent_name'],
            'system_instructions': data['system_instructions'],
            'model': data.get('model', 'gpt-4o'),
            'temperature': data.get('temperature', '0.8'),
            'max_tokens': data.get('max_tokens', '4000'),
            'version': data.get('version', '1.0'),
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'last_updated': datetime.utcnow().isoformat() + 'Z'
        }

        table.put_item(Item=item)

        return {
            'statusCode': 201,
            'body': {
                'message': 'Agent created successfully',
                'agent': item
            }
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': {'error': str(e)}
        }
