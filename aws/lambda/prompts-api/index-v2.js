/**
 * Prompts API Lambda V2 - Multi-Table Template System
 *
 * Supports 4 template types across 4 DynamoDB tables:
 * - Theme & Narrative (PromptTemplatesV2)
 * - Image Generation (ImageGenerationTemplates)
 * - Video Editing (VideoEditingTemplates)
 * - CTA (CTATemplates)
 */

const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { DynamoDBDocumentClient, ScanCommand, GetCommand, PutCommand, QueryCommand, DeleteCommand } = require('@aws-sdk/lib-dynamodb');

const client = new DynamoDBClient({ region: process.env.AWS_REGION || 'eu-central-1' });
const docClient = DynamoDBDocumentClient.from(client);

// Table mapping
const TABLES = {
  'theme': 'PromptTemplatesV2',
  'narrative': 'PromptTemplatesV2',
  'image': 'ImageGenerationTemplates',
  'video': 'VideoEditingTemplates',
  'cta': 'CTATemplates'
};

// CORS headers
const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Authorization',
  'Content-Type': 'application/json'
};

exports.handler = async (event) => {
  console.log('Event:', JSON.stringify(event, null, 2));

  const method = event.requestContext?.http?.method || event.httpMethod || 'GET';
  const path = event.requestContext?.http?.path || event.rawPath || event.path || '/';

  // Handle CORS preflight
  if (method === 'OPTIONS') {
    return {
      statusCode: 200,
      headers: CORS_HEADERS,
      body: ''
    };
  }

  try {
    const pathParts = path.split('/').filter(p => p);
    let body = {};
    if (event.body) {
      body = typeof event.body === 'string' ? JSON.parse(event.body) : event.body;
    }
    const queryParams = event.queryStringParameters || {};

    console.log(`${method} ${path}`, { pathParts, queryParams, bodyKeys: Object.keys(body) });

    // Route handling
    if (method === 'GET' && pathParts.length === 0) {
      // GET / - List templates (requires ?type=theme|narrative|image|video|cta)
      const templateType = queryParams.type || queryParams.template_type;
      if (!templateType) {
        return sendError(400, 'Missing required query parameter: type (theme|narrative|image|video|cta)');
      }
      return await handleListTemplates(templateType, queryParams);
    }

    if (method === 'GET' && pathParts.length === 2 && pathParts[0] === 'template') {
      // GET /template/{id}?type=theme - Get specific template
      const templateType = queryParams.type || queryParams.template_type;
      if (!templateType) {
        return sendError(400, 'Missing required query parameter: type');
      }
      return await handleGetTemplate(templateType, pathParts[1]);
    }

    if (method === 'POST' && pathParts.length === 0) {
      // POST / - Create new template (type in body)
      if (!body.template_type) {
        return sendError(400, 'Missing required field: template_type');
      }
      return await handleCreateTemplate(body.template_type, body);
    }

    if (method === 'PUT' && pathParts.length === 2 && pathParts[0] === 'template') {
      // PUT /template/{id} - Update template (type in body or query)
      const templateType = body.template_type || queryParams.type;
      if (!templateType) {
        return sendError(400, 'Missing template_type in body or query');
      }
      return await handleUpdateTemplate(templateType, pathParts[1], body);
    }

    if (method === 'DELETE' && pathParts.length === 2 && pathParts[0] === 'template') {
      // DELETE /template/{id}?type=theme - Delete template
      const templateType = queryParams.type;
      if (!templateType) {
        return sendError(400, 'Missing required query parameter: type');
      }
      return await handleDeleteTemplate(templateType, pathParts[1]);
    }

    // SSML generation endpoint
    if (method === 'POST' && pathParts.length === 1 && pathParts[0] === 'generate-ssml') {
      // POST /generate-ssml - Generate SSML from params
      return await handleGenerateSSML(body);
    }

    return sendError(404, 'Endpoint not found');

  } catch (error) {
    console.error('Error:', error);
    return sendError(500, `Server error: ${error.message}`);
  }
};

// ============================================================================
// HANDLERS
// ============================================================================

