# PowerShell script to deploy debug-test-runner via SSH to n8n server
# This uploads the Lambda function and deploys it using AWS CLI on the server

$SERVER = "ubuntu@3.75.97.188"
$SSH_KEY = "/tmp/aws-key.pem"  # Update with your SSH key path
$FUNCTION_NAME = "debug-test-runner"

Write-Host "🚀 Deploying $FUNCTION_NAME via SSH..." -ForegroundColor Cyan

# Create temporary directory on server
Write-Host "📁 Creating temporary directory on server..." -ForegroundColor Yellow
ssh -i $SSH_KEY $SERVER "mkdir -p /tmp/lambda-deploy/$FUNCTION_NAME"

# Upload Lambda function
Write-Host "📤 Uploading Lambda function..." -ForegroundColor Yellow
scp -i $SSH_KEY lambda_function.py "${SERVER}:/tmp/lambda-deploy/$FUNCTION_NAME/"

# Deploy using AWS CLI on server
Write-Host "🔧 Deploying to AWS Lambda..." -ForegroundColor Yellow
ssh -i $SSH_KEY $SERVER @"
cd /tmp/lambda-deploy/$FUNCTION_NAME

# Create deployment package
echo "📦 Creating deployment package..."
zip -r function.zip lambda_function.py

# Update Lambda function
echo "📝 Updating Lambda function..."
aws lambda update-function-code \
    --function-name $FUNCTION_NAME \
    --zip-file fileb://function.zip \
    --region eu-central-1

# Update configuration
echo "⚙️  Updating configuration..."
aws lambda update-function-configuration \
    --function-name $FUNCTION_NAME \
    --timeout 300 \
    --memory-size 512 \
    --region eu-central-1

# Get function URL
FUNCTION_URL=`$(aws lambda get-function-url-config \
    --function-name $FUNCTION_NAME \
    --region eu-central-1 \
    --query 'FunctionUrl' \
    --output text 2>/dev/null)

if [ -z "`$FUNCTION_URL" ]; then
    echo "🔗 Creating Function URL..."
    aws lambda create-function-url-config \
        --function-name $FUNCTION_NAME \
        --auth-type NONE \
        --cors AllowOrigins="*",AllowMethods="POST,GET,OPTIONS",AllowHeaders="Content-Type" \
        --region eu-central-1

    FUNCTION_URL=`$(aws lambda get-function-url-config \
        --function-name $FUNCTION_NAME \
        --region eu-central-1 \
        --query 'FunctionUrl' \
        --output text)
fi

echo "✅ Deployment complete!"
echo "📍 Function URL: `$FUNCTION_URL"

# Save URL to file
echo `$FUNCTION_URL > /tmp/lambda-deploy/$FUNCTION_NAME/function_url.txt

# Cleanup zip
rm function.zip
"@

# Download function URL
Write-Host "📥 Getting Function URL..." -ForegroundColor Yellow
scp -i $SSH_KEY "${SERVER}:/tmp/lambda-deploy/$FUNCTION_NAME/function_url.txt" ./function_url.txt

if (Test-Path ./function_url.txt) {
    $FunctionUrl = Get-Content ./function_url.txt
    Write-Host "✅ Deployment complete!" -ForegroundColor Green
    Write-Host "📍 Function URL: $FunctionUrl" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "💡 Update debug-dashboard.html with this URL" -ForegroundColor Yellow

    # Cleanup
    Remove-Item ./function_url.txt
} else {
    Write-Host "⚠️  Could not retrieve Function URL" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🧹 Cleaning up server..." -ForegroundColor Yellow
ssh -i $SSH_KEY $SERVER "rm -rf /tmp/lambda-deploy/$FUNCTION_NAME"

Write-Host "✅ Done!" -ForegroundColor Green
