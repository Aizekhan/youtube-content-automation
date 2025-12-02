#!/bin/bash
# Deploy Lambda Functions - CI/CD Script
# Week 4 Issue #25

set -e  # Exit on error

echo "========================================="
echo "Lambda Deployment Script"
echo "========================================="

# Configuration
REGION="eu-central-1"
LAMBDA_DIR="aws/lambda"

# Lambda functions to deploy
LAMBDAS=(
    "content-narrative"
    "content-audio-tts"
    "content-save-result"
    "content-theme-agent"
    "content-get-channels"
    "content-video-assembly"
    "dashboard-content"
    "dashboard-costs"
    "dashboard-monitoring"
    "prompts-api"
)

# Deploy Lambda Layer (shared utilities)
deploy_layer() {
    echo ""
    echo "📦 Deploying Lambda Layer (shared utilities)..."

    cd aws/lambda/shared

    # Create zip
    if [ -f shared-utils.zip ]; then
        rm shared-utils.zip
    fi

    zip -r shared-utils.zip *.py -x "__pycache__/*" -x "*.pyc"

    # Publish layer
    LAYER_VERSION=$(aws lambda publish-layer-version \
        --layer-name shared-utilities \
        --description "Shared utilities for YouTube Content Automation (CI/CD)" \
        --zip-file fileb://shared-utils.zip \
        --compatible-runtimes python3.11 \
        --region $REGION \
        --query 'Version' \
        --output text)

    echo "✅ Published layer version: $LAYER_VERSION"

    cd ../../..

    echo $LAYER_VERSION
}

# Deploy individual Lambda function
deploy_lambda() {
    local FUNCTION_NAME=$1
    local LAMBDA_PATH="$LAMBDA_DIR/$FUNCTION_NAME"

    echo ""
    echo "🚀 Deploying $FUNCTION_NAME..."

    cd $LAMBDA_PATH

    # Create deployment package
    if [ -f function.zip ]; then
        rm function.zip
    fi

    # Check if lambda_function.py exists
    if [ ! -f lambda_function.py ]; then
        echo "⚠️  Skipping $FUNCTION_NAME - no lambda_function.py found"
        cd ../../..
        return
    fi

    # Zip the function
    zip function.zip lambda_function.py

    # Add any additional files if they exist
    if [ -f config_merger.py ]; then
        zip function.zip config_merger.py
    fi
    if [ -f mega_config_merger.py ]; then
        zip function.zip mega_config_merger.py
    fi
    if [ -f mega_prompt_builder.py ]; then
        zip function.zip mega_prompt_builder.py
    fi
    if [ -f response_extractor.py ]; then
        zip function.zip response_extractor.py
    fi
    if [ -f ssml_validator.py ]; then
        zip function.zip ssml_validator.py
    fi
    if [ -f ssml_generator.py ]; then
        zip function.zip ssml_generator.py
    fi

    # Deploy to AWS
    aws lambda update-function-code \
        --function-name $FUNCTION_NAME \
        --zip-file fileb://function.zip \
        --region $REGION \
        --output text \
        --query 'LastModified'

    echo "✅ Deployed $FUNCTION_NAME"

    # Clean up
    rm function.zip

    cd ../../..
}

# Main deployment flow
main() {
    echo "Starting deployment..."
    echo "Region: $REGION"
    echo ""

    # Deploy shared Lambda Layer
    LAYER_VERSION=$(deploy_layer)

    # Update Lambda functions to use new layer version
    echo ""
    echo "📝 Updating Lambda functions to use layer version $LAYER_VERSION..."

    LAYER_ARN="arn:aws:lambda:$REGION:$(aws sts get-caller-identity --query Account --output text):layer:shared-utilities:$LAYER_VERSION"

    for LAMBDA in "${LAMBDAS[@]}"; do
        echo "  Updating $LAMBDA to use layer version $LAYER_VERSION..."
        aws lambda update-function-configuration \
            --function-name $LAMBDA \
            --layers $LAYER_ARN \
            --region $REGION \
            --output text \
            --query 'LastModified' || echo "  ⚠️  Failed to update $LAMBDA (may not exist)"
    done

    # Deploy each Lambda function
    echo ""
    echo "🚀 Deploying Lambda functions..."

    DEPLOYED=0
    FAILED=0

    for LAMBDA in "${LAMBDAS[@]}"; do
        if deploy_lambda $LAMBDA; then
            ((DEPLOYED++))
        else
            ((FAILED++))
        fi
    done

    echo ""
    echo "========================================="
    echo "Deployment Summary"
    echo "========================================="
    echo "✅ Successfully deployed: $DEPLOYED Lambda functions"
    echo "❌ Failed: $FAILED"
    echo "📦 Layer version: $LAYER_VERSION"
    echo ""

    if [ $FAILED -gt 0 ]; then
        echo "⚠️  Some deployments failed. Check logs above."
        exit 1
    else
        echo "✅ All deployments successful!"
    fi
}

# Run main
main
