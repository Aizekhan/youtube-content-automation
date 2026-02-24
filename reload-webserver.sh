#!/bin/bash
# Script to reload web server (tries nginx, apache2, httpd)

echo "Attempting to reload web server..."

# Try nginx
if sudo systemctl reload nginx 2>/dev/null; then
    echo "✓ Nginx reloaded successfully"
    exit 0
fi

# Try apache2 (Debian/Ubuntu)
if sudo systemctl reload apache2 2>/dev/null; then
    echo "✓ Apache2 reloaded successfully"
    exit 0
fi

# Try httpd (RedHat/CentOS)
if sudo systemctl reload httpd 2>/dev/null; then
    echo "✓ Httpd reloaded successfully"
    exit 0
fi

# Try n8n restart (if n8n serves frontend)
if sudo systemctl restart n8n 2>/dev/null; then
    echo "✓ N8N restarted successfully"
    exit 0
fi

echo "✗ Could not find web server service"
echo "Available services:"
systemctl list-units --type=service --state=running | grep -E 'nginx|apache|httpd|n8n' || echo "No web servers found"
exit 1
