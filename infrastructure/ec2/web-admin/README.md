# Web Admin Infrastructure

Production web admin panel infrastructure for EC2.

## 🏗️ Architecture

```
web-admin/
├── docker-compose.yml          # Services orchestration
├── nginx/
│   ├── nginx.conf              # Main Nginx config
│   └── conf.d/
│       └── admin.conf          # Admin panel site config
├── certbot/
│   ├── conf/                   # SSL certificates (Let's Encrypt)
│   └── www/                    # ACME challenge files
└── html/
    ├── admin.html              # Admin dashboard
    ├── channel-configs.html    # Channel configuration UI
    └── api/                    # PHP API endpoints
```

## 🐳 Services

### Nginx
- **Ports:** 80 (HTTP), 443 (HTTPS)
- **Role:** Web server, SSL termination, reverse proxy to PHP-FPM
- **Image:** `nginx:latest`

### PHP-FPM
- **Port:** 9000 (internal)
- **Role:** PHP processing for admin panel
- **Image:** `php:8.1-fpm`

### Certbot
- **Role:** Automatic SSL certificate renewal (Let's Encrypt)
- **Image:** `certbot/certbot`
- **Schedule:** Checks for renewal every 12 hours

## 📦 Deployment

### Prerequisites

- Docker and Docker Compose installed
- Domain name configured (for SSL)
- Ports 80 and 443 open

### Setup

1. **Copy infrastructure to server:**
   ```bash
   scp -r infrastructure/ec2/web-admin ubuntu@YOUR_SERVER:~/
   ```

2. **Configure SSL domain:**
   ```bash
   # Edit nginx/conf.d/admin.conf
   # Replace YOUR_DOMAIN with your actual domain
   ```

3. **Add HTML files:**
   ```bash
   mkdir -p ~/web-admin/html
   # Add your admin.html, channel-configs.html, etc.
   ```

4. **Start services:**
   ```bash
   cd ~/web-admin
   docker-compose up -d
   ```

5. **Verify:**
   ```bash
   docker-compose ps
   curl http://localhost
   curl https://localhost -k
   ```

## 🔐 SSL Certificates

### Initial Setup

If certificates don't exist yet:

```bash
# Stop nginx temporarily
docker-compose stop nginx

# Obtain certificate
docker-compose run --rm certbot certonly --webroot \
  -w /var/www/certbot \
  -d YOUR_DOMAIN \
  --email YOUR_EMAIL \
  --agree-tos \
  --non-interactive

# Start nginx
docker-compose up -d nginx
```

### Automatic Renewal

Certbot container automatically renews certificates every 12 hours.

## 🔧 Management

### View logs
```bash
docker-compose logs -f nginx
docker-compose logs -f php-fpm
```

### Restart services
```bash
docker-compose restart nginx
docker-compose restart php-fpm
```

### Update configuration
```bash
# Edit config files
vim nginx/conf.d/admin.conf

# Reload nginx
docker-compose exec nginx nginx -s reload
```

### Stop all services
```bash
docker-compose down
```

## 🛡️ Security

- ✅ HTTPS enforced (HTTP redirects to HTTPS)
- ✅ Modern TLS protocols (TLS 1.2+)
- ✅ Security headers configured
- ✅ Hidden files blocked
- ✅ PHP execution restricted to .php files

## 📊 Monitoring

### Check service status
```bash
docker-compose ps
```

### Test endpoints
```bash
curl -I http://YOUR_DOMAIN
curl -I https://YOUR_DOMAIN
```

### SSL certificate info
```bash
docker-compose exec certbot certbot certificates
```

## 🆘 Troubleshooting

### Nginx won't start
```bash
# Check config syntax
docker-compose exec nginx nginx -t

# View error logs
docker-compose logs nginx
```

### SSL issues
```bash
# Check certificate files
ls -la certbot/conf/live/YOUR_DOMAIN/

# Manual renewal
docker-compose run --rm certbot renew --force-renewal
```

### PHP not working
```bash
# Check PHP-FPM logs
docker-compose logs php-fpm

# Verify PHP-FPM is running
docker-compose exec php-fpm php-fpm -v
```

## 📝 Notes

- Replace `YOUR_DOMAIN` with your actual domain in `nginx/conf.d/admin.conf`
- Ensure DNS is configured before obtaining SSL certificates
- Keep Docker images updated: `docker-compose pull && docker-compose up -d`
