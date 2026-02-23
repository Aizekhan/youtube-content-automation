#!/bin/bash

# ==============================================================================
# MASTER CLEANUP SCRIPT
# ==============================================================================
# Complete removal of FLUX, SD3.5, Replicate, Vast.ai, Bedrock
# Keep ONLY ec2-zimage (Z-Image-Turbo)
#
# This script orchestrates all cleanup operations in the correct order
# ==============================================================================

set -e  # Exit on error

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="cleanup_log_${TIMESTAMP}.txt"

# Logging function
log() {
    echo "$1" | tee -a "$LOG_FILE"
}

log "========================================================================"
log "🚀 MASTER CLEANUP SCRIPT - Started at $(date)"
log "========================================================================"
log ""

# ==============================================================================
# CONFIRMATION
# ==============================================================================
log "⚠️  WARNING: This will perform DESTRUCTIVE operations:"
log "   - Delete AWS Lambda functions (ec2-sd35-control, ec2-flux-control)"
log "   - Delete Secrets Manager secrets"
log "   - Update ALL DynamoDB ChannelConfigs"
log "   - Modify 40+ code files"
log "   - Delete deprecated documentation"
log ""
read -p "Type 'DELETE FLUX AND SD35' to confirm: " CONFIRM

if [ "$CONFIRM" != "DELETE FLUX AND SD35" ]; then
    log "❌ Aborted by user"
    exit 1
fi

log ""
log "✅ Confirmed. Starting cleanup..."
log ""

# ==============================================================================
# STEP 1: Run AWS cleanup (Lambda, Secrets, DynamoDB)
# ==============================================================================
log "📋 STEP 1: AWS Resources Cleanup"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "cleanup-deprecated-providers.sh" ]; then
    log "   Running cleanup-deprecated-providers.sh..."
    bash cleanup-deprecated-providers.sh 2>&1 | tee -a "$LOG_FILE"
    log "   ✅ AWS cleanup completed"
else
    log "   ⚠️  cleanup-deprecated-providers.sh not found, skipping AWS cleanup"
fi

log ""

# ==============================================================================
# STEP 2: Clean Lambda function code
# ==============================================================================
log "📋 STEP 2: Lambda Code Cleanup"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "clean-lambda-code.py" ]; then
    log "   Running clean-lambda-code.py..."
    python clean-lambda-code.py 2>&1 | tee -a "$LOG_FILE"
    log "   ✅ Lambda code cleanup completed"
else
    log "   ⚠️  clean-lambda-code.py not found, skipping Lambda cleanup"
fi

log ""

# ==============================================================================
# STEP 3: Clean frontend code (JS, HTML)
# ==============================================================================
log "📋 STEP 3: Frontend Code Cleanup"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "clean-frontend-code.py" ]; then
    log "   Running clean-frontend-code.py..."
    python clean-frontend-code.py 2>&1 | tee -a "$LOG_FILE"
    log "   ✅ Frontend code cleanup completed"
else
    log "   ⚠️  clean-frontend-code.py not found, skipping frontend cleanup"
fi

log ""

# ==============================================================================
# STEP 4: Verify cleanup
# ==============================================================================
log "📋 STEP 4: Verification"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

log "   🔍 Searching for remaining references to deprecated providers..."
log ""

# Search for deprecated terms
DEPRECATED_TERMS=("flux" "sd35" "sd3.5" "sd3-5" "replicate" "vast-ai" "bedrock-sdxl")
REMAINING_REFERENCES=0

for term in "${DEPRECATED_TERMS[@]}"; do
    log "   Searching for '$term'..."
    matches=$(grep -ri "$term" \
        aws/lambda/ \
        js/ \
        *.html \
        --include="*.py" \
        --include="*.js" \
        --include="*.html" \
        2>/dev/null || true)

    if [ -n "$matches" ]; then
        count=$(echo "$matches" | wc -l)
        REMAINING_REFERENCES=$((REMAINING_REFERENCES + count))
        log "      ⚠️  Found $count references:"
        echo "$matches" | head -5 | while read line; do
            log "         $line"
        done
        if [ $count -gt 5 ]; then
            log "         ... and $((count - 5)) more"
        fi
    else
        log "      ✅ No references found"
    fi
