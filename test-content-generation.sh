#!/bin/bash
# Quick test script for content generation
# Starts execution and monitors until completion

REGION="eu-central-1"
STATE_MACHINE="arn:aws:states:eu-central-1:599297130956:stateMachine:ContentGenerator"
USER_ID="c334d862-4031-7097-4207-84856b59d3ed"
CHANNEL_ID="UCRmO5HB89GW_zjX3dJACfzw"

TIMESTAMP=$(date +%s)
EXEC_NAME="quick-test-$TIMESTAMP"

echo "=== STARTING CONTENT GENERATION TEST ==="
echo "Execution name: $EXEC_NAME"
echo ""

# Start execution
EXEC_ARN=$(aws stepfunctions start-execution \
    --state-machine-arn "$STATE_MACHINE" \
    --name "$EXEC_NAME" \
    --input "{\"user_id\":\"$USER_ID\",\"selected_channels\":[\"$CHANNEL_ID\"]}" \
    --region "$REGION" \
    --query 'executionArn' \
    --output text)

echo "Execution started: $EXEC_ARN"
echo "Expected duration: 7-9 minutes"
echo ""

# Monitor progress
echo "Monitoring progress (checking every 30 seconds)..."
for i in {1..20}; do
    sleep 30

    STATUS=$(aws stepfunctions describe-execution \
        --execution-arn "$EXEC_ARN" \
        --region "$REGION" \
        --query 'status' \
        --output text)

    ELAPSED=$((i * 30))
    echo "[$ELAPSED s] Status: $STATUS"

    if [ "$STATUS" != "RUNNING" ]; then
        echo ""
        echo "=== EXECUTION COMPLETED ==="

        # Get full results
        aws stepfunctions describe-execution \
            --execution-arn "$EXEC_ARN" \
            --region "$REGION" \
            --output json | python -c "
import json, sys, datetime
d = json.load(sys.stdin)
start = datetime.datetime.fromisoformat(d['startDate'].replace('Z', '+00:00'))
stop = datetime.datetime.fromisoformat(d['stopDate'].replace('Z', '+00:00'))
duration = (stop - start).total_seconds()
print(f\"Status: {d['status']}\")
print(f\"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)\")
if 'output' in d:
    output = json.loads(d['output'])
    print(f\"Output: {json.dumps(output, indent=2)}\")
"
        exit 0
    fi
done

echo ""
echo "Test still running after 10 minutes. Check manually:"
echo "aws stepfunctions describe-execution --execution-arn $EXEC_ARN --region $REGION"
