#!/bin/bash
set -e

echo "=========================================="
echo "Z-Image-Turbo EC2 Deployment Script"
echo "=========================================="

# Configuration
APP_DIR="/home/ubuntu/zimage-api"
VENV_DIR="$APP_DIR/venv"
SERVICE_NAME="zimage-api"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}[1/8]${NC} Checking CUDA..."
if ! nvidia-smi &> /dev/null; then
    echo -e "${RED}❌ NVIDIA driver not found!${NC}"
    exit 1
fi
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
echo ""

echo -e "${GREEN}[2/8]${NC} Creating application directory..."
mkdir -p "$APP_DIR"
cd "$APP_DIR"
echo "   Directory: $APP_DIR"
echo ""

echo -e "${GREEN}[3/8]${NC} Setting up Python virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "   Created new venv"
else
    echo "   Using existing venv"
fi
source "$VENV_DIR/bin/activate"
echo ""

echo -e "${GREEN}[4/8]${NC} Upgrading pip..."
pip install --upgrade pip
echo ""

echo -e "${GREEN}[5/8]${NC} Installing dependencies..."
echo "   This may take 5-10 minutes..."

# Install PyTorch with CUDA support first
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# Install diffusers from source for latest Z-Image support
echo "   Installing diffusers from source..."
pip install git+https://github.com/huggingface/diffusers

# Install other dependencies
pip install transformers accelerate flask pillow safetensors sentencepiece
echo ""

echo -e "${GREEN}[6/8]${NC} Copying API server file..."
# Note: This assumes api_server.py is uploaded to the instance
if [ -f "/tmp/api_server.py" ]; then
    cp /tmp/api_server.py "$APP_DIR/api_server.py"
    chmod +x "$APP_DIR/api_server.py"
    echo "   Copied from /tmp/api_server.py"
else
    echo -e "${YELLOW}⚠️  api_server.py not found in /tmp${NC}"
    echo "   Please upload api_server.py to the instance"
fi
echo ""

echo -e "${GREEN}[7/8]${NC} Setting up systemd service..."
sudo tee /etc/systemd/system/$SERVICE_NAME.service > /dev/null <<EOF
[Unit]
Description=Z-Image-Turbo API Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_DIR/bin"
ExecStart=$VENV_DIR/bin/python $APP_DIR/api_server.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
echo "   Service created and enabled"
echo ""

echo -e "${GREEN}[8/8]${NC} Starting service..."
sudo systemctl restart $SERVICE_NAME
echo "   Waiting for service to start..."
sleep 5

# Check service status
if sudo systemctl is-active --quiet $SERVICE_NAME; then
    echo -e "${GREEN}✅ Service is running!${NC}"
else
    echo -e "${RED}❌ Service failed to start${NC}"
    echo ""
    echo "Checking logs:"
    sudo journalctl -u $SERVICE_NAME -n 20 --no-pager
    exit 1
fi
echo ""

echo -e "${GREEN}Testing API...${NC}"
sleep 10  # Give model time to load

# Get local IP
LOCAL_IP=$(hostname -I | awk '{print $1}')

# Test health endpoint
if curl -s http://localhost:5000/health | grep -q "healthy"; then
    echo -e "${GREEN}✅ API is responding!${NC}"
    echo ""
    echo "=========================================="
    echo -e "${GREEN}Deployment Complete!${NC}"
    echo "=========================================="
    echo ""
    echo "API Endpoints:"
    echo "  Health: http://$LOCAL_IP:5000/health"
    echo "  Generate: http://$LOCAL_IP:5000/generate"
    echo "  Stats: http://$LOCAL_IP:5000/stats"
    echo ""
    echo "Service Management:"
    echo "  Status:  sudo systemctl status $SERVICE_NAME"
    echo "  Logs:    sudo journalctl -u $SERVICE_NAME -f"
    echo "  Restart: sudo systemctl restart $SERVICE_NAME"
    echo "  Stop:    sudo systemctl stop $SERVICE_NAME"
    echo ""
    echo "Test generation:"
    echo '  curl -X POST http://localhost:5000/generate \'
    echo '    -H "Content-Type: application/json" \'
    echo '    -d '"'"'{"prompt": "A sunset over mountains", "width": 1024, "height": 1024}'"'"' \'
    echo '    --output test.png'
    echo ""
else
    echo -e "${YELLOW}⚠️  API not responding yet${NC}"
    echo "   Model may still be loading..."
    echo "   Check logs: sudo journalctl -u $SERVICE_NAME -f"
fi
