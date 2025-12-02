# Deploy Content Security Policy Headers - Week 2.4

**Date:** 2025-12-01
**File:** `nginx-security-headers-v2.conf`
**Target:** Web server (nginx)

---

## What This Does

Adds security headers to protect against:
- ✅ **XSS (Cross-Site Scripting)** - CSP controls script sources
- ✅ **Clickjacking** - X-Frame-Options prevents iframe embedding
- ✅ **MIME sniffing** - X-Content-Type-Options prevents content type confusion
- ✅ **Data leakage** - Referrer-Policy controls referrer info
- ✅ **Unwanted features** - Permissions-Policy disables unused browser APIs

---

## Deployment Options

### Option 1: Include in nginx site config (Recommended)

```bash
# 1. Upload security headers file to server
scp nginx-security-headers-v2.conf ubuntu@YOUR_SERVER:/tmp/

# 2. SSH to server
ssh ubuntu@YOUR_SERVER

# 3. Move to nginx config directory
sudo mv /tmp/nginx-security-headers-v2.conf /etc/nginx/conf.d/security-headers.conf

# 4. Edit your site config to include it
sudo nano /etc/nginx/sites-available/default

# Add this line inside the server{} block:
include /etc/nginx/conf.d/security-headers.conf;

# 5. Test configuration
sudo nginx -t

# 6. Reload nginx
sudo systemctl reload nginx
```

---

### Option 2: Add directly to site config

```bash
# 1. SSH to server
ssh ubuntu@YOUR_SERVER

# 2. Backup current config
sudo cp /etc/nginx/sites-available/default /etc/nginx/sites-available/default.backup

# 3. Edit site config
sudo nano /etc/nginx/sites-available/default

# 4. Add the security headers inside server{} block
#    (copy content from nginx-security-headers-v2.conf)

# 5. Test and reload
sudo nginx -t && sudo systemctl reload nginx
```

---

### Option 3: Docker/Docker Compose (if using containers)

```yaml
# docker-compose.yml
services:
  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx-security-headers-v2.conf:/etc/nginx/conf.d/security-headers.conf:ro
      - ./html:/usr/share/nginx/html:ro
    ports:
      - "80:80"
```

---

## CSP Policy Explained

### Allowed Sources

**Scripts:**
- ✅ `'self'` - Your own domain
- ✅ `accounts.google.com` - Google OAuth
- ✅ `cdn.jsdelivr.net`, `cdnjs.cloudflare.com` - CDN libraries
- ⚠️ `'unsafe-inline'`, `'unsafe-eval'` - Required for existing code (should be removed in future)

**Styles:**
- ✅ `'self'` - Your own stylesheets
- ✅ `fonts.googleapis.com` - Google Fonts
- ⚠️ `'unsafe-inline'` - Required for inline styles (should be removed in future)

**Images:**
- ✅ `'self'` - Your own images
- ✅ `https:` - Any HTTPS image (for S3 presigned URLs)
- ✅ `data:`, `blob:` - Base64 and blob images

**API Connections:**
- ✅ `'self'` - Your own API
- ✅ `*.lambda-url.eu-central-1.on.aws` - AWS Lambda Function URLs
- ✅ `*.s3.eu-central-1.amazonaws.com` - S3 buckets
- ✅ `accounts.google.com` - Google OAuth
- ✅ `cognito-idp.eu-central-1.amazonaws.com` - AWS Cognito

**Frames:**
- ✅ `accounts.google.com` - Google OAuth login iframe
- ❌ Everything else blocked

---

## Testing After Deployment

### 1. Check Headers with curl

```bash
curl -I https://YOUR_DOMAIN/

# Should see:
# Content-Security-Policy: default-src 'self'; ...
# X-Content-Type-Options: nosniff
# X-Frame-Options: DENY
# Referrer-Policy: strict-origin-when-cross-origin
```

### 2. Check in Browser DevTools

```javascript
// Open browser console (F12) and check Network tab
// Click on any request → Headers tab
// Should see security headers in Response Headers
```

### 3. Check CSP Violations

```javascript
// Open browser console (F12)
// Look for CSP violation reports
// Format: "Refused to load script from 'X' because it violates CSP"
```

### 4. Online Security Header Check

Visit: https://securityheaders.com/?q=YOUR_DOMAIN
Expected grade: **A** or **A+**

---

## Common Issues & Fixes

### Issue 1: Scripts Not Loading

**Symptom:** Console error: "Refused to load script... violates CSP"

**Fix:** Add the script source to CSP policy
```nginx
script-src 'self' 'unsafe-inline' https://new-cdn.com;
```

---

### Issue 2: Images Not Loading

**Symptom:** S3 images not displaying

**Fix:** Ensure `https:` is in `img-src` (allows all HTTPS images)
```nginx
img-src 'self' https: data: blob:;
```

---

### Issue 3: API Calls Failing

**Symptom:** Fetch/XHR requests blocked

**Fix:** Add API endpoint to `connect-src`
```nginx
connect-src 'self' https://your-api.example.com;
```

---

### Issue 4: Google OAuth Not Working

**Symptom:** Login popup blocked

**Fix:** Ensure Google domains in `frame-src` and `script-src`
```nginx
frame-src 'self' https://accounts.google.com;
script-src 'self' https://accounts.google.com;
```

---

## Monitoring CSP Violations

### Option 1: Browser Console

Check console for CSP violation warnings during testing

### Option 2: CSP Reporting (Future Enhancement)

Add reporting endpoint to CSP header:
```nginx
add_header Content-Security-Policy "
    default-src 'self';
    ...
    report-uri /csp-violation-report;
    report-to csp-endpoint;
";
```

Create Lambda function to receive and log CSP violation reports

---

## Security Improvements Over Time

### Phase 1: Current (Permissive)
- ✅ Deployed with `'unsafe-inline'` and `'unsafe-eval'`
- Reason: Existing code uses inline scripts
- Risk: Medium (still vulnerable to some XSS)

### Phase 2: Remove unsafe-inline (Future)
- Move all inline scripts to external .js files
- Use nonces or hashes for required inline scripts
- Risk: Low (most XSS vectors blocked)

### Phase 3: Remove unsafe-eval (Future)
- Replace dynamic code execution (eval, Function constructor)
- Use static code patterns
- Risk: Very Low (XSS nearly impossible)

---

## Rollback

If CSP breaks functionality:

```bash
# SSH to server
ssh ubuntu@YOUR_SERVER

# Remove security headers
sudo rm /etc/nginx/conf.d/security-headers.conf

# OR comment out include line in site config
sudo nano /etc/nginx/sites-available/default
# Comment: # include /etc/nginx/conf.d/security-headers.conf;

# Reload nginx
sudo systemctl reload nginx
```

---

## Verification Checklist

After deployment, verify:

- [ ] All pages load correctly (index, dashboard, channels, etc.)
- [ ] Google OAuth login works
- [ ] Content generation works (API calls succeed)
- [ ] Images load from S3
- [ ] Audio playback works
- [ ] No CSP violations in console (or only expected ones)
- [ ] Security headers present in all responses

---

## Next Steps

1. Deploy CSP headers to staging/test environment first
2. Test all functionality
3. Monitor for CSP violations
4. Deploy to production
5. Plan Phase 2: Remove `'unsafe-inline'` and `'unsafe-eval'`

---

**Status:** ✅ Configuration ready for deployment
**Impact:** High security improvement, no functionality impact (if configured correctly)
**Effort:** 10-15 minutes deployment + testing
