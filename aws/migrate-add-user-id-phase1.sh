#!/bin/bash
# ============================================
# DATABASE MIGRATION - Phase 1
# Add user_id field to critical tables
# ============================================

set -e  # Exit on error

REGION="eu-central-1"
ADMIN_USER_ID="admin-legacy-user"  # Default user for existing data

echo "🗄️  Database Migration - Phase 1: Critical Tables"
echo "=================================================="
echo ""
echo "⚠️  WARNING: This will modify production tables!"
echo "   - YouTubeCredentials (CRITICAL - OAuth tokens)"
echo "   - ChannelConfigs"
echo ""
read -p "Have you backed up the database? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "❌ Backup confirmation required. Exiting."
    exit 1
fi

echo ""
echo "Starting migration..."
echo ""

# ============================================
# Step 1: Add GSI to YouTubeCredentials
# ============================================
echo "📋 Step 1: Adding user_id GSI to YouTubeCredentials..."

aws dynamodb update-table \
    --table-name YouTubeCredentials \
    --attribute-definitions AttributeName=user_id,AttributeType=S \
    --global-secondary-index-updates \
        '[{
            "Create": {
                "IndexName": "user_id-index",
                "KeySchema": [
                    {"AttributeName": "user_id", "KeyType": "HASH"}
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 5,
                    "WriteCapacityUnits": 5
                }
            }
        }]' \
    --region $REGION 2>/dev/null || echo "  (GSI may already exist)"

echo "✅ GSI creation initiated for YouTubeCredentials"
echo "   Waiting for index to build..."

# Wait for table to be active
aws dynamodb wait table-exists --table-name YouTubeCredentials --region $REGION

echo "✅ YouTubeCredentials table ready"
echo ""

# ============================================
# Step 2: Update existing YouTubeCredentials records
# ============================================
echo "📋 Step 2: Adding user_id to existing YouTubeCredentials records..."

# Create Python script to update records
cat > /tmp/migrate_youtube_creds.py << 'PYTHON_SCRIPT'
import boto3
import sys
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
table = dynamodb.Table('YouTubeCredentials')

admin_user_id = sys.argv[1] if len(sys.argv) > 1 else 'admin-legacy-user'

print(f"Scanning YouTubeCredentials table...")

# Scan all items
response = table.scan()
items = response.get('Items', [])

# Handle pagination
while 'LastEvaluatedKey' in response:
    response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
    items.extend(response.get('Items', []))

print(f"Found {len(items)} records")

updated_count = 0
skipped_count = 0

for item in items:
    channel_id = item.get('channel_id')

    # Check if user_id already exists
    if 'user_id' in item and item['user_id']:
        print(f"  ⏭️  Skipping {channel_id} - already has user_id")
        skipped_count += 1
        continue

    # Add user_id field
    try:
        table.update_item(
            Key={'channel_id': channel_id},
            UpdateExpression='SET user_id = :uid, updated_at = :updated',
            ExpressionAttributeValues={
                ':uid': admin_user_id,
                ':updated': datetime.utcnow().isoformat() + 'Z'
            }
        )
        print(f"  ✅ Updated {channel_id}")
        updated_count += 1
    except Exception as e:
        print(f"  ❌ Error updating {channel_id}: {e}")

print(f"\n✅ Migration complete:")
print(f"   Updated: {updated_count}")
print(f"   Skipped: {skipped_count}")
print(f"   Total: {len(items)}")
PYTHON_SCRIPT

python3 /tmp/migrate_youtube_creds.py "$ADMIN_USER_ID"

echo ""

# ============================================
# Step 3: Add GSI to ChannelConfigs
# ============================================
echo "📋 Step 3: Adding user_id GSI to ChannelConfigs..."

aws dynamodb update-table \
    --table-name ChannelConfigs \
    --attribute-definitions \
        AttributeName=user_id,AttributeType=S \
        AttributeName=channel_id,AttributeType=S \
    --global-secondary-index-updates \
        '[{
            "Create": {
                "IndexName": "user_id-channel_id-index",
                "KeySchema": [
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "channel_id", "KeyType": "RANGE"}
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 5,
                    "WriteCapacityUnits": 5
                }
            }
        }]' \
    --region $REGION 2>/dev/null || echo "  (GSI may already exist)"

echo "✅ GSI creation initiated for ChannelConfigs"
echo "   Waiting for index to build..."

aws dynamodb wait table-exists --table-name ChannelConfigs --region $REGION

echo "✅ ChannelConfigs table ready"
echo ""

# ============================================
# Step 4: Update existing ChannelConfigs records
# ============================================
echo "📋 Step 4: Adding user_id to existing ChannelConfigs records..."

# Create Python script to update records
cat > /tmp/migrate_channel_configs.py << 'PYTHON_SCRIPT'
import boto3
import sys
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
table = dynamodb.Table('ChannelConfigs')

admin_user_id = sys.argv[1] if len(sys.argv) > 1 else 'admin-legacy-user'

print(f"Scanning ChannelConfigs table...")

# Scan all items
response = table.scan()
items = response.get('Items', [])

# Handle pagination
while 'LastEvaluatedKey' in response:
    response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
    items.extend(response.get('Items', []))

print(f"Found {len(items)} records")

updated_count = 0
skipped_count = 0

for item in items:
    config_id = item.get('config_id')
    channel_id = item.get('channel_id', 'unknown')

    # Check if user_id already exists
    if 'user_id' in item and item['user_id']:
        print(f"  ⏭️  Skipping {channel_id} - already has user_id")
        skipped_count += 1
        continue

    # Add user_id field
    try:
        table.update_item(
            Key={'config_id': config_id},
            UpdateExpression='SET user_id = :uid, updated_at = :updated',
            ExpressionAttributeValues={
                ':uid': admin_user_id,
                ':updated': datetime.utcnow().isoformat() + 'Z'
            }
        )
        print(f"  ✅ Updated {channel_id} (config: {config_id})")
        updated_count += 1
    except Exception as e:
        print(f"  ❌ Error updating {config_id}: {e}")

print(f"\n✅ Migration complete:")
print(f"   Updated: {updated_count}")
print(f"   Skipped: {skipped_count}")
print(f"   Total: {len(items)}")
PYTHON_SCRIPT

python3 /tmp/migrate_channel_configs.py "$ADMIN_USER_ID"

echo ""

# ============================================
# Summary
# ============================================
echo "=================================================="
echo "✅ Phase 1 Migration Complete!"
echo "=================================================="
echo ""
echo "📊 Summary:"
echo "   ✅ YouTubeCredentials: user_id GSI created"
echo "   ✅ YouTubeCredentials: Records updated with user_id"
echo "   ✅ ChannelConfigs: user_id-channel_id GSI created"
echo "   ✅ ChannelConfigs: Records updated with user_id"
echo ""
echo "⚠️  All existing data assigned to: $ADMIN_USER_ID"
echo ""
echo "📋 Next Steps:"
echo "   1. Update Lambda functions to use user_id"
echo "   2. Test with admin user"
echo "   3. Run Phase 2 migration (remaining tables)"
echo ""
echo "🔍 Verify migration:"
echo "   aws dynamodb scan --table-name YouTubeCredentials --region $REGION --max-items 5"
echo "   aws dynamodb scan --table-name ChannelConfigs --region $REGION --max-items 5"
echo ""
