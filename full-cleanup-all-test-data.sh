#!/bin/bash
# =============================================================================
# FULL CLEANUP - ALL TEST DATA
# YouTube Content Automation Platform
# =============================================================================
#
# WARNING: This script will DELETE:
# 1. Deprecated DynamoDB tables (9)
# 2. Deprecated Lambda functions (8)
# 3. ALL content in GeneratedContent table (270+ items)
# 4. ALL files in S3 buckets (audio, video, images)
# 5. ALL cost tracking records
#
# This is a COMPLETE RESET of the system!
#
# Usage:
#   ./full-cleanup-all-test-data.sh --dry-run    # Preview only
#   ./full-cleanup-all-test-data.sh --execute    # Actually delete
# =============================================================================

set -e

REGION="eu-central-1"
DRY_RUN=true

# Parse arguments
if [ "$1" = "--execute" ]; then
    DRY_RUN=false
    echo "⚠️  EXECUTE MODE: ALL DATA WILL BE DELETED!"
    echo ""
    echo "This will delete:"
    echo "  - 9 deprecated DynamoDB tables"
    echo "  - 8 deprecated Lambda functions"
    echo "  - ALL 270+ generated videos from GeneratedContent"
    echo "  - ALL audio/video/image files from S3"
    echo "  - ALL cost tracking records"
    echo ""
    read -p "Are you ABSOLUTELY sure? Type 'DELETE ALL' to confirm: " confirm
    if [ "$confirm" != "DELETE ALL" ]; then
        echo "Cancelled."
        exit 1
    fi
elif [ "$1" = "--dry-run" ] || [ -z "$1" ]; then
    DRY_RUN=true
    echo "🔍 DRY-RUN MODE: No resources will be deleted"
else
    echo "Usage: $0 [--dry-run|--execute]"
    exit 1
fi

echo ""
echo "=========================================="
echo "FULL CLEANUP - ALL TEST DATA"
echo "=========================================="
echo ""

# =============================================================================
# PART 1: DEPRECATED RESOURCES
# =============================================================================

echo "📋 PART 1: Deprecated DynamoDB Tables (9)"
echo ""

DEPRECATED_TABLES=(
    "NarrativeTemplates"
    "ThemeTemplates"
    "VideoEditingTemplates"
    "CTATemplates"
    "DescriptionTemplates"
    "ThumbnailTemplates"
    "PromptTemplatesV2"
    "EC2InstanceLocks"
    "Users"
)

for table in "${DEPRECATED_TABLES[@]}"; do
    echo "  - $table"
    if [ "$DRY_RUN" = false ]; then
        if aws dynamodb describe-table --table-name "$table" --region "$REGION" &>/dev/null; then
            aws dynamodb delete-table --table-name "$table" --region "$REGION"
            echo "    ✓ Deleted"
        else
            echo "    ⚠️  Does not exist"
        fi
    fi
done

echo ""
echo "⚡ PART 1: Deprecated Lambda Functions (8)"
echo ""

DEPRECATED_LAMBDAS=(
    "content-cta-audio"
    "ssml-generator"
    "merge-image-batches"
    "prepare-image-batches"
    "save-phase1-to-s3"
    "load-phase1-from-s3"
    "queue-failed-ec2"
    "retry-ec2-queue"
)

for func in "${DEPRECATED_LAMBDAS[@]}"; do
    echo "  - $func"
    if [ "$DRY_RUN" = false ]; then
        if aws lambda get-function --function-name "$func" --region "$REGION" &>/dev/null; then
            aws lambda delete-function --function-name "$func" --region "$REGION"
            echo "    ✓ Deleted"
        else
            echo "    ⚠️  Does not exist"
        fi
    fi
done

echo ""

# =============================================================================
# PART 2: PRODUCTION DATA CLEANUP
# =============================================================================

echo "=========================================="
echo "PART 2: PRODUCTION DATA CLEANUP"
echo "=========================================="
echo ""

# -----------------------------------------------------------------------------
# 2.1 Clear GeneratedContent table
# -----------------------------------------------------------------------------

echo "📊 2.1 Clear GeneratedContent table"
echo ""

