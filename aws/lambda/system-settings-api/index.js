/**
 * System Settings API Lambda
 * Manages system settings (Telegram notifications, API keys, etc.)
 */

const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { DynamoDBDocumentClient, GetCommand, PutCommand, DeleteCommand, ScanCommand } = require('@aws-sdk/lib-dynamodb');

const client = new DynamoDBClient({ region: 'eu-central-1' });
const docClient = DynamoDBDocumentClient.from(client);

const TABLE_NAME = 'SystemSettings';

// CORS headers
const CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Methods': 'GET,POST,DELETE,OPTIONS',
    'Content-Type': 'application/json'
};

exports.handler = async (event) => {
    console.log('Event:', JSON.stringify(event, null, 2));

    // Handle OPTIONS for CORS
    if (event.httpMethod === 'OPTIONS' || event.requestContext?.http?.method === 'OPTIONS') {
        return {
            statusCode: 200,
            headers: CORS_HEADERS,
            body: ''
        };
    }

    try {
        const method = event.httpMethod || event.requestContext?.http?.method;
        const path = event.path || event.requestContext?.http?.path || '';

        // GET /settings or GET /settings/{type}
        if (method === 'GET') {
            return await handleGet(event);
        }

        // POST /settings - save/update settings
        if (method === 'POST') {
            return await handlePost(event);
        }

        // DELETE /settings/{type}
        if (method === 'DELETE') {
            return await handleDelete(event);
        }

        return {
            statusCode: 400,
            headers: CORS_HEADERS,
            body: JSON.stringify({ error: 'Unsupported method' })
        };

    } catch (error) {
        console.error('Error:', error);
        return {
            statusCode: 500,
            headers: CORS_HEADERS,
            body: JSON.stringify({
                error: 'Internal server error',
                details: error.message
            })
        };
    }
};

async function handleGet(event) {
    const pathParams = event.pathParameters || {};
    const queryParams = event.queryStringParameters || {};

    const settingType = pathParams.type || queryParams.type;
    const settingId = pathParams.id || queryParams.id || 'default';

    // If no type specified, return all settings
    if (!settingType) {
        const command = new ScanCommand({
            TableName: TABLE_NAME
        });

        const response = await docClient.send(command);

        return {
            statusCode: 200,
            headers: CORS_HEADERS,
            body: JSON.stringify({
                success: true,
                settings: response.Items || []
            })
        };
    }

    // Get specific setting
    const command = new GetCommand({
        TableName: TABLE_NAME,
        Key: {
            setting_type: settingType,
            setting_id: settingId
        }
    });

    const response = await docClient.send(command);

    if (!response.Item) {
        return {
            statusCode: 404,
            headers: CORS_HEADERS,
            body: JSON.stringify({
                success: false,
                error: 'Setting not found'
            })
        };
    }

    return {
        statusCode: 200,
        headers: CORS_HEADERS,
        body: JSON.stringify({
            success: true,
            setting: response.Item
        })
    };
}

async function handlePost(event) {
    const body = typeof event.body === 'string' ? JSON.parse(event.body) : event.body;

    if (!body.setting_type) {
        return {
            statusCode: 400,
            headers: CORS_HEADERS,
            body: JSON.stringify({ error: 'setting_type is required' })
        };
    }

    const settingId = body.setting_id || 'default';
    const config = body.config || {};

    const item = {
        setting_type: body.setting_type,
        setting_id: settingId,
        config: config,
        updated_at: new Date().toISOString(),
        updated_by: body.updated_by || 'system'
    };

    const command = new PutCommand({
        TableName: TABLE_NAME,
        Item: item
    });

    await docClient.send(command);

    return {
        statusCode: 200,
        headers: CORS_HEADERS,
        body: JSON.stringify({
            success: true,
            message: 'Setting saved successfully',
            setting: item
        })
    };
}

async function handleDelete(event) {
    const pathParams = event.pathParameters || {};
    const settingType = pathParams.type;
    const settingId = pathParams.id || 'default';

    if (!settingType) {
        return {
            statusCode: 400,
            headers: CORS_HEADERS,
            body: JSON.stringify({ error: 'setting_type is required' })
        };
    }

    const command = new DeleteCommand({
        TableName: TABLE_NAME,
        Key: {
            setting_type: settingType,
            setting_id: settingId
        }
    });

    await docClient.send(command);

    return {
        statusCode: 200,
        headers: CORS_HEADERS,
        body: JSON.stringify({
            success: true,
            message: 'Setting deleted successfully'
        })
    };
}
