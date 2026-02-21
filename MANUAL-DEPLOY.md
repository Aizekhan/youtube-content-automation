# Manual Deployment Guide

## Problem
GitHub Actions is NOT deploying frontend files to production server (n8n-creator.space / 3.75.97.188)

## Evidence
```bash
# Current navigation.js on production MISSING Topics Queue link
curl -k https://n8n-creator.space/js/navigation.js | grep -A2 "Content.html"
# Shows: Content → Costs (NO Topics Queue between them)

# Local navigation.js HAS Topics Queue link
cat js/navigation.js | grep -A2 "Content.html"
# Shows: Content → Topics Queue → Costs ✅
```

## Root Cause Analysis

### Possible Issues:
1. **GitHub Actions workflow not triggering**
   - Check: https://github.com/Aizekhan/youtube-content-automation/actions
   - Look for "Deploy to Production" runs

2. **SSH_KEY secret expired or incorrect**
   - Workflow uses `secrets.SSH_KEY` to connect to ubuntu@3.75.97.188
   - If SSH auth fails, files won't copy

3. **File detection logic failing**
   - Workflow uses: `git diff --name-only HEAD^ HEAD | grep -E "\.(html|css|js)$"`
   - May not detect changes in some commits

## Solution Options

### Option 1: Check GitHub Actions (RECOMMENDED)
1. Open: https://github.com/Aizekhan/youtube-content-automation/actions
2. Find latest "Deploy to Production" workflow run
3. Check logs for errors
4. If no runs → workflow not triggering!
5. If failed → check error message (likely SSH key issue)

### Option 2: Manual SCP Deployment (if you have SSH access)
```bash
# From your local machine where SSH key works:
cd E:/youtube-content-automation

# Deploy navigation.js (most critical)
scp js/navigation.js ubuntu@3.75.97.188:/home/ubuntu/web-admin/html/js/

# Deploy topics-manager files
scp topics-manager.html ubuntu@3.75.97.188:/home/ubuntu/web-admin/html/
scp js/topics-manager.js ubuntu@3.75.97.188:/home/ubuntu/web-admin/html/js/
scp js/auth.js ubuntu@3.75.97.188:/home/ubuntu/web-admin/html/js/

# Deploy all updated HTML files
scp index.html dashboard.html channels.html content.html costs.html audio-library.html settings.html \
    ubuntu@3.75.97.188:/home/ubuntu/web-admin/html/
```

### Option 3: Fix GitHub Actions Secrets
1. Go to: https://github.com/Aizekhan/youtube-content-automation/settings/secrets/actions
2. Update `SSH_KEY` secret with working private key for ubuntu@3.75.97.188
3. Verify other secrets exist:
   - AWS_ACCESS_KEY_ID
   - AWS_SECRET_ACCESS_KEY
   - SSH_KEY
   - TELEGRAM_BOT_TOKEN (optional)
   - TELEGRAM_CHAT_ID (optional)

### Option 4: Trigger Manual Deployment via GitHub Actions
1. Go to: https://github.com/Aizekhan/youtube-content-automation/actions/workflows/deploy-production.yml
2. Click "Run workflow" button (top right)
3. Select branch: master
4. Click green "Run workflow" button
5. Watch progress in Actions tab

## Verification After Deployment

```bash
# Check navigation.js has Topics Queue
curl -k https://n8n-creator.space/js/navigation.js | grep -A5 "Content"

# Should show:
# <a href="content.html" class="nav-link">
#     <i class="bi bi-file-earmark-text"></i> Content
# </a>
# <a href="topics-manager.html" class="nav-link">
#     <i class="bi bi-list-check"></i> Topics Queue
# </a>
```

## Files That Need Deployment

### Critical (Topics Manager):
- `js/navigation.js` - Has Topics Queue link
- `topics-manager.html` - Topics Manager page
- `js/topics-manager.js` - Topics Manager logic with AuthManager
- `js/auth.js` - Authentication (if not already deployed)

### Updated (cache-busting versions):
- `index.html`
- `dashboard.html`
- `channels.html`
- `content.html`
- `costs.html`
- `audio-library.html`
- `settings.html`

## Next Steps

1. **FIRST**: Check GitHub Actions status
2. **IF working**: Just wait for auto-deployment
3. **IF failing**: Check logs for SSH errors
4. **IF not running**: Manually trigger workflow or use SCP

## Important Notes

- Production domain: **n8n-creator.space** (points to 3.75.97.188)
- Lambda functions ARE deployed and working ✅
- Only frontend files need deployment
- SSL certificate is expired (use -k with curl or http://)
