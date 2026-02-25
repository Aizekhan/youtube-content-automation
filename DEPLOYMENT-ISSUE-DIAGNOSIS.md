# Deployment Issue Diagnosis - Series Manager

## Problem Summary

Код Series Manager задеплоєно через GitHub Actions, але НЕ доступний на продакшені (https://n8n-creator.space/).

## Evidence

### 1. GitHub Actions - SUCCESS ✅
```
Run ID: 22335354288
Status: completed - success
Duration: 19s
Deployed files:
  - series-manager.html → /home/ubuntu/web-admin/html/
  - js/series-manager.js → /home/ubuntu/web-admin/html/js/
  - js/topics-manager.js → /home/ubuntu/web-admin/html/js/
  - index.html → /home/ubuntu/web-admin/html/
```

### 2. Production Check - FAILED ❌
```bash
# Checking for new function
curl -s "https://n8n-creator.space/js/topics-manager.js" | grep -c "openSeriesDashboard"
# Result: 0 (function not found)

# Checking series-manager.html
curl -s "https://n8n-creator.space/series-manager.html"
# Result: Connection timeout/error

# Ping test
ping n8n-creator.space
# Result: Request timed out (ICMP blocked - normal for AWS)
```

### 3. EC2 Instance Status
```
Current Instance: i-0f3cfc5f7f4845984
Name: n8n-server
IP: 3.75.97.188
State: running
```

**Previous Instance ID in workflow:** `i-0e8f24f8e88888cdb` (NOT FOUND - was terminated/replaced)

## Root Cause Hypotheses

### Hypothesis 1: Nginx Cache/Configuration Issue
- Files deployed to `/home/ubuntu/web-admin/html/`
- Nginx might serve from different location or have aggressive caching
- Nginx might not have been restarted after file deployment

### Hypothesis 2: CDN/Proxy Layer
- n8n-creator.space might use CloudFront or another CDN
- CDN cache not invalidated after deployment
- Files exist on server but CDN serves old version

### Hypothesis 3: Incorrect Deployment Path
- GitHub Actions deploys to `/home/ubuntu/web-admin/html/`
- Nginx might be configured to serve from different root (e.g., `/var/www/html/` or `/usr/share/nginx/html/`)

### Hypothesis 4: File Permissions
- Files deployed but nginx user (www-data/nginx) can't read them
- Need to check file ownership/permissions after SCP

## What GitHub Actions Does (from logs)

```bash
# For HTML files
scp -i ~/.ssh/id_rsa -o StrictHostKeyChecking=no "series-manager.html" ubuntu@3.75.97.188:/home/ubuntu/web-admin/html/

# For JS files
scp -i ~/.ssh/id_rsa -o StrictHostKeyChecking=no "js/topics-manager.js" ubuntu@3.75.97.188:/home/ubuntu/web-admin/html/js/
```

**Issue:** No nginx restart command after file deployment!

## Required Actions

### Action 1: Check Nginx Configuration
```bash
# SSH to server and check nginx config
ssh ubuntu@3.75.97.188
sudo cat /etc/nginx/sites-enabled/default | grep "root"
# Should show document root path
```

### Action 2: Verify Files on Server
```bash
# Check if files actually exist and have correct content
ls -lh /home/ubuntu/web-admin/html/series-manager.html
ls -lh /home/ubuntu/web-admin/html/js/series-manager.js
ls -lh /home/ubuntu/web-admin/html/js/topics-manager.js

# Check last 20 lines of topics-manager.js for new function
tail -20 /home/ubuntu/web-admin/html/js/topics-manager.js | grep "openSeriesDashboard"
```

### Action 3: Check File Permissions
```bash
# Check ownership
ls -l /home/ubuntu/web-admin/html/*.html
ls -l /home/ubuntu/web-admin/html/js/*.js

# Should be readable by nginx user (usually www-data or nginx)
```

### Action 4: Restart Nginx
```bash
# Clear any cache and reload
sudo systemctl restart nginx

# Or if using nginx cache
sudo rm -rf /var/cache/nginx/*
sudo systemctl reload nginx
```

### Action 5: Check CDN/CloudFront
```bash
# If CloudFront is used, invalidate cache
aws cloudfront create-invalidation --distribution-id DISTID --paths "/js/*" "/series-manager.html"
```

## Recommended Fix: Update GitHub Workflow

Add nginx restart step to `.github/workflows/deploy-frontend-manual.yml`:

```yaml
- name: Deploy Frontend files
  run: |
    echo "Deploying frontend files..."

    # ... existing SCP commands ...

    # NEW: Restart nginx after deployment
    echo "Restarting nginx..."
    ssh -i ~/.ssh/id_rsa -o StrictHostKeyChecking=no ubuntu@3.75.97.188 'sudo systemctl restart nginx'

    echo "✅ Frontend deployment completed!"
```

## Quick Test Commands

```bash
# 1. Check if workflow deployed files
gh run list --workflow=deploy-frontend-manual.yml --limit 3

# 2. Try accessing with cache bypass
curl -H "Cache-Control: no-cache" -H "Pragma: no-cache" "https://n8n-creator.space/js/topics-manager.js?v=$(date +%s)" | grep "openSeriesDashboard"

# 3. Check nginx error logs (if accessible)
aws ssm start-session --target i-0f3cfc5f7f4845984 --document-name AWS-StartInteractiveCommand --parameters command="sudo tail -50 /var/log/nginx/error.log"
```

## Current Status

- ✅ Code written and committed
- ✅ GitHub Actions deployment SUCCESS
- ❌ Files NOT accessible on production
- ❓ Nginx not restarted after deployment
- ❓ Possible CDN caching issue
- ❓ Need server access to diagnose further

## Next Steps

1. SSH access to server to verify file existence
2. Check nginx configuration
3. Restart nginx manually
4. Test if files become accessible
5. Update GitHub workflow to include nginx restart
6. Re-deploy with updated workflow
