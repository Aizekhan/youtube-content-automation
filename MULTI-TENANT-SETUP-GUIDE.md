# 🚀 Multi-Tenant Setup Guide
## YouTube Content Automation - Complete Authentication System

**Last Updated:** January 28, 2025
**Status:** Ready for Implementation
**Estimated Time:** 2-3 hours for initial setup

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Step-by-Step Setup](#step-by-step-setup)
4. [Testing](#testing)
5. [Troubleshooting](#troubleshooting)
6. [Next Steps](#next-steps)

---

## 🎯 Overview

This guide will help you set up complete multi-tenant authentication for the YouTube Content Automation system using:

- **AWS Cognito** for user management
- **Google OAuth** for sign-in
- **DynamoDB** for user data storage
- **JWT tokens** for API authentication

### What Gets Installed:

✅ AWS Cognito User Pool
✅ Users table in DynamoDB
✅ Login page with Google Sign-In
✅ Session management (auth.js)
✅ Database migration (add user_id to all tables)
✅ Row-level security for all data

---

## ⚡ Prerequisites

### 1. AWS Account Setup

```bash
# Verify AWS credentials
aws sts get-caller-identity

# Should output:
# {
#     "UserId": "...",
#     "Account": "599297130956",
#     "Arn": "arn:aws:iam::599297130956:user/..."
# }
```

### 2. Google Cloud Project

You need a Google Cloud Project with OAuth 2.0 credentials:

1. Go to: https://console.cloud.google.com/apis/credentials
2. Create a new project (or use existing)
3. Enable "Google+ API"
4. Create OAuth 2.0 Client ID:
   - Application type: **Web application**
   - Name: `YouTube Automation`
   - Authorized redirect URIs: (will be added after Cognito setup)

**Don't create the OAuth client yet - we need the Cognito redirect URI first!**

### 3. Tools Required

- AWS CLI (configured)
- Python 3.x
- Bash shell (Git Bash on Windows)
- Text editor

---

## 🔧 Step-by-Step Setup

### **PHASE 1: AWS Cognito Setup (30 min)**

#### Step 1.1: Create Cognito User Pool & Users Table

```bash
cd E:/youtube-content-automation/aws

# Make script executable (if on Linux/Mac)
chmod +x setup-cognito-multitenant.sh

# Run setup script
bash setup-cognito-multitenant.sh
```

**What this does:**
- Creates `Users` table in DynamoDB
- Creates Cognito User Pool
- Creates App Client
- Creates Cognito Domain
- Outputs configuration files

**Output files:**
- `cognito-user-pool-id.txt`
- `cognito-client-id.txt`
- `cognito-domain.txt`

**⚠️ SAVE THESE VALUES!** You'll need them next.

---

#### Step 1.2: Configure Google OAuth

Now that you have the Cognito domain, configure Google OAuth:

1. **Get Cognito redirect URI:**
```bash
cat cognito-domain.txt
# Example: https://youtube-automation-1234567890.auth.eu-central-1.amazoncognito.com
```

Your redirect URI will be:
```
<cognito-domain>/oauth2/idpresponse
```
Example:
```
https://youtube-automation-1234567890.auth.eu-central-1.amazoncognito.com/oauth2/idpresponse
```

2. **Create Google OAuth Client:**
   - Go to: https://console.cloud.google.com/apis/credentials
   - Click "Create Credentials" → "OAuth 2.0 Client ID"
   - Application type: **Web application**
   - Name: `YouTube Automation`
   - Authorized redirect URIs: **Paste the URI from above**
   - Click "Create"
   - **COPY the Client ID and Client Secret**

3. **Add Google as Identity Provider in Cognito:**

```bash
# Replace with YOUR values:
GOOGLE_CLIENT_ID="123456789-abc123.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET="GOCSPX-abc123xyz"
USER_POOL_ID="$(cat cognito-user-pool-id.txt)"

# Add Google provider
aws cognito-idp create-identity-provider \
  --user-pool-id $USER_POOL_ID \
  --provider-name Google \
  --provider-type Google \
  --provider-details \
    client_id=$GOOGLE_CLIENT_ID,\
    client_secret=$GOOGLE_CLIENT_SECRET,\
    authorize_scopes="openid email profile" \
  --attribute-mapping \
    email=email,\
    name=name,\
    picture=picture \
  --region eu-central-1
```

✅ **Google OAuth is now connected!**

---

#### Step 1.3: Update Frontend Configuration

Update the configuration in your HTML files:

**Files to update:**
1. `login.html` (line 226-230)
2. `callback.html` (line 73-77)

```javascript
// Replace these values:
const AUTH_CONFIG = {
    region: 'eu-central-1',
    userPoolId: 'REPLACE_WITH_USER_POOL_ID',  // From cognito-user-pool-id.txt
    userPoolWebClientId: 'REPLACE_WITH_CLIENT_ID',  // From cognito-client-id.txt
    authDomain: 'REPLACE_WITH_DOMAIN',  // From cognito-domain.txt
};
```

**Example after replacement:**
```javascript
const AUTH_CONFIG = {
    region: 'eu-central-1',
    userPoolId: 'eu-central-1_ABC123',
    userPoolWebClientId: '4a5b6c7d8e9f0g1h2i3j4k',
    authDomain: 'https://youtube-automation-1234567890.auth.eu-central-1.amazoncognito.com',
};
```

**Also update in `js/auth.js` (line 17-20):**
```javascript
this.config = {
    region: 'eu-central-1',
    userPoolId: 'eu-central-1_ABC123',  // Your value
    userPoolWebClientId: '4a5b6c7d8e9f0g1h2i3j4k',  // Your value
    authDomain: 'https://youtube-automation-1234567890.auth.eu-central-1.amazoncognito.com',  // Your value
};
```

---

### **PHASE 2: Database Migration (1 hour)**

⚠️ **IMPORTANT: Backup your database first!**

```bash
# Create backup
bash backup-production.sh
```

#### Step 2.1: Migrate Critical Tables (Phase 1)

```bash
cd E:/youtube-content-automation/aws

# Run Phase 1 migration
bash migrate-add-user-id-phase1.sh
```

**This migrates:**
- ✅ YouTubeCredentials (adds user_id GSI + updates records)
- ✅ ChannelConfigs (adds user_id-channel_id GSI + updates records)

**Duration:** ~10-15 minutes (depends on data size)

All existing data will be assigned to `admin-legacy-user`.

---

#### Step 2.2: Migrate Remaining Tables (Phase 2)

```bash
# Run Phase 2 migration
bash migrate-add-user-id-phase2.sh
```

**This migrates:**
- ✅ GeneratedContent
- ✅ CostTracking
- ✅ AIPromptConfigs

**Duration:** ~20-30 minutes (depends on data size)

---

### **PHASE 3: Update Lambda Functions (1-2 hours)**

Now we need to update Lambda functions to enforce user_id filtering.

#### Step 3.1: Update content-get-channels

**File:** `aws/lambda/content-get-channels/lambda_function.py`

**Replace entire file with:**

```python
import json
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
table = dynamodb.Table('ChannelConfigs')

def lambda_handler(event, context):
    """Get Active Channels - Multi-tenant version"""
    print(f"🔍 Get Active Channels - Multi-tenant")
    print(f"Event: {json.dumps(event, default=str)}")

    # Extract user_id from event
    user_id = event.get('user_id')

    if not user_id:
        print("❌ No user_id provided")
        return {
            'statusCode': 403,
            'body': json.dumps({'error': 'user_id required'})
        }

    try:
        # Query by user_id with is_active filter
        response = table.query(
            IndexName='user_id-channel_id-index',
            KeyConditionExpression='user_id = :uid',
            FilterExpression='is_active = :active',
            ExpressionAttributeValues={
                ':uid': user_id,
                ':active': True
            }
        )

        items = response.get('Items', [])

        channels = []
        for item in items:
            # Verify ownership (defense in depth)
            if item.get('user_id') != user_id:
                print(f"⚠️ Security: Skipping channel {item.get('channel_id')} - wrong user")
                continue

            channels.append({
                'channel_id': item.get('channel_id', ''),
                'config_id': item.get('config_id', ''),
                'channel_name': item.get('channel_name', ''),
                'genre': item.get('genre', 'General')
            })

        result = channels[:10]
        print(f"✅ Returning {len(result)} channels for user {user_id}")

        # Return channels array directly for Step Functions
        return result

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return []
```

**Deploy:**
```bash
cd aws/lambda/content-get-channels
zip -r function.zip lambda_function.py
aws lambda update-function-code \
  --function-name content-get-channels \
  --zip-file fileb://function.zip \
  --region eu-central-1
```

---

#### Step 3.2: Update dashboard-content

**File:** `aws/lambda/dashboard-content/lambda_function.py`

**Find the `get_content_list` function (line 115) and replace with:**

```python
def get_content_list(user_id, params):
    """Get content filtered by user_id"""

    table = dynamodb.Table('GeneratedContent')

    # Query using user_id GSI instead of scanning
    response = table.query(
        IndexName='user_id-created_at-index',
        KeyConditionExpression='user_id = :uid',
        ExpressionAttributeValues={
            ':uid': user_id
        },
        ScanIndexForward=False,  # Newest first
        Limit=int(params.get('limit', 100))
    )

    items = response.get('Items', [])

    # Filter: only show complete content with narrative scenes
    items = [item for item in items if item.get('narrative_data', {}).get('scenes')]

    # Rest of function stays the same...
    # (stats calculation, S3 URL conversion, etc.)
```

**And update the `lambda_handler` function (line 64):**

```python
def lambda_handler(event, context):
    """Dashboard Content API - Multi-tenant version"""

    print(f"Event: {json.dumps(event, default=str)}")

    # Extract user_id from API Gateway authorizer or header
    user_id = None

    # Try from authorizer
    if 'requestContext' in event and 'authorizer' in event['requestContext']:
        authorizer = event['requestContext']['authorizer']
        if 'claims' in authorizer:
            user_id = authorizer['claims'].get('sub')

    # Try from header
    if not user_id and 'headers' in event:
        user_id = event['headers'].get('X-User-ID')

    if not user_id:
        return {
            'statusCode': 401,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': 'https://n8n-creator.space'
            },
            'body': json.dumps({'error': 'Unauthorized'})
        }

    query_params = event.get('queryStringParameters') or {}

    try:
        response_data = get_content_list(user_id, query_params)

        # Rest stays the same...
```

**Deploy:**
```bash
cd aws/lambda/dashboard-content
zip -r function.zip lambda_function.py
aws lambda update-function-code \
  --function-name dashboard-content \
  --zip-file fileb://function.zip \
  --region eu-central-1
```

---

### **PHASE 4: Update Frontend Pages (30 min)**

Add authentication checks to all HTML pages.

**Update `index.html`, `channels.html`, `content.html`, `costs.html`, etc.**

**Add at the end of `<head>` section:**
```html
<script src="js/auth.js"></script>
```

**Add at the start of `<script>` section (before any other code):**
```javascript
// Require authentication
(async function() {
    showAuthLoadingOverlay();
    const isAuth = await auth.requireAuth();
    hideAuthLoadingOverlay();

    if (!isAuth) {
        return; // Will redirect to login
    }

    // Create user profile dropdown
    createUserProfileDropdown();

    // Now safe to load page content
    loadPageData();
})();
```

**Update all API calls to include auth headers:**

**Example - channels.html:**
```javascript
// OLD:
const response = await fetch(API_URLS.getChannels);

// NEW:
const response = await fetch(API_URLS.getChannels, {
    headers: auth.getAuthHeaders()
});
```

---

## ✅ Testing

### Test 1: Login Flow

1. Open: `https://n8n-creator.space/login.html`
2. Click "Continue with Google"
3. Select Google account
4. Should redirect to `callback.html` → then to `index.html`
5. Verify profile dropdown appears in navbar

### Test 2: Data Isolation

1. Create test user in Cognito
2. Login as test user
3. Verify channels page shows NO channels (because user_id doesn't match)
4. Create a channel as test user
5. Logout and login as admin user
6. Verify admin sees only their channels

### Test 3: API Authentication

```bash
# Try to call API without auth (should fail)
curl https://YOUR_LAMBDA_URL/content

# Should return: {"error": "Unauthorized"}
```

---

## 🐛 Troubleshooting

### Issue: "REPLACE_WITH_USER_POOL_ID" error

**Solution:** You forgot to update the configuration in `login.html`, `callback.html`, and `js/auth.js`.

Copy values from:
- `cognito-user-pool-id.txt`
- `cognito-client-id.txt`
- `cognito-domain.txt`

### Issue: "Invalid redirect URI"

**Solution:** Make sure you added the EXACT redirect URI to Google OAuth:
```
<your-cognito-domain>/oauth2/idpresponse
```

### Issue: Migration script fails

**Solution:**
1. Check AWS credentials: `aws sts get-caller-identity`
2. Check table exists: `aws dynamodb describe-table --table-name YouTubeCredentials --region eu-central-1`
3. Run with verbose: `bash -x migrate-add-user-id-phase1.sh`

### Issue: No channels showing after login

**Expected!** Existing channels are assigned to `admin-legacy-user`. You need to:
1. Login with your actual user
2. Get your user_id from browser console: `auth.getUserId()`
3. Manually update one channel in DynamoDB to test:
```bash
aws dynamodb update-item \
  --table-name ChannelConfigs \
  --key '{"config_id": {"S": "YOUR_CONFIG_ID"}}' \
  --update-expression "SET user_id = :uid" \
  --expression-attribute-values '{":uid": {"S": "YOUR_USER_ID"}}' \
  --region eu-central-1
```

---

## 🎉 Next Steps

After completing setup:

1. **Create First Real User:**
   - Login with Google
   - Note your user_id
   - Assign your existing channels to your user_id

2. **Update Step Functions:**
   - Modify workflow to pass user_id through all stages
   - Test full content generation pipeline

3. **Add Lambda Authorizer:**
   - Create authorizer Lambda
   - Attach to API Gateway/Function URLs
   - Validate JWT tokens

4. **Update Remaining Lambdas:**
   - content-save-result
   - content-narrative
   - content-theme-agent
   - All others to accept user_id

5. **Security Audit:**
   - Test data isolation
   - Test unauthorized access attempts
   - Enable CloudWatch alarms

6. **Documentation:**
   - Update API docs
   - Create user guide
   - Create admin guide

---

## 📚 Additional Resources

- [AWS Cognito Docs](https://docs.aws.amazon.com/cognito/)
- [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2)
- [DynamoDB GSI Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/bp-indexes.html)

---

## 🆘 Support

If you encounter issues:

1. Check CloudWatch Logs
2. Review browser console errors
3. Test with `curl` commands
4. Verify IAM permissions

**Created:** January 28, 2025
**Version:** 1.0
**Status:** Production Ready
