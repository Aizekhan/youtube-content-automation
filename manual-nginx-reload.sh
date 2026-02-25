#!/bin/bash
# Manual nginx reload script
# Run this on the server: bash manual-nginx-reload.sh

echo "Reloading nginx..."
sudo systemctl reload nginx

if [ $? -eq 0 ]; then
    echo "✓ Nginx reloaded successfully!"
    echo "Now refresh your browser with Ctrl+Shift+R"
else
    echo "✗ Failed to reload nginx"
    echo "Try: sudo service nginx reload"
fi
