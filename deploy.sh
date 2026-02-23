#!/bin/bash
# Quick deploy script for frontend files

echo "🚀 Deploying to production..."

# Deploy topics-manager.js
echo "📦 Deploying topics-manager.js..."
scp -i n8n-key.pem -o StrictHostKeyChecking=no js/topics-manager.js ubuntu@3.75.97.188:/home/ubuntu/web-admin/html/js/

echo "✅ Deployment complete!"
echo ""
echo "🔗 Check: https://n8n-creator.space/topics-manager.html"
