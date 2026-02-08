#!/bin/bash
# Production Backup Script for n8n-creator.space
# Date: $(date +%Y-%m-%d)

BACKUP_DATE=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="backups/production-$BACKUP_DATE"
SERVER_USER="ubuntu"
SERVER_IP="3.75.97.188"
SSH_KEY="/tmp/aws-key.pem"
REMOTE_PATH="/home/ubuntu/n8n-docker/html"

echo "🔄 Starting production backup: $BACKUP_DATE"
echo "================================================"

# Create backup directory
mkdir -p "$BACKUP_DIR"
mkdir -p "$BACKUP_DIR/html"
mkdir -p "$BACKUP_DIR/docs"

echo "📥 Downloading HTML files from production..."

# List of main HTML files to backup
FILES=(
    "index.html"
    "dashboard.html"
    "content.html"
    "channels.html"
    "costs.html"
    "prompts-editor.html"
    "settings.html"
    "audio-library.html"
    "documentation.html"
)

# Download each HTML file
for file in "${FILES[@]}"; do
    echo "  → $file"
    scp -i "$SSH_KEY" "${SERVER_USER}@${SERVER_IP}:${REMOTE_PATH}/${file}" "$BACKUP_DIR/html/" 2>/dev/null || echo "    ⚠ Failed to download $file"
done

# Download CSS directory
echo "📁 Downloading CSS files..."
scp -i "$SSH_KEY" -r "${SERVER_USER}@${SERVER_IP}:${REMOTE_PATH}/css" "$BACKUP_DIR/html/" 2>/dev/null || echo "  ⚠ Failed to download CSS"

# Download JS directory
echo "📁 Downloading JS files..."
scp -i "$SSH_KEY" -r "${SERVER_USER}@${SERVER_IP}:${REMOTE_PATH}/js" "$BACKUP_DIR/html/" 2>/dev/null || echo "  ⚠ Failed to download JS"

# Download favicon if exists
echo "🎨 Downloading favicon..."
scp -i "$SSH_KEY" "${SERVER_USER}@${SERVER_IP}:${REMOTE_PATH}/favicon.png" "$BACKUP_DIR/html/" 2>/dev/null || echo "  ⚠ No favicon found"

# Download documentation if exists
echo "📚 Downloading documentation..."
scp -i "$SSH_KEY" -r "${SERVER_USER}@${SERVER_IP}:${REMOTE_PATH}/docs" "$BACKUP_DIR/" 2>/dev/null || echo "  ⚠ No docs folder found"

# Create backup manifest
echo "📝 Creating backup manifest..."
cat > "$BACKUP_DIR/MANIFEST.txt" << EOF
Production Backup Manifest
===========================
Date: $BACKUP_DATE
Source: n8n-creator.space ($SERVER_IP)
Remote Path: $REMOTE_PATH

Files Backed Up:
EOF

# List all files in backup
find "$BACKUP_DIR/html" -type f >> "$BACKUP_DIR/MANIFEST.txt"

# Count files
FILE_COUNT=$(find "$BACKUP_DIR/html" -type f | wc -l)

echo ""
echo "✅ Backup completed!"
echo "================================================"
echo "📦 Backup location: $BACKUP_DIR"
echo "📊 Total files backed up: $FILE_COUNT"
echo "💾 Backup size: $(du -sh "$BACKUP_DIR" | cut -f1)"
echo ""
echo "To restore this backup:"
echo "  cp -r $BACKUP_DIR/html/* ./"
echo ""
