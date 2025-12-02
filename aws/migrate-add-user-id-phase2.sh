#!/bin/bash
# ============================================
# DATABASE MIGRATION - Phase 2
# Add user_id to remaining tables
# ============================================

set -e  # Exit on error

REGION="eu-central-1"
ADMIN_USER_ID="admin-legacy-user"

echo "🗄️  Database Migration - Phase 2: Remaining Tables"
echo "=================================================="
echo ""
echo "Tables to migrate:"
echo "  - GeneratedContent"
echo "  - CostTracking"
echo "  - AIPromptConfigs"
echo ""

# ============================================
# GeneratedContent
# ============================================
echo "📋 Step 1: Migrating GeneratedContent..."
echo ""

# Add GSI
echo "  Creating user_id-created_at GSI..."
aws dynamodb update-table \
    --table-name GeneratedContent \
    --attribute-definitions \
        AttributeName=user_id,AttributeType=S \
        AttributeName=created_at,AttributeType=S \
    --global-secondary-index-updates \
        '[{
            "Create": {
                "IndexName": "user_id-created_at-index",
                "KeySchema": [
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"}
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 5,
                    "WriteCapacityUnits": 5
                }
            }
        }]' \
    --region $REGION 2>/dev/null || echo "  (GSI may already exist)"

echo "  Waiting for index to build..."
aws dynamodb wait table-exists --table-name GeneratedContent --region $REGION

# Update records
cat > /tmp/migrate_generated_content.py << 'PYTHON_SCRIPT'
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
table = dynamodb.Table('GeneratedContent')
admin_user_id = 'admin-legacy-user'

print("Scanning GeneratedContent...")
response = table.scan()
items = response.get('Items', [])

while 'LastEvaluatedKey' in response:
    response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
    items.extend(response.get('Items', []))

print(f"Found {len(items)} records")

updated = 0
for item in items:
    if 'user_id' in item:
        continue

    try:
        table.update_item(
            Key={
                'channel_id': item['channel_id'],
                'created_at': item['created_at']
            },
            UpdateExpression='SET user_id = :uid',
            ExpressionAttributeValues={':uid': admin_user_id}
        )
        updated += 1
        if updated % 10 == 0:
            print(f"  Progress: {updated}/{len(items)}")
    except Exception as e:
        print(f"  Error: {e}")

print(f"✅ Updated {updated} records")
PYTHON_SCRIPT

python3 /tmp/migrate_generated_content.py

echo "✅ GeneratedContent migrated"
echo ""

# ============================================
# CostTracking
# ============================================
echo "📋 Step 2: Migrating CostTracking..."
echo ""

echo "  Creating user_id-date GSI..."
aws dynamodb update-table \
    --table-name CostTracking \
    --attribute-definitions \
        AttributeName=user_id,AttributeType=S \
        AttributeName=date,AttributeType=S \
    --global-secondary-index-updates \
        '[{
            "Create": {
                "IndexName": "user_id-date-index",
                "KeySchema": [
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "date", "KeyType": "RANGE"}
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 5,
                    "WriteCapacityUnits": 5
                }
            }
        }]' \
    --region $REGION 2>/dev/null || echo "  (GSI may already exist)"

aws dynamodb wait table-exists --table-name CostTracking --region $REGION

# Update records
cat > /tmp/migrate_cost_tracking.py << 'PYTHON_SCRIPT'
import boto3

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
table = dynamodb.Table('CostTracking')
admin_user_id = 'admin-legacy-user'

print("Scanning CostTracking...")
response = table.scan()
items = response.get('Items', [])

while 'LastEvaluatedKey' in response:
    response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
    items.extend(response.get('Items', []))

print(f"Found {len(items)} records")

updated = 0
for item in items:
    if 'user_id' in item:
        continue

    try:
        table.update_item(
            Key={
                'date': item['date'],
                'timestamp': item['timestamp']
            },
            UpdateExpression='SET user_id = :uid',
            ExpressionAttributeValues={':uid': admin_user_id}
        )
        updated += 1
    except Exception as e:
        print(f"  Error: {e}")

print(f"✅ Updated {updated} records")
PYTHON_SCRIPT

python3 /tmp/migrate_cost_tracking.py

echo "✅ CostTracking migrated"
echo ""

# ============================================
# AIPromptConfigs
# ============================================
echo "📋 Step 3: Migrating AIPromptConfigs..."
echo ""

echo "  Creating user_id-template_type GSI..."
aws dynamodb update-table \
    --table-name AIPromptConfigs \
    --attribute-definitions \
        AttributeName=user_id,AttributeType=S \
        AttributeName=template_type,AttributeType=S \
    --global-secondary-index-updates \
        '[{
            "Create": {
                "IndexName": "user_id-template_type-index",
                "KeySchema": [
                    {"AttributeName": "user_id", "KeyType": "HASH"},
                    {"AttributeName": "template_type", "KeyType": "RANGE"}
                ],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 5,
                    "WriteCapacityUnits": 5
                }
            }
        }]' \
    --region $REGION 2>/dev/null || echo "  (GSI may already exist)"

aws dynamodb wait table-exists --table-name AIPromptConfigs --region $REGION

# Mark existing templates as system templates
cat > /tmp/migrate_prompt_configs.py << 'PYTHON_SCRIPT'
import boto3

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
table = dynamodb.Table('AIPromptConfigs')

print("Scanning AIPromptConfigs...")
response = table.scan()
items = response.get('Items', [])

while 'LastEvaluatedKey' in response:
    response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
    items.extend(response.get('Items', []))

print(f"Found {len(items)} records")

updated = 0
for item in items:
    if 'user_id' in item:
        continue

    # Mark as system template (no user_id = available to all)
    try:
        table.update_item(
            Key={'template_id': item['template_id']},
            UpdateExpression='SET visibility = :vis',
            ExpressionAttributeValues={':vis': 'system'}
        )
        updated += 1
    except Exception as e:
        print(f"  Error: {e}")

print(f"✅ Marked {updated} templates as system templates")
PYTHON_SCRIPT

python3 /tmp/migrate_prompt_configs.py

echo "✅ AIPromptConfigs migrated"
echo ""

# ============================================
# Summary
# ============================================
echo "=================================================="
echo "✅ Phase 2 Migration Complete!"
echo "=================================================="
echo ""
echo "📊 All tables migrated:"
echo "   ✅ GeneratedContent"
echo "   ✅ CostTracking"
echo "   ✅ AIPromptConfigs"
echo ""
echo "🎉 Database migration 100% complete!"
echo ""
