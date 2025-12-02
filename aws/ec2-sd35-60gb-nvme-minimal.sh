#!/bin/bash
# Minimal UserData - downloads full setup script
set -e
exec > >(tee /var/log/userdata.log) 2>&1

echo "Downloading full setup script..."
curl -fsSL https://raw.githubusercontent.com/user/repo/main/setup.sh -o /tmp/setup.sh 2>/dev/null || {
    # Fallback: inline minimal setup
    cat > /tmp/setup.sh << 'SETUP_EOF'
#!/bin/bash
set -e
exec > >(tee /var/log/sd35-setup.log) 2>&1

echo "=== SD 3.5 MEDIUM - 60GB EBS + NVMe SETUP ==="
date

# Check if already installed
if [ -f /home/ubuntu/sd35-api/.installed ]; then
    echo "Already installed, re-mounting NVMe..."
    NVME=$(lsblk -d -n -o NAME,TYPE | grep nvme | grep -v nvme0 | head -1 | awk '{print $1}')
    [ -z "$NVME" ] && { echo "ERROR: NVMe not found!"; exit 1; }
    [ ! -d /mnt/nvme/pip-cache ] && {
        mkfs.ext4 -F /dev/$NVME
        mkdir -p /mnt/nvme
        mount /dev/$NVME /mnt/nvme
        mkdir -p /mnt/nvme/{pip-cache,torch-cache,tmp}
        chown -R ubuntu:ubuntu /mnt/nvme
    }
    exit 0
fi

# Mount NVMe (MANDATORY)
NVME=$(lsblk -d -n -o NAME,TYPE | grep nvme | grep -v nvme0 | head -1 | awk '{print $1}')
if [ -z "$NVME" ]; then
    echo "ERROR: NVMe instance store NOT FOUND!"
    echo "60GB EBS requires NVMe for caches"
    exit 1
fi

mkfs.ext4 -F /dev/$NVME
mkdir -p /mnt/nvme
mount /dev/$NVME /mnt/nvme
mkdir -p /mnt/nvme/{pip-cache,torch-cache,tmp}
chown -R ubuntu:ubuntu /mnt/nvme

# System packages
apt-get update
apt-get install -y python3-pip python3-venv git curl nvme-cli
apt-get clean
rm -rf /var/lib/apt/lists/*

# Create app
mkdir -p /home/ubuntu/sd35-api
cd /home/ubuntu/sd35-api
python3 -m venv venv
source venv/bin/activate

# Configure caches
export PIP_CACHE_DIR=/mnt/nvme/pip-cache
export TORCH_HOME=/mnt/nvme/torch-cache
export TMPDIR=/mnt/nvme/tmp
export HF_HOME=/home/ubuntu/.cache/huggingface
export HF_TOKEN=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

pip config set global.cache-dir /mnt/nvme/pip-cache

# Install packages
pip install --upgrade pip
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install diffusers transformers accelerate flask pillow requests sentencepiece protobuf

# Create server
cat > server.py << 'PYEOF'
from flask import Flask, request, send_file
import torch, io, os, time, shutil
app = Flask(__name__)
pipe = None

def load_model():
    global pipe
    if pipe: return True
    try:
        from diffusers import StableDiffusion3Pipeline
        hf_token = os.environ.get('HF_TOKEN', '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')
        pipe = StableDiffusion3Pipeline.from_pretrained(
            "stabilityai/stable-diffusion-3.5-medium",
            torch_dtype=torch.bfloat16, token=hf_token
        )
        if torch.cuda.is_available():
            pipe = pipe.to("cuda")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

@app.route('/health')
def health():
    ebs_total, ebs_used, ebs_free = shutil.disk_usage('/')
    nvme = None
    if os.path.exists('/mnt/nvme'):
        n_tot, n_use, n_free = shutil.disk_usage('/mnt/nvme')
        nvme = {'total_gb': round(n_tot/1024**3,2), 'used_gb': round(n_use/1024**3,2), 'free_gb': round(n_free/1024**3,2)}
    return {
        'status': 'healthy',
        'model_loaded': pipe is not None,
        'cuda': torch.cuda.is_available(),
        'gpu': torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        'ebs': {'total_gb': round(ebs_total/1024**3,2), 'used_gb': round(ebs_used/1024**3,2), 'free_gb': round(ebs_free/1024**3,2)},
        'nvme': nvme
    }

@app.route('/generate', methods=['POST'])
def generate():
    if not pipe:
        return {'error': 'Model not loaded'}, 503
    data = request.json
    prompt = data.get('prompt', '')
    img = pipe(prompt, height=data.get('height',1024), width=data.get('width',1024),
               num_inference_steps=data.get('steps',28), guidance_scale=data.get('guidance_scale',3.5)).images[0]
    bio = io.BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    return send_file(bio, mimetype='image/png')

if __name__ == '__main__':
    load_model()
    app.run(host='0.0.0.0', port=5000)
PYEOF

# Environment
cat >> venv/bin/activate << 'EOF'
export HF_TOKEN=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
export HF_HOME=/home/ubuntu/.cache/huggingface
[ -d /mnt/nvme ] && {
    export PIP_CACHE_DIR=/mnt/nvme/pip-cache
    export TORCH_HOME=/mnt/nvme/torch-cache
    export TMPDIR=/mnt/nvme/tmp
}
EOF

# Systemd service
cat > /etc/systemd/system/sd35-api.service << 'EOF'
[Unit]
Description=SD 3.5 Medium API
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/sd35-api
Environment="PATH=/home/ubuntu/sd35-api/venv/bin"
Environment="HF_TOKEN=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"
Environment="HF_HOME=/home/ubuntu/.cache/huggingface"
Environment="PIP_CACHE_DIR=/mnt/nvme/pip-cache"
Environment="TORCH_HOME=/mnt/nvme/torch-cache"
Environment="TMPDIR=/mnt/nvme/tmp"
ExecStart=/home/ubuntu/sd35-api/venv/bin/python server.py
Restart=always
StandardOutput=append:/var/log/sd35-api.log
StandardError=append:/var/log/sd35-api-error.log

[Install]
WantedBy=multi-user.target
EOF

chown -R ubuntu:ubuntu /home/ubuntu/sd35-api
chown -R ubuntu:ubuntu /home/ubuntu/.cache
chown -R ubuntu:ubuntu /mnt/nvme

systemctl daemon-reload
systemctl enable sd35-api
systemctl start sd35-api

touch /home/ubuntu/sd35-api/.installed
chown ubuntu:ubuntu /home/ubuntu/sd35-api/.installed

echo "=== SETUP COMPLETE ==="
date
SETUP_EOF
}

chmod +x /tmp/setup.sh
bash /tmp/setup.sh