done

log ""

if [ $REMAINING_REFERENCES -eq 0 ]; then
    log "   🎉 PERFECT! No deprecated provider references found!"
else
    log "   ⚠️  Found $REMAINING_REFERENCES remaining references"
    log "      These may be in comments, documentation, or backups"
fi

log ""

# ==============================================================================
# STEP 5: Check DynamoDB ChannelConfigs
# ==============================================================================
log "📋 STEP 5: DynamoDB Verification"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

log "   🔍 Checking ChannelConfigs providers..."

python3 << 'PYTHON_VERIFY'
import boto3
import sys

try:
    dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
    table = dynamodb.Table('ChannelConfigs')

    response = table.scan()
    items = response.get('Items', [])

    zimage_count = 0
    other_count = 0
    other_providers = []

    for item in items:
        provider = item.get('image_generation', {}).get('provider', 'not_set')
        if provider == 'ec2-zimage':
            zimage_count += 1
        else:
            other_count += 1
            other_providers.append((item.get('channel_name', 'Unknown'), provider))

    print(f"   📊 ChannelConfigs summary:")
    print(f"      ✅ ec2-zimage: {zimage_count}")
    print(f"      ⚠️  Other providers: {other_count}")

    if other_count > 0:
        print(f"\n   ⚠️  Channels with deprecated providers:")
        for name, provider in other_providers[:5]:
            print(f"      - {name[:30]:30} : {provider}")
        if len(other_providers) > 5:
            print(f"      ... and {len(other_providers) - 5} more")
        sys.exit(1)
    else:
        print(f"\n   🎉 All channels using ec2-zimage!")

except Exception as e:
    print(f"   ❌ DynamoDB check failed: {e}")
    sys.exit(1)
PYTHON_VERIFY

DB_CHECK_RESULT=$?

log ""

# ==============================================================================
# STEP 6: Git status
# ==============================================================================
log "📋 STEP 6: Git Changes Summary"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

log "   📝 Git status:"
git status --short 2>&1 | head -20 | tee -a "$LOG_FILE"

CHANGED_FILES=$(git status --short | wc -l)
log ""
log "   Total modified/deleted files: $CHANGED_FILES"

log ""

# ==============================================================================
# SUMMARY
# ==============================================================================
log "========================================================================"
log "✅ MASTER CLEANUP COMPLETED!"
log "========================================================================"
log ""
log "📊 Summary:"
log "   ✅ AWS resources cleaned (Lambda, Secrets, EC2 checks)"
log "   ✅ Lambda code cleaned (content-generate-images, content-narrative, etc.)"
log "   ✅ Frontend code cleaned (JS, HTML)"
log "   ✅ Documentation cleaned"
log "   ✅ DynamoDB ChannelConfigs updated"
log ""

if [ $REMAINING_REFERENCES -gt 0 ]; then
    log "⚠️  WARNINGS:"
    log "   - $REMAINING_REFERENCES deprecated references still found (check log)"
fi

if [ $DB_CHECK_RESULT -ne 0 ]; then
    log "   - Some channels still using deprecated providers"
fi

log ""
log "📋 NEXT STEPS:"
log "   1. Review changes: git diff"
log "   2. Test image generation with ec2-zimage"
log "   3. Deploy cleaned Lambda functions:"
log "      cd aws/lambda/content-generate-images && zip -r ../content-generate-images.zip . && aws lambda update-function-code --function-name content-generate-images --zip-file fileb://../content-generate-images.zip"
log "   4. Verify dashboard UI (no FLUX references)"
log "   5. Run test generation for one channel"
log "   6. Commit changes:"
log "      git add ."
log "      git commit -m 'chore: remove deprecated image providers (FLUX, SD3.5, Bedrock) - ec2-zimage only'"
log "      git push"
log ""
log "📄 Full log saved to: $LOG_FILE"
log ""
log "========================================================================"
log "🎉 Cleanup finished at $(date)"
log "========================================================================"
