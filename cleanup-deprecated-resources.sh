#!/bin/bash
# =============================================================================
# CLEANUP DEPRECATED AWS RESOURCES
# YouTube Content Automation Platform
# =============================================================================
#
# WARNING: This script will DELETE AWS resources!
# Make sure you have backups before running.
#
# Usage:
#   ./cleanup-deprecated-resources.sh --dry-run    # Preview only
#   ./cleanup-deprecated-resources.sh --execute    # Actually delete
# =============================================================================

set -e  # Exit on error

REGION="eu-central-1"
DRY_RUN=true

# Parse arguments
if [ "$1" = "--execute" ]; then
    DRY_RUN=false
    echo "⚠️  EXECUTE MODE: Resources will be DELETED!"
    read -p "Are you sure? Type 'DELETE' to confirm: " confirm
    if [ "$confirm" != "DELETE" ]; then
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
echo "DEPRECATED RESOURCES CLEANUP"
echo "=========================================="
echo ""

# =============================================================================
# 1. DYNAMODB TABLES (9 tables)
# =============================================================================

echo "📋 1. DynamoDB Tables to delete:"
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
        # Check if table exists
        if aws dynamodb describe-table --table-name "$table" --region "$REGION" &>/dev/null; then
            echo "    Deleting $table..."
            aws dynamodb delete-table --table-name "$table" --region "$REGION"
            echo "    ✓ Deleted"
        else
            echo "    ⚠️  Table does not exist (already deleted?)"
        fi
    fi
done

echo ""

# =============================================================================
# 2. LAMBDA FUNCTIONS (8 functions)
# =============================================================================

echo "⚡ 2. Lambda Functions to delete:"
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
        # Check if function exists
        if aws lambda get-function --function-name "$func" --region "$REGION" &>/dev/null; then
            echo "    Deleting $func..."
            aws lambda delete-function --function-name "$func" --region "$REGION"
            echo "    ✓ Deleted"
        else
            echo "    ⚠️  Function does not exist (already deleted?)"
        fi
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
echo "DynamoDB Tables: ${#DEPRECATED_TABLES[@]} tables"
echo "Lambda Functions: ${#DEPRECATED_LAMBDAS[@]} functions"
echo ""

if [ "$DRY_RUN" = true ]; then
    echo "✅ DRY-RUN complete. No resources were deleted."
    echo ""
    echo "To actually delete these resources, run:"
    echo "  ./cleanup-deprecated-resources.sh --execute"
else
    echo "✅ CLEANUP complete!"
    echo ""
    echo "Deleted:"
    echo "  - ${#DEPRECATED_TABLES[@]} DynamoDB tables"
    echo "  - ${#DEPRECATED_LAMBDAS[@]} Lambda functions"
    echo ""
    echo "⚠️  Note: CloudWatch Logs for deleted Lambdas are retained."
    echo "You can manually delete them if needed:"
    echo "  aws logs delete-log-group --log-group-name /aws/lambda/<function-name>"
fi

echo ""
