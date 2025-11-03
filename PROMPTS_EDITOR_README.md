# AI Prompts Editor Dashboard

Web-based dashboard for managing AI agent configurations stored in DynamoDB AIPromptConfigs table.

## Features

- View all AI agents (Theme Agent, Narrative Architect)
- Edit system instructions, model, temperature, max_tokens
- Real-time character counter for instructions
- Responsive Bootstrap UI with dark theme
- CRUD operations via Lambda API

## Architecture

```
prompts-editor.html (Frontend)
    ↓ HTTPS
Lambda Function URL: prompts-api
    ↓ boto3
DynamoDB: AIPromptConfigs
```

## API Endpoint

**Lambda Function URL:**
```
https://nipe5nhmptrgg2rpik7hgip4vm0euxqr.lambda-url.eu-central-1.on.aws
```

**Endpoints:**

- `GET /prompts` - List all agents
- `GET /prompts/{agent_id}` - Get specific agent
- `PUT /prompts/{agent_id}` - Update agent configuration
- `POST /prompts` - Create new agent (optional)

## Setup Instructions

### 1. Deploy Lambda API (Already Done)

Lambda function `prompts-api` is deployed with:
- Runtime: Python 3.9
- IAM Role: ContentGeneratorLambdaRole
- Timeout: 30 seconds
- Function URL: Public access with CORS enabled

### 2. Deploy HTML Dashboard

Upload `prompts-editor.html` to your hosting:

**Option A: S3 Static Website**
```bash
aws s3 cp prompts-editor.html s3://n8n-creator.space/prompts-editor.html --acl public-read
```

**Option B: GitHub Pages / Other Hosting**
Just upload the HTML file to your web server.

### 3. Access Dashboard

Navigate to:
```
https://n8n-creator.space/prompts-editor.html
```

## Usage

### View Agents

1. Dashboard loads all agents automatically
2. Shows: model, temperature, max_tokens, version
3. Preview of system instructions (first 100 chars)

### Edit Agent

1. Click on any agent card
2. Modal opens with full configuration
3. Edit fields:
   - **Version**: e.g., "1.0", "1.1", "2.0"
   - **Model**: gpt-4o, gpt-4o-mini, gpt-4-turbo
   - **Temperature**: 0.0 - 2.0 (creativity level)
   - **Max Tokens**: 100 - 16000 (response length limit)
   - **System Instructions**: Full prompt text
4. Click "Save Changes"
5. Confirmation toast appears
6. List refreshes automatically

### Example: Update Theme Agent

```javascript
// Current configuration
{
  "agent_id": "theme_agent",
  "model": "gpt-4o",
  "temperature": "0.9",
  "max_tokens": "500",
  "version": "1.0",
  "system_instructions": "You are ThemeAgent..."
}

// Update to version 1.1 with more structured output
PUT /prompts/theme_agent
{
  "version": "1.1",
  "model": "gpt-4o",
  "temperature": "0.85",
  "max_tokens": "600",
  "system_instructions": "Enhanced instructions..."
}
```

## Testing API Manually

### List All Agents
```bash
curl https://nipe5nhmptrgg2rpik7hgip4vm0euxqr.lambda-url.eu-central-1.on.aws/prompts
```

### Get Specific Agent
```bash
curl https://nipe5nhmptrgg2rpik7hgip4vm0euxqr.lambda-url.eu-central-1.on.aws/prompts/theme_agent
```

### Update Agent
```bash
curl -X PUT \
  https://nipe5nhmptrgg2rpik7hgip4vm0euxqr.lambda-url.eu-central-1.on.aws/prompts/theme_agent \
  -H "Content-Type: application/json" \
  -d '{
    "version": "1.1",
    "model": "gpt-4o",
    "temperature": "0.85",
    "max_tokens": "600",
    "system_instructions": "Updated instructions..."
  }'
```

## Security

- Lambda Function URL has public access (`AuthType: NONE`)
- CORS enabled for all origins (`AllowOrigins: *`)
- No authentication required
- DynamoDB access controlled via IAM role

**For Production:**
1. Add Cognito authentication
2. Restrict CORS to specific domain
3. Add API Gateway with rate limiting
4. Enable CloudWatch logging

## Troubleshooting

### Dashboard shows "No agents found"

Check API connectivity:
```bash
curl https://nipe5nhmptrgg2rpik7hgip4vm0euxqr.lambda-url.eu-central-1.on.aws/prompts
```

Expected response:
```json
{
  "agents": [...],
  "count": 2
}
```

### Save fails with error

1. Check browser console for error details
2. Verify Lambda logs:
```bash
aws logs tail /aws/lambda/prompts-api --region eu-central-1 --follow
```

3. Ensure DynamoDB permissions are set:
```bash
aws iam get-role-policy \
  --role-name ContentGeneratorLambdaRole \
  --policy-name DynamoDBAccessPolicy
```

### CORS errors

Lambda Function URL should have CORS configured:
```bash
aws lambda get-function-url-config \
  --function-name prompts-api \
  --region eu-central-1
```

Expected output:
```json
{
  "Cors": {
    "AllowOrigins": ["*"],
    "AllowMethods": ["*"],
    "AllowHeaders": ["*"],
    "MaxAge": 3600
  }
}
```

## CI/CD Integration

GitHub Actions automatically deploys `prompts-api` Lambda on push to master:

```yaml
- name: Deploy Prompts API Lambda
  run: |
    cd aws/lambda/prompts-api
    zip -r prompts-api.zip lambda_function.py
    aws lambda update-function-code \
      --function-name prompts-api \
      --zip-file fileb://prompts-api.zip \
      --region eu-central-1
```

Trigger:
```bash
git add aws/lambda/prompts-api/lambda_function.py
git commit -m "Update prompts API"
git push
```

## DynamoDB Schema

**Table:** AIPromptConfigs

| Field | Type | Description |
|-------|------|-------------|
| `agent_id` (PK) | String | Unique agent identifier |
| `agent_name` | String | Display name |
| `system_instructions` | String | Full prompt text |
| `model` | String | OpenAI model name |
| `temperature` | String | 0.0 - 2.0 |
| `max_tokens` | String | Response length limit |
| `version` | String | Config version |
| `last_updated` | String | ISO timestamp |

## Next Steps

1. Deploy HTML to n8n-creator.space
2. Test editing Theme Agent instructions
3. Test editing Narrative Architect instructions
4. Add version history tracking
5. Add backup/restore functionality
6. Add multi-user permissions

## Links

- Dashboard URL: https://n8n-creator.space/prompts-editor.html
- API URL: https://nipe5nhmptrgg2rpik7hgip4vm0euxqr.lambda-url.eu-central-1.on.aws
- Lambda Function: `prompts-api` (eu-central-1)
- DynamoDB Table: `AIPromptConfigs` (eu-central-1)
