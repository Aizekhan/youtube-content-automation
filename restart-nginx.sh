#!/bin/bash

# Restart nginx to clear cache and reload files
echo "Restarting nginx..."
sudo systemctl restart nginx

# Wait a moment
sleep 2

# Check nginx status
sudo systemctl status nginx --no-pager | head -5

echo "Nginx restarted successfully!"