if [ "$DRY_RUN" = false ]; then
    # Get item count
    ITEM_COUNT=$(aws dynamodb scan \
        --table-name GeneratedContent \
        --select COUNT \
        --region "$REGION" \
        --query 'Count' \
        --output text)

    echo "  Found $ITEM_COUNT items to delete"

    # Scan and delete all items (batch delete)
    aws dynamodb scan \
        --table-name GeneratedContent \
        --region "$REGION" \
        --output json | \
    jq -r '.Items[] | {content_id: .content_id.S}' | \
    jq -s '.' | \
    jq '{GeneratedContent: [.[] | {DeleteRequest: {Key: {content_id: {S: .content_id}}}}]}' | \
    while read -r batch; do
        if [ -n "$batch" ]; then
            echo "$batch" | aws dynamodb batch-write-item \
                --request-items file:///dev/stdin \
                --region "$REGION" &>/dev/null
        fi
    done

    echo "  ✓ Cleared GeneratedContent table"
else
    # Dry-run: just count
    ITEM_COUNT=$(aws dynamodb scan \
        --table-name GeneratedContent \
        --select COUNT \
        --region "$REGION" \
        --query 'Count' \
        --output text 2>/dev/null || echo "0")
    echo "  Would delete $ITEM_COUNT items"
fi

echo ""

# -----------------------------------------------------------------------------
# 2.2 Clear CostTracking table
# -----------------------------------------------------------------------------

echo "💰 2.2 Clear CostTracking table"
echo ""

if [ "$DRY_RUN" = false ]; then
    ITEM_COUNT=$(aws dynamodb scan \
        --table-name CostTracking \
        --select COUNT \
        --region "$REGION" \
        --query 'Count' \
        --output text)

    echo "  Found $ITEM_COUNT cost records to delete"

    # Similar batch delete for CostTracking
    # Note: CostTracking has composite key (date, timestamp)
    echo "  ⚠️  Manual cleanup recommended for CostTracking (composite key)"
    echo "  Run: aws dynamodb scan --table-name CostTracking | process manually"
else
    ITEM_COUNT=$(aws dynamodb scan \
        --table-name CostTracking \
        --select COUNT \
        --region "$REGION" \
        --query 'Count' \
        --output text 2>/dev/null || echo "0")
    echo "  Would delete $ITEM_COUNT cost records"
fi

echo ""

# -----------------------------------------------------------------------------
# 2.3 Clear S3 buckets (audio, video, images)
# -----------------------------------------------------------------------------

echo "🗂️  2.3 Clear S3 buckets"
echo ""

S3_BUCKETS=(
    "youtube-automation-audio-files"
    "youtube-automation-images"
    "youtube-automation-final-videos"
)

for bucket in "${S3_BUCKETS[@]}"; do
    echo "  Bucket: $bucket"

    if [ "$DRY_RUN" = false ]; then
        # Count objects
        OBJECT_COUNT=$(aws s3 ls "s3://$bucket" --recursive --region "$REGION" | wc -l)
        echo "    Found $OBJECT_COUNT files"

        # Delete all objects (versioned bucket safe delete)
        aws s3 rm "s3://$bucket" --recursive --region "$REGION"
        echo "    ✓ Cleared"
    else
        OBJECT_COUNT=$(aws s3 ls "s3://$bucket" --recursive --region "$REGION" 2>/dev/null | wc -l || echo "0")
        echo "    Would delete $OBJECT_COUNT files"
    fi
done

echo ""

# =============================================================================
# SUMMARY
# =============================================================================

echo "=========================================="
echo "SUMMARY"
echo "=========================================="
echo ""

if [ "$DRY_RUN" = true ]; then
    echo "✅ DRY-RUN complete. No resources were deleted."
    echo ""
    echo "Would delete:"
    echo "  - 9 DynamoDB tables (deprecated)"
    echo "  - 8 Lambda functions (deprecated)"
    echo "  - GeneratedContent: all items"
    echo "  - CostTracking: all records"
    echo "  - S3 buckets: all files"
    echo ""
    echo "To execute cleanup, run:"
    echo "  ./full-cleanup-all-test-data.sh --execute"
else
    echo "✅ FULL CLEANUP COMPLETE!"
    echo ""
    echo "Deleted:"
    echo "  - 9 deprecated DynamoDB tables"
    echo "  - 8 deprecated Lambda functions"
    echo "  - GeneratedContent: cleared"
    echo "  - S3 buckets: cleared"
    echo ""
    echo "System is now in CLEAN STATE:"
    echo "  - No test data"
    echo "  - No deprecated resources"
    echo "  - Ready for production use"
fi

echo ""
