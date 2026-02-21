#!/bin/bash
# =============================================================================
# BACKUP AWS RESOURCES BEFORE CLEANUP
# YouTube Content Automation Platform
# =============================================================================
#
# This script backs up DynamoDB tables and Lambda function code
# before deleting deprecated resources.
#
# Usage:
#   ./backup-before-cleanup.sh
# =============================================================================

set -e

REGION="eu-central-1"
BACKUP_DIR="./backups/cleanup-$(date +%Y%m%d-%H%M%S)"

mkdir -p "$BACKUP_DIR/dynamodb"
mkdir -p "$BACKUP_DIR/lambda"

echo "=========================================="
echo "BACKUP BEFORE CLEANUP"
echo "=========================================="
echo ""
echo "Backup directory: $BACKUP_DIR"
echo ""

# =============================================================================
# 1. BACKUP DYNAMODB TABLES
# =============================================================================

echo "📋 1. Backing up DynamoDB tables..."
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
    echo "  Backing up $table..."

    # Check if table exists
    if aws dynamodb describe-table --table-name "$table" --region "$REGION" &>/dev/null; then
        # Scan entire table
        aws dynamodb scan \
            --table-name "$table" \
            --region "$REGION" \
            > "$BACKUP_DIR/dynamodb/${table}.json"

        # Get item count
        ITEM_COUNT=$(jq '.Items | length' "$BACKUP_DIR/dynamodb/${table}.json")
        echo "    ✓ Backed up ($ITEM_COUNT items)"
    else
        echo "    ⚠️  Table does not exist"
    fi
done

echo ""

# =============================================================================
# 2. BACKUP LAMBDA FUNCTIONS
# =============================================================================

echo "⚡ 2. Backing up Lambda function code..."
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
    echo "  Backing up $func..."

    # Check if function exists
    if aws lambda get-function --function-name "$func" --region "$REGION" &>/dev/null; then
        # Get function code URL
        CODE_URL=$(aws lambda get-function \
            --function-name "$func" \
            --region "$REGION" \
            --query 'Code.Location' \
            --output text)

        # Download deployment package
        curl -s "$CODE_URL" -o "$BACKUP_DIR/lambda/${func}.zip"

        # Get function configuration
        aws lambda get-function-configuration \
            --function-name "$func" \
            --region "$REGION" \
            > "$BACKUP_DIR/lambda/${func}-config.json"

        echo "    ✓ Backed up (code + config)"
    else
        echo "    ⚠️  Function does not exist"
    fi
done

echo ""

# =============================================================================
# 3. CREATE BACKUP MANIFEST
# =============================================================================

cat > "$BACKUP_DIR/MANIFEST.md" << EOF
# Backup Manifest

**Date:** $(date -u +"%Y-%m-%d %H:%M:%S UTC")
**Region:** $REGION
**Purpose:** Backup before deprecated resources cleanup

## DynamoDB Tables

$(for table in "${DEPRECATED_TABLES[@]}"; do
    if [ -f "$BACKUP_DIR/dynamodb/${table}.json" ]; then
        ITEM_COUNT=$(jq '.Items | length' "$BACKUP_DIR/dynamodb/${table}.json")
        echo "- **$table**: $ITEM_COUNT items"
    fi
done)

## Lambda Functions

$(for func in "${DEPRECATED_LAMBDAS[@]}"; do
    if [ -f "$BACKUP_DIR/lambda/${func}.zip" ]; then
        SIZE=$(du -h "$BACKUP_DIR/lambda/${func}.zip" | cut -f1)
        echo "- **$func**: $SIZE"
    fi
done)

## Restoration

To restore a DynamoDB table:
\`\`\`bash
aws dynamodb batch-write-item --request-items file://dynamodb/<table>.json
\`\`\`

To restore a Lambda function:
\`\`\`bash
aws lambda update-function-code \\
  --function-name <function-name> \\
  --zip-file fileb://lambda/<function-name>.zip
\`\`\`
EOF

echo "=========================================="
echo "BACKUP COMPLETE"
echo "=========================================="
echo ""
echo "Backup saved to: $BACKUP_DIR"
echo ""
echo "Contents:"
echo "  - dynamodb/: DynamoDB table scans"
echo "  - lambda/: Lambda deployment packages + configs"
echo "  - MANIFEST.md: Backup details"
echo ""
echo "Next steps:"
echo "  1. Review backed up data"
echo "  2. Run: ./cleanup-deprecated-resources.sh --dry-run"
echo "  3. Run: ./cleanup-deprecated-resources.sh --execute"
echo ""
