#!/bin/bash
# Clear all items from CostTracking table

REGION="eu-central-1"
TABLE="CostTracking"

echo "Clearing $TABLE table..."
echo ""

# Get all items and delete them
aws dynamodb scan --table-name "$TABLE" --region "$REGION" --output text --query 'Items[*].[date.S, timestamp.S]' | \
while read date timestamp; do
  if [ -n "$date" ] && [ -n "$timestamp" ]; then
    aws dynamodb delete-item \
      --table-name "$TABLE" \
      --key "{\"date\":{\"S\":\"$date\"},\"timestamp\":{\"S\":\"$timestamp\"}}" \
      --region "$REGION" 2>/dev/null
    echo -n "."
  fi
done

echo ""
echo ""

# Verify
REMAINING=$(aws dynamodb scan --table-name "$TABLE" --select COUNT --region "$REGION" --query 'Count' --output text)
echo "Remaining items: $REMAINING"
echo ""

if [ "$REMAINING" = "0" ]; then
  echo "✓ CostTracking table cleared successfully!"
else
  echo "⚠️  Warning: $REMAINING items still remain"
fi
