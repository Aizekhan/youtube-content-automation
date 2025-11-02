# EC2 Web Admin Setup Guide

Complete guide for setting up the web admin panel on EC2.

## 📋 Overview

This infrastructure provides:
- **Nginx** web server with SSL
- **PHP-FPM** for PHP processing
- **Certbot** for automatic SSL renewal
- **Admin panel** for content management

## 🎯 Prerequisites

- EC2 instance running Ubuntu
- Docker and Docker Compose installed
- Domain name (optional, for SSL)
- Security group with ports 80, 443 open

## 🚀 Quick Start

### 1. Install Docker (if not installed)

```bash
# Update packages
sudo apt update

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Verify
docker --version
docker compose version
```

### 2. Create Directory Structure

```bash
cd ~
mkdir -p web-admin/{nginx/conf.d,certbot/{conf,www},html}
```

### 3. Copy Configuration Files

**From local machine:**
```bash
scp -r infrastructure/ec2/web-admin/* ubuntu@YOUR_EC2_IP:~/web-admin/
```

**Or manually create files on EC2.**

### 4. Add Your HTML Files

```bash
# Upload admin panel files
scp admin.html ubuntu@YOUR_EC2_IP:~/web-admin/html/
scp channel-configs.html ubuntu@YOUR_EC2_IP:~/web-admin/html/
# ... other files
```

### 5. Configure Domain (Optional)

Edit `~/web-admin/nginx/conf.d/admin.conf`:
```bash
nano ~/web-admin/nginx/conf.d/admin.conf
```

Replace `YOUR_DOMAIN` with your actual domain.

### 6. Start Services

```bash
cd ~/web-admin
docker compose up -d
```

### 7. Verify

```bash
# Check containers
docker compose ps

# Test HTTP
curl http://localhost

# Test HTTPS (if SSL configured)
curl https://localhost -k
```

## 🔐 SSL Certificate Setup

### Option 1: With Domain

```bash
cd ~/web-admin

# Stop nginx temporarily
docker compose stop nginx

# Obtain certificate
docker compose run --rm certbot certonly --webroot \
  -w /var/www/certbot \
  -d your-domain.com \
  --email your-email@example.com \
  --agree-tos \
  --non-interactive

# Start nginx
docker compose up -d nginx
```

### Option 2: Without Domain (Self-Signed)

```bash
# Generate self-signed certificate
sudo mkdir -p ~/web-admin/certbot/conf/live/localhost
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ~/web-admin/certbot/conf/live/localhost/privkey.pem \
  -out ~/web-admin/certbot/conf/live/localhost/fullchain.pem \
  -subj "/CN=localhost"

# Update nginx config to use localhost
sed -i 's/YOUR_DOMAIN/localhost/g' ~/web-admin/nginx/conf.d/admin.conf
```

## 🔧 Management Commands

### View Logs
```bash
docker compose logs -f nginx
docker compose logs -f php-fpm
docker compose logs certbot
```

### Restart Services
```bash
docker compose restart nginx
docker compose restart php-fpm
```

### Update Configuration
```bash
# Edit config
nano ~/web-admin/nginx/conf.d/admin.conf

# Test config
docker compose exec nginx nginx -t

# Reload nginx
docker compose exec nginx nginx -s reload
```

### Stop Services
```bash
docker compose down
```

### Update Containers
```bash
docker compose pull
docker compose up -d
```

## 📊 Directory Structure

```
~/web-admin/
├── docker-compose.yml
├── nginx/
│   ├── nginx.conf
│   └── conf.d/
│       └── admin.conf
├── certbot/
│   ├── conf/
│   │   └── live/
│   │       └── your-domain/
│   │           ├── fullchain.pem
│   │           └── privkey.pem
│   └── www/
└── html/
    ├── admin.html
    ├── channel-configs.html
    └── api/
```

## 🛡️ Security Best Practices

1. **Firewall Configuration:**
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

2. **Keep Docker Updated:**
   ```bash
   sudo apt update && sudo apt upgrade docker-ce docker-compose-plugin
   ```

3. **Regular Backups:**
   ```bash
   # Backup configuration
   tar -czf web-admin-backup-$(date +%Y%m%d).tar.gz ~/web-admin
   ```

4. **Monitor Logs:**
   ```bash
   docker compose logs --tail=100 -f
   ```

## 🆘 Troubleshooting

### Nginx Won't Start

```bash
# Check syntax
docker compose exec nginx nginx -t

# Check logs
docker compose logs nginx

# Check port conflicts
sudo netstat -tulpn | grep :80
sudo netstat -tulpn | grep :443
```

### SSL Certificate Issues

```bash
# Check certificate files
ls -la ~/web-admin/certbot/conf/live/

# Manual renewal
docker compose run --rm certbot renew --force-renewal

# Check expiration
docker compose exec certbot certbot certificates
```

### PHP Not Working

```bash
# Check PHP-FPM status
docker compose exec php-fpm php -v

# Check logs
docker compose logs php-fpm

# Restart PHP-FPM
docker compose restart php-fpm
```

### Permission Issues

```bash
# Fix ownership
sudo chown -R ubuntu:ubuntu ~/web-admin

# Fix permissions
chmod -R 755 ~/web-admin/html
```

## 📈 Performance Optimization

### Nginx Cache

Add to `nginx/conf.d/admin.conf`:
```nginx
location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### PHP-FPM Tuning

Create `~/web-admin/php-fpm/www.conf`:
```ini
pm = dynamic
pm.max_children = 50
pm.start_servers = 5
pm.min_spare_servers = 5
pm.max_spare_servers = 35
```

## 🔄 Updates and Maintenance

### Weekly Tasks
- Check logs for errors
- Monitor disk space
- Review SSL certificate expiration

### Monthly Tasks
- Update Docker images
- Backup configuration
- Review security headers

### Quarterly Tasks
- Security audit
- Performance review
- Dependency updates

## 📞 Support

For issues or questions:
1. Check logs: `docker compose logs`
2. Verify configuration: `nginx -t`
3. Review this documentation
4. Check Docker status: `docker compose ps`

## 📚 Additional Resources

- [Nginx Documentation](https://nginx.org/en/docs/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [PHP-FPM Documentation](https://www.php.net/manual/en/install.fpm.php)
