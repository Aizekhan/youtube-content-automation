# HOTFIX: prompts-api Lambda ImportModuleError

**Date:** 2026-02-08 16:11 UTC
**Severity:** CRITICAL (502 Bad Gateway)
**Status:** FIXED

## Problem

Frontend (prompts-editor.html) was getting 502 Bad Gateway errors when loading templates.

**Error:**
```
Runtime.ImportModuleError: Error: Cannot find module 'index'
Require stack:
- /var/runtime/index.mjs
```

## Root Cause

prompts-api Lambda was deployed WITHOUT node_modules, but the code uses AWS SDK v3:
```javascript
const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { DynamoDBDocumentClient, ScanCommand, ... } = require('@aws-sdk/lib-dynamodb');
```

**Deployed code size:** 2,217 bytes (just index.js + package.json)
**Missing:** node_modules directory (~2.8MB)

## Impact

- Frontend could not load any templates (Theme, Narrative, TTS, etc.)
- Users could not view or edit prompts
- All 9 template types affected

## Fix Applied

1. **Created proper deployment package:**
   ```bash
   cd aws/lambda/prompts-api
   powershell -Command "Compress-Archive -Path index.js,package.json,node_modules -DestinationPath function.zip -Force"
   ```

2. **Deployed with node_modules:**
   ```bash
   aws lambda update-function-code --function-name prompts-api --zip-file fileb://function.zip
   ```

3. **Verification:**
   - CodeSize increased: 2,217 → 2,880,227 bytes (2.8MB)
   - LastModified: 2026-02-08T16:11:54Z
   - Test successful: `curl "https://djpb4ue6wv2ohfjey32lfnhcre0zppqd.lambda-url.eu-central-1.on.aws/?type=theme"`
   - Response: `{"success":true,"data":{"templates":[...]}}`

## Performance Metrics

**After fix:**
- Duration: 2-9ms (warm start)
- Init Duration: 367ms (cold start)
- Max Memory Used: 86 MB / 512 MB
- No errors in CloudWatch logs

## Prevention

**Why this happened:**
- Previous deployment at 15:59 UTC used incomplete package
- Likely deployed with just `index.js + package.json` without node_modules

**To prevent:**
1. Always verify CodeSize after deployment (should be ~2.8MB, not 2KB)
2. Use deployment script that includes node_modules
3. Add automated test after deployment to verify Lambda works

## Related

This fix is separate from the content-generate-images optimization work (batch DynamoDB loading).
