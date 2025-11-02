#!/bin/bash

# Web Admin Setup Script for EC2
# This script sets up a fresh web admin infrastructure

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   🚀 WEB ADMIN SETUP${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo ""

# Configuration
WEB_ADMIN_DIR="$HOME/web-admin"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}⚠️  Docker not found. Installing...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    echo -e "${GREEN}✅ Docker installed${NC}"
fi

# Check if Docker Compose is installed
if ! docker compose version &> /dev/null; then
    echo -e "${YELLOW}⚠️  Docker Compose not found. Installing...${NC}"
    sudo apt update
    sudo apt install docker-compose-plugin -y
    echo -e "${GREEN}✅ Docker Compose installed${NC}"
fi

echo ""
echo -e "${GREEN}[1/6]${NC} Creating directory structure..."
mkdir -p "$WEB_ADMIN_DIR"/{nginx/conf.d,certbot/{conf,www},html}
echo -e "${GREEN}✅ Directories created${NC}"

echo ""
echo -e "${GREEN}[2/6]${NC} Copying configuration files..."
# Check if infrastructure files exist
if [ -d "infrastructure/ec2/web-admin" ]; then
    cp -r infrastructure/ec2/web-admin/* "$WEB_ADMIN_DIR/"
    echo -e "${GREEN}✅ Configuration files copied${NC}"
else
    echo -e "${YELLOW}⚠️  Infrastructure files not found in current directory${NC}"
    echo -e "${YELLOW}   Please copy files manually or run from project root${NC}"
fi

echo ""
echo -e "${GREEN}[3/6]${NC} Setting permissions..."
chmod -R 755 "$WEB_ADMIN_DIR"
echo -e "${GREEN}✅ Permissions set${NC}"

echo ""
echo -e "${GREEN}[4/6]${NC} Checking for HTML files..."
if [ -d "$WEB_ADMIN_DIR/html" ] && [ "$(ls -A $WEB_ADMIN_DIR/html)" ]; then
    echo -e "${GREEN}✅ HTML files found${NC}"
else
    echo -e "${YELLOW}⚠️  No HTML files found${NC}"
    echo -e "${YELLOW}   Add your admin panel files to: $WEB_ADMIN_DIR/html/${NC}"
fi

echo ""
echo -e "${GREEN}[5/6]${NC} Starting Docker services..."
cd "$WEB_ADMIN_DIR"

if [ -f "docker-compose.yml" ]; then
    docker compose up -d
    echo -e "${GREEN}✅ Services started${NC}"
else
    echo -e "${YELLOW}⚠️  docker-compose.yml not found${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}[6/6]${NC} Verifying setup..."
sleep 3

echo ""
echo "📦 Running containers:"
docker compose ps

echo ""
echo "🌐 Testing endpoints:"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost 2>/dev/null || echo "000")
echo "  HTTP: $HTTP_CODE"

HTTPS_CODE=$(curl -k -s -o /dev/null -w "%{http_code}" https://localhost 2>/dev/null || echo "000")
echo "  HTTPS: $HTTPS_CODE"

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ WEB ADMIN SETUP COMPLETE!${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${YELLOW}📋 Next Steps:${NC}"
echo ""
echo "1. Add HTML files to: $WEB_ADMIN_DIR/html/"
echo ""
echo "2. Configure SSL (if using domain):"
echo "   ${BLUE}cd $WEB_ADMIN_DIR${NC}"
echo "   ${BLUE}docker compose run --rm certbot certonly --webroot \\${NC}"
echo "   ${BLUE}     -w /var/www/certbot -d YOUR_DOMAIN \\${NC}"
echo "   ${BLUE}     --email YOUR_EMAIL --agree-tos${NC}"
echo ""
echo "3. Update domain in nginx config:"
echo "   ${BLUE}nano $WEB_ADMIN_DIR/nginx/conf.d/admin.conf${NC}"
echo "   Replace 'YOUR_DOMAIN' with actual domain"
echo ""
echo "4. Reload nginx:"
echo "   ${BLUE}docker compose exec nginx nginx -s reload${NC}"
echo ""
echo "5. View logs:"
echo "   ${BLUE}docker compose logs -f${NC}"
echo ""
