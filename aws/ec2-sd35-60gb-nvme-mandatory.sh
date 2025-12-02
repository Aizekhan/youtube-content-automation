#!/bin/bash
# SD 3.5 Medium - 60GB EBS + NVMe MANDATORY
# EBS (60GB):  Model cache, venv, OS (persistent)
# NVMe (250GB): Pip, Torch, Temp caches (ephemeral, auto-cleanup on STOP)
#
# CRITICAL: NVMe is MANDATORY! Script fails if NVMe not found.

set -e  # Exit on error

# Logging
exec > >(tee /var/log/sd35-setup.log)
exec 2>&1

echo "=========================================="
echo "SD 3.5 MEDIUM - 60GB EBS + NVMe SETUP"
echo "=========================================="
date

# ============================================
# STEP 1: CHECK IF ALREADY INSTALLED
# ============================================
if [ -f /home/ubuntu/sd35-api/.installed ]; then
    echo "✅ SD 3.5 already installed (not first boot)"
    echo ""
    echo "🔍 Checking NVMe mount status..."

    # NVMe is ephemeral - need to re-mount after STOP/START
    NVME_DEVICE=$(lsblk -d -n -o NAME,TYPE | grep nvme | grep -v nvme0 | head -1 | awk '{print $1}')

    if [ -z "$NVME_DEVICE" ]; then
        echo "❌ CRITICAL ERROR: NVMe instance store NOT FOUND!"
        echo "   g5.xlarge should have 250GB NVMe"
        echo "   Check instance type or AWS availability zone"
        exit 1
    fi

    if [ ! -d /mnt/nvme/pip-cache ]; then
        echo "🔧 Re-mounting NVMe after restart..."

        # Format and mount NVMe
        mkfs.ext4 -F /dev/$NVME_DEVICE
        mkdir -p /mnt/nvme
        mount /dev/$NVME_DEVICE /mnt/nvme

        # Create cache directories
        mkdir -p /mnt/nvme/pip-cache
        mkdir -p /mnt/nvme/torch-cache
        mkdir -p /mnt/nvme/tmp

        # Set permissions
        chown -R ubuntu:ubuntu /mnt/nvme

        echo "✅ NVMe re-mounted successfully"
        df -h /mnt/nvme
    else
        echo "✅ NVMe already mounted"
    fi

    echo "🚀 Systemd will auto-start sd35-api service"
    exit 0
fi

echo "🆕 FIRST RUN - Full installation starting..."
echo ""

# ============================================
# STEP 2: MOUNT NVMe INSTANCE STORE (MANDATORY!)
# ============================================
echo "=========================================="
echo "STEP 1/8: NVMe Instance Store (MANDATORY)"
echo "=========================================="

# Find NVMe device (should be nvme1n1, NOT nvme0n1 which is EBS root)
NVME_DEVICE=$(lsblk -d -n -o NAME,TYPE | grep nvme | grep -v nvme0 | head -1 | awk '{print $1}')

if [ -z "$NVME_DEVICE" ]; then
    echo "❌ CRITICAL ERROR: NVMe instance store NOT FOUND!"
    echo ""
    echo "This setup requires NVMe for pip/torch/temp caches"
    echo "to prevent filling up the 60GB EBS volume."
    echo ""
    echo "Possible causes:"
    echo "  1. Instance type is not g5.xlarge"
    echo "  2. AMI doesn't support instance store mapping"
    echo "  3. Availability zone doesn't have NVMe-enabled hardware"
    echo ""
    echo "Solutions:"
    echo "  1. Use block-device-mappings: {DeviceName:/dev/sdb,VirtualName:ephemeral0}"
    echo "  2. Try different availability zone"
    echo "  3. Use 100GB EBS instead (more expensive)"
    echo ""
    echo "SETUP ABORTED - refusing to continue without NVMe"
    exit 1
fi

echo "✅ Found NVMe instance store: /dev/$NVME_DEVICE"

# Format NVMe as ext4
echo "Formatting /dev/$NVME_DEVICE as ext4..."
mkfs.ext4 -F /dev/$NVME_DEVICE

