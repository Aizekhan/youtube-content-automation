#!/bin/bash
# Delete CloudWatch log groups for deprecated Lambda functions

REGION="eu-central-1"

echo "Deleting CloudWatch log groups for deprecated Lambda functions..."
echo ""

DEPRECATED_LOG_GROUPS=(
    "/aws/lambda/content-cta-audio"
    "/aws/lambda/ssml-generator"
    "/aws/lambda/merge-image-batches"
    "/aws/lambda/prepare-image-batches"
    "/aws/lambda/save-phase1-to-s3"
    "/aws/lambda/load-phase1-from-s3"
    "/aws/lambda/queue-failed-ec2"
    "/aws/lambda/retry-ec2-queue"
    "/aws/lambda/content-audio-tts"
    "/aws/lambda/content-audio-polly"
    "/aws/lambda/content-theme-agent"
    "/aws/lambda/prompts-api"
    "/aws/lambda/ec2-sd35-control"
)

DELETED=0
NOT_FOUND=0

for log_group in "${DEPRECATED_LOG_GROUPS[@]}"; do
    echo "Checking: $log_group"

    if aws logs describe-log-groups --log-group-name-pattern "$log_group" --region "$REGION" 2>/dev/null | grep -q "$log_group"; then
        aws logs delete-log-group --log-group-name "$log_group" --region "$REGION" 2>/dev/null
        if [ $? -eq 0 ]; then
            echo "  ✓ Deleted"
            ((DELETED++))
        else
            echo "  ✗ Failed to delete"
        fi
    else
        echo "  - Does not exist"
        ((NOT_FOUND++))
    fi
done

echo ""
echo "=== Summary ==="
echo "Deleted: $DELETED log groups"
echo "Not found: $NOT_FOUND log groups"
echo ""
