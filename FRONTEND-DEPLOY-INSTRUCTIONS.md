# Frontend Deployment Instructions

**File to deploy:** `js/auth.js`
**Date:** 2025-12-01
**Changes:** Security fixes (Secure cookie flags, JWT parsing warnings)

---

## Option 1: SCP (Recommended)

```bash
# Upload to your web server
scp js/auth.js ubuntu@YOUR_SERVER:/home/ubuntu/web-admin/html/js/

# OR if using different path:
scp js/auth.js user@server:/path/to/html/js/
```

---

## Option 2: Manual Upload via SFTP/FTP

1. Connect to server via SFTP client (FileZilla, WinSCP, etc.)
2. Navigate to: `/home/ubuntu/web-admin/html/js/`
3. Upload `js/auth.js`
4. Verify permissions: `chmod 644 auth.js`

---

## Option 3: Direct Edit on Server

```bash
# SSH to server
ssh ubuntu@YOUR_SERVER

# Backup current file
cp /home/ubuntu/web-admin/html/js/auth.js /home/ubuntu/web-admin/html/js/auth.js.backup

# Edit file
nano /home/ubuntu/web-admin/html/js/auth.js

# Or upload via cat
cat > /home/ubuntu/web-admin/html/js/auth.js << 'EOF'
[paste content of js/auth.js here]
EOF
```

---

## Changes in auth.js

### 1. Secure Cookie Flags (setCookie method)
```javascript
// BEFORE:
document.cookie = name + "=" + value + ";path=/;SameSite=Lax";

// AFTER:
document.cookie = name + "=" + value +
    ";path=/;SameSite=Strict;Secure";  // Added Strict + Secure
```

### 2. JWT Parsing Warnings (parseJwt method)
```javascript
/**
 * ⚠️ SECURITY WARNING: This function does NOT verify the JWT signature!
 * Backend MUST validate JWT signature before trusting any claims.
 */
parseJwt(token) {
    // Added validation checks
    if (!token || typeof token !== 'string') {
        throw new Error('Invalid token format');
    }

    const parts = token.split('.');
    if (parts.length !== 3) {
        throw new Error('Invalid JWT structure');
    }
    // ...
}
```

### 3. getUserId Warning
```javascript
/**
 * ⚠️ SECURITY WARNING: This user_id is extracted from an UNVERIFIED JWT!
 * Backend Lambda functions MUST validate the JWT signature.
 */
getUserId() {
    return this.user?.user_id || null;
}
```

---

## Verification After Deployment

### 1. Check Cookie Security

```javascript
// Open browser DevTools → Application → Cookies
// Verify:
//  - Secure: true (if HTTPS)
//  - SameSite: Strict
//  - Path: /
```

### 2. Check Console for Warnings

```javascript
// Open browser console (F12)
// Look for JWT security warnings when parsing tokens
```

### 3. Test Login Flow

```
1. Go to login page
2. Login with Google
3. Check cookies are set correctly
4. Verify no errors in console
```

---

## Rollback (if needed)

```bash
# Restore from backup
cp /home/ubuntu/web-admin/html/js/auth.js.backup \
   /home/ubuntu/web-admin/html/js/auth.js

# Or restore from local backup
cd E:/youtube-content-automation/backups/production-backup-20251201-162341/frontend
scp js/auth.js ubuntu@SERVER:/home/ubuntu/web-admin/html/js/
```

---

## Next Steps After Deployment

1. Clear browser cache
2. Test login functionality
3. Monitor browser console for errors
4. Check CloudWatch logs for Lambda errors
5. Proceed with Week 2 fixes