async function handleListTemplates(templateType, queryParams) {
  const tableName = TABLES[templateType];
  if (!tableName) {
    return sendError(400, `Invalid template type: ${templateType}. Must be one of: theme, narrative, image, video, cta`);
  }

  console.log(`Listing ${templateType} templates from ${tableName}`);

  // For PromptTemplatesV2, filter by template_type
  let filterExpression = null;
  let expressionAttributeValues = {};

  if (tableName === 'PromptTemplatesV2') {
    filterExpression = 'template_type = :templateType';
    expressionAttributeValues[':templateType'] = templateType;
  }

  // Add is_active filter if provided
  if (queryParams.is_active !== undefined) {
    const activeValue = queryParams.is_active === 'true' || queryParams.is_active === '1';
    if (filterExpression) {
      filterExpression += ' AND is_active = :isActive';
    } else {
      filterExpression = 'is_active = :isActive';
    }
    expressionAttributeValues[':isActive'] = activeValue;
  }

  const scanParams = {
    TableName: tableName
  };

  if (filterExpression) {
    scanParams.FilterExpression = filterExpression;
    scanParams.ExpressionAttributeValues = expressionAttributeValues;
  }

  const result = await docClient.send(new ScanCommand(scanParams));

  return sendSuccess({
    templates: result.Items || [],
    count: result.Items?.length || 0,
    template_type: templateType,
    table: tableName
  });
}

async function handleGetTemplate(templateType, templateId) {
  const tableName = TABLES[templateType];
  if (!tableName) {
    return sendError(400, `Invalid template type: ${templateType}`);
  }

  console.log(`Getting ${templateType} template ${templateId} from ${tableName}`);

  const result = await docClient.send(new GetCommand({
    TableName: tableName,
    Key: { template_id: templateId }
  }));

  if (!result.Item) {
    return sendError(404, 'Template not found');
  }

  return sendSuccess({
    template: result.Item
  });
}

async function handleCreateTemplate(templateType, body) {
  const tableName = TABLES[templateType];
  if (!tableName) {
    return sendError(400, `Invalid template type: ${templateType}`);
  }

  console.log(`Creating ${templateType} template in ${tableName}`);

  // Generate template ID
  const timestamp = Date.now();
  const random = Math.random().toString(36).substring(2, 8);
  const templateId = body.template_id || `${templateType}_template_${timestamp}_${random}`;

  // Common fields for all templates
  const template = {
    template_id: templateId,
    template_type: templateType,
    template_name: body.template_name || 'Unnamed Template',
    description: body.description || '',
    genre: body.genre || 'General',
    is_active: body.is_active !== undefined ? body.is_active : true,
    version: body.version || 1,
    created_at: Date.now(),
    updated_at: Date.now(),
    created_by: body.created_by || 'admin',
    usage_count: 0,
    ...body
  };

  // Validate specific fields per type
  if (templateType === 'image' && !body.prompt_structure) {
    return sendError(400, 'Image templates require prompt_structure field');
  }
  if (templateType === 'video' && !body.editing_params) {
    return sendError(400, 'Video templates require editing_params field');
  }
  if (templateType === 'cta' && !body.elements) {
    return sendError(400, 'CTA templates require elements field');
  }

  await docClient.send(new PutCommand({
    TableName: tableName,
    Item: template
  }));

  return sendSuccess({
    template,
    message: `${templateType} template created successfully`
  }, 201);
}

async function handleUpdateTemplate(templateType, templateId, body) {
  const tableName = TABLES[templateType];
  if (!tableName) {
    return sendError(400, `Invalid template type: ${templateType}`);
  }

  console.log(`Updating ${templateType} template ${templateId} in ${tableName}`);

  // Get existing template
  const result = await docClient.send(new GetCommand({
    TableName: tableName,
    Key: { template_id: templateId }
  }));

  if (!result.Item) {
    return sendError(404, 'Template not found');
  }

  const existing = result.Item;

  // Update fields
  const updated = {
    ...existing,
    ...body,
    template_id: templateId,  // Keep primary key
    template_type: templateType,  // Keep type
    updated_at: Date.now()
  };

  // Increment version if major changes
  if (body.prompt_structure || body.editing_params || body.elements || body.sections) {
    updated.version = (existing.version || 1) + 1;
  }

  await docClient.send(new PutCommand({
    TableName: tableName,
    Item: updated
  }));

  return sendSuccess({
    template: updated,
    message: 'Template updated successfully'
  });
}

