#!/bin/bash
# Multi-Tenant Setup Script - AWS Cognito + Google OAuth
# Run this script to set up complete authentication system

set -e  # Exit on error

REGION="eu-central-1"
ACCOUNT_ID="599297130956"

echo "🚀 YouTube Content Automation - Multi-Tenant Setup"
echo "=================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# ==============================================
# Step 1: Create Users DynamoDB Table
# ==============================================
echo -e "${YELLOW}Step 1: Creating Users DynamoDB Table...${NC}"

aws dynamodb create-table \
    --table-name Users \
    --attribute-definitions \
        AttributeName=user_id,AttributeType=S \
        AttributeName=email,AttributeType=S \
    --key-schema \
        AttributeName=user_id,KeyType=HASH \
    --global-secondary-indexes \
        "[
            {
                \"IndexName\": \"email-index\",
                \"KeySchema\": [{\"AttributeName\":\"email\",\"KeyType\":\"HASH\"}],
                \"Projection\": {\"ProjectionType\":\"ALL\"}
            }
        ]" \
    --billing-mode PAY_PER_REQUEST \
    --region $REGION

echo -e "${GREEN}✅ Users table created${NC}"

# Wait for table to be active
echo "Waiting for table to be active..."
aws dynamodb wait table-exists --table-name Users --region $REGION
echo -e "${GREEN}✅ Users table is active${NC}"

# ==============================================
# Step 2: Create Cognito User Pool
# ==============================================
echo ""
echo -e "${YELLOW}Step 2: Creating Cognito User Pool...${NC}"

USER_POOL_ID=$(aws cognito-idp create-user-pool \
    --pool-name "YouTubeAutomationUsers" \
    --policies "PasswordPolicy={MinimumLength=8,RequireUppercase=true,RequireLowercase=true,RequireNumbers=true,RequireSymbols=false}" \
    --auto-verified-attributes email \
    --username-attributes email \
    --schema "Name=email,AttributeDataType=String,Required=true,Mutable=true" \
    --mfa-configuration OFF \
    --email-configuration "EmailSendingAccount=COGNITO_DEFAULT" \
    --region $REGION \
    --query 'UserPool.Id' \
    --output text)

echo -e "${GREEN}✅ User Pool created: ${USER_POOL_ID}${NC}"

# Save User Pool ID
echo $USER_POOL_ID > cognito-user-pool-id.txt

# ==============================================
# Step 3: Create Cognito User Pool Client
# ==============================================
echo ""
echo -e "${YELLOW}Step 3: Creating User Pool App Client...${NC}"

USER_POOL_CLIENT_ID=$(aws cognito-idp create-user-pool-client \
    --user-pool-id $USER_POOL_ID \
    --client-name "YouTubeAutomationWebApp" \
    --no-generate-secret \
    --allowed-o-auth-flows "code" "implicit" \
    --allowed-o-auth-scopes "openid" "email" "profile" \
    --allowed-o-auth-flows-user-pool-client \
    --supported-identity-providers "COGNITO" \
    --callback-urls "https://n8n-creator.space/callback.html" "http://localhost:8080/callback.html" \
    --logout-urls "https://n8n-creator.space/login.html" "http://localhost:8080/login.html" \
    --region $REGION \
    --query 'UserPoolClient.ClientId' \
    --output text)

echo -e "${GREEN}✅ App Client created: ${USER_POOL_CLIENT_ID}${NC}"

# Save Client ID
echo $USER_POOL_CLIENT_ID > cognito-client-id.txt

# ==============================================
# Step 4: Create Cognito Domain
# ==============================================
echo ""
echo -e "${YELLOW}Step 4: Creating Cognito Domain...${NC}"

DOMAIN_PREFIX="youtube-automation-$(date +%s)"

aws cognito-idp create-user-pool-domain \
    --domain $DOMAIN_PREFIX \
    --user-pool-id $USER_POOL_ID \
    --region $REGION

echo -e "${GREEN}✅ Cognito Domain created: ${DOMAIN_PREFIX}.auth.${REGION}.amazoncognito.com${NC}"

# Save domain
echo "https://${DOMAIN_PREFIX}.auth.${REGION}.amazoncognito.com" > cognito-domain.txt

# ==============================================
# Step 5: Output Configuration
# ==============================================
echo ""
echo -e "${GREEN}=================================================="
echo "✅ Multi-Tenant Infrastructure Setup Complete!"
echo "==================================================${NC}"
echo ""
echo "📋 Configuration Details:"
echo "------------------------"
echo "Region: $REGION"
echo "User Pool ID: $USER_POOL_ID"
echo "App Client ID: $USER_POOL_CLIENT_ID"
echo "Cognito Domain: https://${DOMAIN_PREFIX}.auth.${REGION}.amazoncognito.com"
echo ""
echo -e "${YELLOW}⚠️  NEXT STEPS:${NC}"
echo ""
echo "1. Configure Google OAuth Provider:"
echo "   - Go to: https://console.cloud.google.com/apis/credentials"
echo "   - Create OAuth 2.0 Client ID"
echo "   - Authorized redirect URI: https://${DOMAIN_PREFIX}.auth.${REGION}.amazoncognito.com/oauth2/idpresponse"
echo "   - Copy Client ID and Client Secret"
echo ""
echo "2. Add Google as Identity Provider in Cognito:"
echo "   aws cognito-idp create-identity-provider \\"
echo "     --user-pool-id $USER_POOL_ID \\"
echo "     --provider-name Google \\"
echo "     --provider-type Google \\"
echo "     --provider-details client_id=YOUR_GOOGLE_CLIENT_ID,client_secret=YOUR_GOOGLE_CLIENT_SECRET,authorize_scopes=\"openid email profile\" \\"
echo "     --attribute-mapping email=email,name=name \\"
echo "     --region $REGION"
echo ""
echo "3. Deploy frontend authentication:"
echo "   - Update js/auth.js with User Pool ID and Client ID"
echo "   - Deploy login.html and callback.html"
echo ""
echo -e "${GREEN}Configuration files saved:${NC}"
echo "  - cognito-user-pool-id.txt"
echo "  - cognito-client-id.txt"
echo "  - cognito-domain.txt"
echo ""
