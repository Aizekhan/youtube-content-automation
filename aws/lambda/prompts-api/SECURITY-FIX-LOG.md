# Security Fix: Input Validation - prompts-api

**Date:** 2025-12-01
**Issue:** Critical - NoSQL Injection vulnerability
**Severity:** CRITICAL
**Status:** FIXED ✅

## Vulnerability Description

The `prompts-api` Lambda function accepted user input (`templateId`, `templateType`) without validation and passed it directly to DynamoDB operations, creating a NoSQL injection vulnerability.

## Changes Made

### 1. Added Input Validation Functions

- `validateTemplateId(templateId)`: Validates template IDs
  - Max length: 100 characters
  - Format: Only `[a-zA-Z0-9_-]` allowed
  - Prevents NoSQL injection

- `validateTemplateType(templateType)`: Whitelist validation
  - Only allows: theme, narrative, sfx, thumbnail, description, image, video, cta, tts

- `validateTemplateBody(body)`: Request body validation
  - Max size: 100KB
  - Prevents prototype pollution
  - Type checking

### 2. Applied Validation to All Routes

- ✅ GET / (list templates)
- ✅ GET /template/{id} (get specific)
- ✅ POST / (create template)
- ✅ PUT /template/{id} (update template)
- ✅ DELETE /template/{id} (delete template)

## Testing

Before deployment, test with:

```bash
# Valid request (should work)
curl "https://YOUR_LAMBDA_URL?type=theme"

# Invalid type (should be rejected)
curl "https://YOUR_LAMBDA_URL?type=../../etc/passwd"

# Invalid ID (should be rejected)
curl "https://YOUR_LAMBDA_URL/template/{id:1}?type=theme"
```

## Deployment

```bash
cd aws/lambda/prompts-api
zip -r function.zip index.js package.json node_modules/
aws lambda update-function-code \
  --function-name prompts-api \
  --zip-file fileb://function.zip
```

## Impact

- ✅ Prevents NoSQL injection attacks
- ✅ Prevents DOS via huge payloads
- ✅ Prevents prototype pollution
- ⚠️ May reject some edge-case valid IDs (if they contain special characters)

## Next Steps

- Deploy to production
- Monitor CloudWatch logs for validation errors
- Update frontend if any valid IDs are being rejected
