#!/bin/bash

# Debug Test Runner - Deploy script
# This script deploys the debug-test-runner Lambda function to AWS

FUNCTION_NAME="debug-test-runner"
REGION="eu-central-1"
ROLE_ARN="arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-execution-role"

echo "🚀 Deploying $FUNCTION_NAME Lambda function..."

# Create deployment package
echo "📦 Creating deployment package..."
zip -r function.zip lambda_function.py

# Check if function exists
if aws lambda get-function --function-name $FUNCTION_NAME --region $REGION 2>/dev/null; then
    echo "📝 Updating existing function..."
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://function.zip \
        --region $REGION

    echo "⚙️  Updating function configuration..."
    aws lambda update-function-configuration \
        --function-name $FUNCTION_NAME \
        --timeout 300 \
        --memory-size 512 \
        --region $REGION
else
    echo "🆕 Creating new function..."
    aws lambda create-function \
        --function-name $FUNCTION_NAME \
        --runtime python3.11 \
        --role $ROLE_ARN \
        --handler lambda_function.lambda_handler \
        --zip-file fileb://function.zip \
        --timeout 300 \
        --memory-size 512 \
        --region $REGION
fi

# Create or update function URL configuration
echo "🔗 Setting up Function URL..."
aws lambda create-function-url-config \
    --function-name $FUNCTION_NAME \
    --auth-type NONE \
    --cors AllowOrigins="*",AllowMethods="POST,GET,OPTIONS",AllowHeaders="Content-Type" \
    --region $REGION 2>/dev/null || \
aws lambda update-function-url-config \
    --function-name $FUNCTION_NAME \
    --auth-type NONE \
    --cors AllowOrigins="*",AllowMethods="POST,GET,OPTIONS",AllowHeaders="Content-Type" \
    --region $REGION

# Get function URL
FUNCTION_URL=$(aws lambda get-function-url-config --function-name $FUNCTION_NAME --region $REGION --query 'FunctionUrl' --output text)

echo "✅ Deployment complete!"
echo "📍 Function URL: $FUNCTION_URL"
echo ""
echo "💡 Test the function with:"
echo "curl -X POST $FUNCTION_URL -H 'Content-Type: application/json' -d '{\"channel_id\": \"YOUR_CHANNEL_ID\"}'"

# Cleanup
rm function.zip