async function handleDeleteTemplate(templateType, templateId) {
  const tableName = TABLES[templateType];
  if (!tableName) {
    return sendError(400, `Invalid template type: ${templateType}`);
  }

  console.log(`Deleting ${templateType} template ${templateId} from ${tableName}`);

  // Soft delete: set is_active = false
  const result = await docClient.send(new GetCommand({
    TableName: tableName,
    Key: { template_id: templateId }
  }));

  if (!result.Item) {
    return sendError(404, 'Template not found');
  }

  const updated = {
    ...result.Item,
    is_active: false,
    updated_at: Date.now()
  };

  await docClient.send(new PutCommand({
    TableName: tableName,
    Item: updated
  }));

  return sendSuccess({
    message: 'Template deactivated successfully'
  });
}

async function handleGenerateSSML(body) {
  const { text, ssml_params, tts_service } = body;

  if (!text || !ssml_params) {
    return sendError(400, 'Missing required fields: text, ssml_params');
  }

  const service = tts_service || 'aws-polly';
  const ssml = generateSSML(text, ssml_params, service);

  return sendSuccess({
    text,
    ssml_params,
    tts_service: service,
    ssml
  });
}

// ============================================================================
// SSML GENERATION
// ============================================================================

function generateSSML(text, params, service = 'aws-polly') {
  const {
    rate = 'medium',
    pitch = '+0%',
    volume = 'medium',
    emphasis = 'moderate',
    pause_before = '0ms',
    pause_after = '0ms'
  } = params;

  switch (service) {
    case 'aws-polly':
      return generateAWSPollySSML(text, { rate, pitch, volume, emphasis, pause_before, pause_after });

    case 'google-tts':
      return generateGoogleSSML(text, { rate, pitch, pause_before, pause_after });

    case 'azure-tts':
      return generateAzureSSML(text, { rate, pitch, volume, pause_before, pause_after });

    case 'elevenlabs':
      // ElevenLabs doesn't use SSML
      return text;

    default:
      return generateAWSPollySSML(text, { rate, pitch, volume, emphasis, pause_before, pause_after });
  }
}

function generateAWSPollySSML(text, params) {
  let ssml = '<speak>';

  // Add pause before if specified
  if (params.pause_before && params.pause_before !== '0ms') {
    ssml += `<break time="${params.pause_before}"/>`;
  }

  // Wrap in prosody
  ssml += `<prosody rate="${params.rate}" pitch="${params.pitch}" volume="${params.volume}">`;

  // Add emphasis if specified
  if (params.emphasis && params.emphasis !== 'none') {
    ssml += `<emphasis level="${params.emphasis}">${text}</emphasis>`;
  } else {
    ssml += text;
  }

  ssml += '</prosody>';

  // Add pause after if specified
  if (params.pause_after && params.pause_after !== '0ms') {
    ssml += `<break time="${params.pause_after}"/>`;
  }

  ssml += '</speak>';
  return ssml;
}

function generateGoogleSSML(text, params) {
  let ssml = '<speak>';

  if (params.pause_before && params.pause_before !== '0ms') {
    ssml += `<break time="${params.pause_before}"/>`;
  }

  ssml += `<prosody rate="${params.rate}" pitch="${params.pitch}">${text}</prosody>`;

  if (params.pause_after && params.pause_after !== '0ms') {
    ssml += `<break time="${params.pause_after}"/>`;
  }

  ssml += '</speak>';
  return ssml;
}

function generateAzureSSML(text, params) {
  let ssml = '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">';

  if (params.pause_before && params.pause_before !== '0ms') {
    ssml += `<break time="${params.pause_before}"/>`;
  }

  ssml += `<prosody rate="${params.rate}" pitch="${params.pitch}" volume="${params.volume}">${text}</prosody>`;

  if (params.pause_after && params.pause_after !== '0ms') {
    ssml += `<break time="${params.pause_after}"/>`;
  }

  ssml += '</speak>';
  return ssml;
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

function sendSuccess(data, statusCode = 200) {
  return {
    statusCode,
    headers: CORS_HEADERS,
    body: JSON.stringify({ success: true, data })
  };
}

function sendError(statusCode, message) {
  return {
    statusCode,
    headers: CORS_HEADERS,
    body: JSON.stringify({ success: false, error: message })
  };
}
