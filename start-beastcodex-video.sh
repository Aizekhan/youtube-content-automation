#!/bin/bash
# Запуск генерації відео для BeastCodex в обхід Step Functions

echo "=== GENERATING BEASTCODEX ANIME VIDEO ==="
echo ""

CHANNEL_ID="UCq4jkW2gvAq_qUPcWzSgEig"
USER_ID="c334d862-4031-7097-4207-84856b59d3ed"
TOPIC="Тэнгу: Крылатый демон-ворон из японских гор"

echo "1. Generating narrative..."
aws lambda invoke \
  --function-name content-narrative \
  --region eu-central-1 \
  --cli-binary-format raw-in-base64-out \
  --payload "{\"user_id\":\"$USER_ID\",\"channel_id\":\"$CHANNEL_ID\",\"selected_topic\":\"$TOPIC\"}" \
  narrative-result.json

CONTENT_ID=$(cat narrative-result.json | python -c "import json,sys; print(json.load(sys.stdin)['content_id'])")
echo "Content ID: $CONTENT_ID"

echo ""
echo "2. Narrative generated successfully!"
echo "   - Check narrative-result.json for details"
echo ""
echo "Next steps (manual):"
echo "   - Start EC2 for images"
echo "   - Generate images"
echo "   - Start EC2 for audio"
echo "   - Generate audio"
echo "   - Assemble video"