# Create mount point and mount
mkdir -p /mnt/nvme
mount /dev/$NVME_DEVICE /mnt/nvme

# Verify mount
if ! mountpoint -q /mnt/nvme; then
    echo "❌ ERROR: Failed to mount NVMe"
    exit 1
fi

# Create cache directories
mkdir -p /mnt/nvme/pip-cache
mkdir -p /mnt/nvme/torch-cache
mkdir -p /mnt/nvme/tmp

# Set permissions
chown -R ubuntu:ubuntu /mnt/nvme

echo "✅ NVMe mounted successfully at /mnt/nvme"
df -h /mnt/nvme
echo ""

# ============================================
# STEP 3: SYSTEM UPDATE & PACKAGES
# ============================================
echo "=========================================="
echo "STEP 2/8: System Packages"
echo "=========================================="

apt-get update

# Install essential packages
apt-get install -y \
    python3-pip \
    python3-venv \
    git \
    curl \
    nvme-cli

echo "✅ System packages installed"

# CRITICAL: Clean apt cache to save EBS space!
echo "Cleaning apt cache to save EBS space..."
apt-get clean
rm -rf /var/lib/apt/lists/*

# Check EBS usage
echo ""
echo "Current EBS usage:"
df -h / | grep -v Filesystem
echo ""

# ============================================
# STEP 4: VERIFY NVIDIA GPU
# ============================================
echo "=========================================="
echo "STEP 3/8: GPU Verification"
echo "=========================================="

if command -v nvidia-smi &> /dev/null; then
    nvidia-smi
    echo "✅ NVIDIA GPU detected"
else
    echo "⚠️ NVIDIA drivers not found (might be first boot)"
    echo "   Drivers should be pre-installed in AWS Deep Learning AMI"
fi

echo ""

# ============================================
# STEP 5: CREATE APP DIRECTORY & VENV
# ============================================
echo "=========================================="
echo "STEP 4/8: Python Environment"
echo "=========================================="

mkdir -p /home/ubuntu/sd35-api
cd /home/ubuntu/sd35-api

# Create Python virtual environment on EBS
echo "Creating Python venv on EBS..."
python3 -m venv venv || python3.11 -m venv venv

source venv/bin/activate

pip install --upgrade pip

echo "✅ Python venv created"
echo ""

# ============================================
# STEP 6: CONFIGURE CACHE LOCATIONS
# ============================================
echo "=========================================="
echo "STEP 5/8: Cache Configuration"
echo "=========================================="

# Configure pip cache on NVMe (ephemeral)
export PIP_CACHE_DIR="/mnt/nvme/pip-cache"
pip config set global.cache-dir /mnt/nvme/pip-cache

# Configure PyTorch cache on NVMe (ephemeral)
export TORCH_HOME="/mnt/nvme/torch-cache"

# Configure temp directory on NVMe (ephemeral)
export TMPDIR="/mnt/nvme/tmp"
export TEMP="/mnt/nvme/tmp"
export TMP="/mnt/nvme/tmp"

# HuggingFace cache on EBS (PERSISTENT - NEVER AUTO-DELETE!)
export HF_HOME="/home/ubuntu/.cache/huggingface"
export TRANSFORMERS_CACHE="/home/ubuntu/.cache/huggingface"

# HuggingFace token
export HF_TOKEN="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"
export HUGGING_FACE_HUB_TOKEN="$HF_TOKEN"

echo "✅ Cache locations configured:"
echo ""
echo "   📦 PERSISTENT (EBS):"
echo "      Model cache:     /home/ubuntu/.cache/huggingface/"
echo "      Python venv:     /home/ubuntu/sd35-api/venv/"
echo ""
echo "   💾 EPHEMERAL (NVMe - auto-deleted on STOP):"
echo "      Pip cache:       /mnt/nvme/pip-cache/"
echo "      Torch cache:     /mnt/nvme/torch-cache/"
echo "      Temp files:      /mnt/nvme/tmp/"
echo ""

# ============================================
# STEP 7: INSTALL PyTorch & DEPENDENCIES
# ============================================
echo "=========================================="
echo "STEP 6/8: Installing Dependencies"
echo "=========================================="

echo "Installing PyTorch with CUDA support..."
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121 || \
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

echo ""
echo "Installing Stable Diffusion dependencies..."
pip install diffusers transformers accelerate flask pillow requests sentencepiece protobuf

echo ""
echo "✅ All dependencies installed"

# Show pip cache size (should be on NVMe)
echo ""
echo "Pip cache size on NVMe:"
du -sh /mnt/nvme/pip-cache/ || echo "Empty"
echo ""

# ============================================
# STEP 8: ADD ENVIRONMENT TO VENV
# ============================================
echo "Adding environment variables to venv activation..."

cat >> venv/bin/activate << 'ENVEOF'

# ========================================
# SD 3.5 Custom Environment
# ========================================

# HuggingFace (PERSISTENT on EBS)
export HF_TOKEN="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"
export HUGGING_FACE_HUB_TOKEN="$HF_TOKEN"
export HF_HOME="/home/ubuntu/.cache/huggingface"
export TRANSFORMERS_CACHE="/home/ubuntu/.cache/huggingface"

# NVMe caches (EPHEMERAL - re-mounted on each START)
if [ -d /mnt/nvme ]; then
    export PIP_CACHE_DIR="/mnt/nvme/pip-cache"
    export TORCH_HOME="/mnt/nvme/torch-cache"
    export TMPDIR="/mnt/nvme/tmp"
    export TEMP="/mnt/nvme/tmp"
    export TMP="/mnt/nvme/tmp"
fi
ENVEOF

echo "✅ Environment configured in venv"
echo ""

# ============================================
# STEP 9: CREATE FLASK API SERVER
# ============================================
echo "=========================================="
echo "STEP 7/8: Creating API Server"
echo "=========================================="

cat > /home/ubuntu/sd35-api/server.py << 'PYTHON_EOF'
from flask import Flask, request, jsonify, send_file
import torch
from PIL import Image
import io
import os
import time
import shutil

app = Flask(__name__)

# Model state
pipe = None
model_loading = False
model_error = None
model_load_start_time = None

def load_model():
    """Load SD 3.5 Medium from EBS cache (persistent storage)"""
    global pipe, model_loading, model_error, model_load_start_time

    if pipe is not None:
        return True

    if model_loading:
        return False

    try:
        model_loading = True
        model_load_start_time = time.time()

        print("=" * 60)
        print("LOADING STABLE DIFFUSION 3.5 MEDIUM")
        print("=" * 60)
        print(f"PyTorch: {torch.__version__}")
        print(f"CUDA: {torch.cuda.is_available()}")

        if torch.cuda.is_available():
            print(f"GPU: {torch.cuda.get_device_name(0)}")
            print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")

        from diffusers import StableDiffusion3Pipeline

        hf_token = os.environ.get('HF_TOKEN') or os.environ.get('HUGGING_FACE_HUB_TOKEN')

        if not hf_token:
            raise Exception("No HuggingFace token found!")

        print(f"Token: {hf_token[:10]}...")

        # Show cache locations
        hf_cache = os.environ.get('HF_HOME', os.path.expanduser('~/.cache/huggingface'))
        print(f"Model cache (EBS): {hf_cache}")

        if os.path.exists('/mnt/nvme'):
            print(f"Torch cache (NVMe): {os.environ.get('TORCH_HOME', 'default')}")
            print(f"Temp dir (NVMe): {os.environ.get('TMPDIR', '/tmp')}")

        print("Loading model from cache or downloading...")

        # Load with bfloat16 (optimal for A10G GPU)
        pipe = StableDiffusion3Pipeline.from_pretrained(
            "stabilityai/stable-diffusion-3.5-medium",
            torch_dtype=torch.bfloat16,
            token=hf_token
        )

        if torch.cuda.is_available():
            pipe = pipe.to("cuda")
            print("✅ Model loaded on GPU")
        else:
            print("⚠️ WARNING: Running on CPU")

        duration = time.time() - model_load_start_time
        print("=" * 60)
        print(f"MODEL LOADED in {duration:.1f}s")
        print("=" * 60)

        model_loading = False
        return True

    except Exception as e:
        model_error = str(e)
        model_loading = False
        duration = time.time() - model_load_start_time if model_load_start_time else 0
        print("=" * 60)
        print(f"❌ ERROR after {duration:.1f}s: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return False

@app.route('/health', methods=['GET'])
def health():
    """Health check with storage info"""

    # EBS disk usage
    ebs_total, ebs_used, ebs_free = shutil.disk_usage('/')

    # NVMe disk usage (if mounted)
    nvme_info = None
    if os.path.exists('/mnt/nvme'):
        nvme_total, nvme_used, nvme_free = shutil.disk_usage('/mnt/nvme')
        nvme_info = {
            'total_gb': round(nvme_total / (1024**3), 2),
            'used_gb': round(nvme_used / (1024**3), 2),
            'free_gb': round(nvme_free / (1024**3), 2),
            'usage_percent': round((nvme_used / nvme_total) * 100, 1)
        }

    return jsonify({
        'status': 'healthy',
        'model': 'stable-diffusion-3.5-medium',
        'model_loaded': pipe is not None,
        'model_loading': model_loading,
        'model_error': model_error,
        'cuda_available': torch.cuda.is_available(),
        'gpu_name': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        'storage': {
            'ebs_60gb': {
                'total_gb': round(ebs_total / (1024**3), 2),
                'used_gb': round(ebs_used / (1024**3), 2),
                'free_gb': round(ebs_free / (1024**3), 2),
                'usage_percent': round((ebs_used / ebs_total) * 100, 1)
            },
            'nvme_250gb': nvme_info
        },
        'cache_locations': {
            'model_persistent': os.environ.get('HF_HOME', '~/.cache/huggingface'),
            'pip_ephemeral': os.environ.get('PIP_CACHE_DIR', 'default'),
            'torch_ephemeral': os.environ.get('TORCH_HOME', 'default'),
            'tmp_ephemeral': os.environ.get('TMPDIR', '/tmp')
        }
    })

@app.route('/generate', methods=['POST'])
def generate():
    """Generate image from prompt"""
    if pipe is None:
        if model_loading:
            return jsonify({'error': 'Model loading...', 'model_loading': True}), 503
        else:
            return jsonify({'error': 'Model failed to load', 'details': model_error}), 500

    data = request.json
    prompt = data.get('prompt')
    if not prompt:
        return jsonify({'error': 'No prompt provided'}), 400

    width = data.get('width', 1024)
    height = data.get('height', 1024)
    steps = data.get('steps', 28)
    guidance = data.get('guidance_scale', 3.5)

    try:
        print(f"Generating: {prompt[:50]}...")
        start = time.time()

        image = pipe(
            prompt,
            height=height,
            width=width,
            num_inference_steps=steps,
            guidance_scale=guidance
        ).images[0]

        duration = time.time() - start
        print(f"✅ Generated in {duration:.1f}s")

        # Save to BytesIO
        img_io = io.BytesIO()
        image.save(img_io, 'PNG')
        img_io.seek(0)

        return send_file(img_io, mimetype='image/png')

    except Exception as e:
        print(f"❌ Generation error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("=" * 60)
    print("SD 3.5 MEDIUM API - 60GB EBS + NVMe")
    print("=" * 60)
    print("Storage:")
    print("  EBS 60GB:  Model cache (persistent)")
    print("  NVMe 250GB: Pip/Torch/Tmp caches (ephemeral)")
    print("=" * 60)

    # Load model on startup
    if load_model():
        print("Starting Flask on port 5000...")
        app.run(host='0.0.0.0', port=5000, debug=False)
    else:
        print("⚠️ Model load failed, starting Flask anyway")
        print("   Check /health endpoint for details")
        app.run(host='0.0.0.0', port=5000, debug=False)
PYTHON_EOF

chown ubuntu:ubuntu /home/ubuntu/sd35-api/server.py

echo "✅ API server created"
echo ""

# ============================================
# STEP 10: CREATE SYSTEMD SERVICE
# ============================================
echo "=========================================="
echo "STEP 8/8: Systemd Service"
echo "=========================================="

cat > /etc/systemd/system/sd35-api.service << 'SERVICE_EOF'
[Unit]
Description=Stable Diffusion 3.5 Medium API (60GB EBS + NVMe)
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/sd35-api
Environment="PATH=/home/ubuntu/sd35-api/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="HF_TOKEN=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"
Environment="HUGGING_FACE_HUB_TOKEN=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"
Environment="HF_HOME=/home/ubuntu/.cache/huggingface"
Environment="TRANSFORMERS_CACHE=/home/ubuntu/.cache/huggingface"
Environment="PIP_CACHE_DIR=/mnt/nvme/pip-cache"
Environment="TORCH_HOME=/mnt/nvme/torch-cache"
Environment="TMPDIR=/mnt/nvme/tmp"
Environment="TEMP=/mnt/nvme/tmp"
Environment="TMP=/mnt/nvme/tmp"

ExecStart=/home/ubuntu/sd35-api/venv/bin/python /home/ubuntu/sd35-api/server.py

Restart=always
RestartSec=10

StandardOutput=append:/var/log/sd35-api.log
StandardError=append:/var/log/sd35-api-error.log

[Install]
WantedBy=multi-user.target
SERVICE_EOF

echo "✅ Systemd service created"
echo ""

# ============================================
# STEP 11: SET PERMISSIONS
# ============================================
echo "Setting permissions..."

chown -R ubuntu:ubuntu /home/ubuntu/sd35-api
chown -R ubuntu:ubuntu /home/ubuntu/.cache
chown -R ubuntu:ubuntu /mnt/nvme

echo "✅ Permissions set"
echo ""

# ============================================
# STEP 12: ENABLE & START SERVICE
# ============================================
echo "Enabling and starting sd35-api service..."

systemctl daemon-reload
systemctl enable sd35-api
systemctl start sd35-api

echo "✅ Service started"
echo ""

# Mark as installed
touch /home/ubuntu/sd35-api/.installed
chown ubuntu:ubuntu /home/ubuntu/sd35-api/.installed

# ============================================
# FINAL SUMMARY
# ============================================
echo "=========================================="
echo "✅ SETUP COMPLETE!"
echo "=========================================="
date
echo ""
echo "📊 STORAGE ARCHITECTURE:"
echo ""
echo "   EBS 60GB (PERSISTENT - survives STOP/START):"
echo "   ├─ Model cache:      /home/ubuntu/.cache/huggingface/"
echo "   ├─ Python venv:      /home/ubuntu/sd35-api/venv/"
echo "   └─ Ubuntu + NVIDIA:  ~15GB"
echo ""
echo "   NVMe 250GB (EPHEMERAL - auto-deleted on STOP):"
echo "   ├─ Pip cache:        /mnt/nvme/pip-cache/"
echo "   ├─ Torch cache:      /mnt/nvme/torch-cache/"
echo "   └─ Temp files:       /mnt/nvme/tmp/"
echo ""
echo "💰 COST: $4.80/month (EBS) + $1.006/hour (EC2 runtime)"
echo ""
echo "📈 DISK USAGE:"
df -h / | grep -v Filesystem
echo ""
if [ -d /mnt/nvme ]; then
    df -h /mnt/nvme | grep -v Filesystem
fi
echo ""
echo "🔧 SERVICE:"
echo "   Name:   sd35-api"
echo "   Status: systemctl status sd35-api"
echo "   Logs:   tail -f /var/log/sd35-api.log"
echo "   Errors: tail -f /var/log/sd35-api-error.log"
echo ""
echo "🌐 HEALTH CHECK:"
echo "   curl http://localhost:5000/health"
echo ""
echo "=========================================="
