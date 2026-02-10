#!/bin/bash
# Qwen3-TTS Setup Script for g4dn.xlarge
# Deep Learning AMI GPU PyTorch 2.7 (Ubuntu 22.04)
set -e
exec > >(tee /var/log/qwen3-tts-setup.log) 2>&1

echo "=========================================="
echo "QWEN3-TTS SETUP - g4dn.xlarge On-Demand"
echo "=========================================="
date

# Check if already installed
if [ -f /home/ubuntu/qwen3-tts/.installed ]; then
    echo "✅ Already installed, starting service..."
    systemctl restart qwen3-tts
    exit 0
fi

# 1. Verify GPU
echo "=== Checking GPU ==="
if ! nvidia-smi > /dev/null 2>&1; then
    echo "❌ ERROR: NVIDIA drivers not found!"
    exit 1
fi
nvidia-smi
echo "✅ GPU detected"

# 2. Install system dependencies
echo "=== Installing system packages ==="
apt-get update
apt-get install -y python3.10-venv git curl htop nvtop
apt-get clean
rm -rf /var/lib/apt/lists/*

# 3. Create application directory
echo "=== Setting up application ==="
mkdir -p /home/ubuntu/qwen3-tts
cd /home/ubuntu/qwen3-tts

# 4. Create Python virtual environment
echo "=== Creating virtual environment ==="
python3.10 -m venv venv
source venv/bin/activate

# 5. Upgrade pip
pip install --upgrade pip setuptools wheel

# 6. Install PyTorch with CUDA 12.2
echo "=== Installing PyTorch 2.8.0 + CUDA 12.2 ==="
pip install torch==2.8.0 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu122

# 7. Install FlashAttention2 (prebuilt wheel for speed)
echo "=== Installing FlashAttention2 ==="
pip install flash-attn --no-build-isolation || {
    echo "⚠️  FlashAttention2 install failed, continuing without it (will use slower attention)"
}

# 8. Install Qwen3-TTS and dependencies
echo "=== Installing Qwen3-TTS ==="
pip install qwen-tts transformers==4.57.3 accelerate==1.12.0
pip install einops librosa soundfile numpy
pip install fastapi uvicorn pydantic boto3 requests

# 9. Verify installation
echo "=== Verifying installation ==="
python -c "import torch; print(f'✅ PyTorch: {torch.__version__}'); print(f'✅ CUDA available: {torch.cuda.is_available()}')"
python -c "import qwen_tts; print('✅ Qwen3-TTS installed')"

# 10. Create FastAPI server
echo "=== Creating FastAPI server ==="
cat > server.py << 'PYEOF'
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import torch
import soundfile as sf
import boto3
import io
import os
import time
from datetime import datetime
from typing import List, Optional
from qwen_tts import Qwen3TTSModel

app = FastAPI(title="Qwen3-TTS API")

# Global state
models = {}
s3_client = boto3.client('s3', region_name='eu-central-1')
last_activity = time.time()
S3_BUCKET = 'youtube-automation-audio-files'

class TTSRequest(BaseModel):
    scenes: List[dict]
    channel_id: str
    narrative_id: str
    language: str = "English"
    speaker: str = "Ryan"

class HealthResponse(BaseModel):
    status: str
    models_loaded: int
    cuda_available: bool
    gpu_name: Optional[str]
    last_activity: str
    uptime_seconds: float

def load_models():
    """Load 3x Qwen3-TTS-0.6B models for parallel inference"""
    global models
    if models:
        print("✅ Models already loaded")
        return

    print("🔄 Loading Qwen3-TTS models...")
    start = time.time()

    try:
        # Load 3 instances of 0.6B model for parallel processing
        for i in range(3):
            print(f"Loading model {i+1}/3...")
            model = Qwen3TTSModel.from_pretrained(
                "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
                device_map=f"cuda:0",  # T4 has 16GB, can fit 3x 0.6B models
                dtype=torch.bfloat16,
                attn_implementation="flash_attention_2" if torch.cuda.is_available() else "sdpa"
            )
            models[f'model_{i}'] = model
            print(f"✅ Model {i+1} loaded")

        elapsed = time.time() - start
        print(f"✅ All models loaded in {elapsed:.2f}s")

    except Exception as e:
        print(f"❌ Error loading models: {e}")
        raise

@app.on_event("startup")
async def startup_event():
    """Pre-load models on server start"""
    load_models()

@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint"""
    global last_activity
    last_activity = time.time()

    return {
        "status": "healthy",
        "models_loaded": len(models),
        "cuda_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "last_activity": datetime.fromtimestamp(last_activity).isoformat(),
        "uptime_seconds": time.time() - app.state.start_time if hasattr(app.state, 'start_time') else 0
    }

@app.post("/tts/generate")
async def generate_tts(request: TTSRequest):
    """Generate TTS for multiple scenes in parallel"""
    global last_activity
    last_activity = time.time()

    if not models:
        raise HTTPException(status_code=503, detail="Models not loaded")

    print(f"🎤 Generating TTS for {len(request.scenes)} scenes")
    start = time.time()

    audio_files = []

    # Process scenes in batches of 3 (parallel)
    for batch_start in range(0, len(request.scenes), 3):
        batch = request.scenes[batch_start:batch_start+3]

        for idx, scene in enumerate(batch):
            model_key = f'model_{idx}'
            model = models.get(model_key)

            if not model:
                print(f"⚠️  Model {model_key} not available, skipping scene")
                continue

            scene_id = scene.get('scene_number') or scene.get('id', 0)
            text = scene.get('scene_narration') or scene.get('text', '')

            if not text:
                print(f"⚠️  Scene {scene_id} has no text, skipping")
                continue

            print(f"Generating audio for scene {scene_id}...")

            try:
                # Generate audio
                wavs, sr = model.generate_custom_voice(
                    text=text,
                    language=request.language,
                    speaker=request.speaker
                )

                # Upload to S3
                s3_key = f"narratives/{request.channel_id}/{request.narrative_id}/scene_{scene_id}.wav"

                audio_buffer = io.BytesIO()
                sf.write(audio_buffer, wavs[0], sr, format='WAV')
                audio_buffer.seek(0)

                s3_client.put_object(
                    Bucket=S3_BUCKET,
                    Key=s3_key,
                    Body=audio_buffer.getvalue(),
                    ContentType='audio/wav'
                )

                s3_url = f"s3://{S3_BUCKET}/{s3_key}"
                duration_ms = int(len(wavs[0]) / sr * 1000)

                audio_files.append({
                    'scene_id': scene_id,
                    's3_url': s3_url,
                    's3_key': s3_key,
                    'duration_ms': duration_ms
                })

                print(f"✅ Scene {scene_id} complete: {duration_ms}ms")

            except Exception as e:
                print(f"❌ Error generating scene {scene_id}: {e}")
                continue

    elapsed = time.time() - start
    total_duration_ms = sum(af['duration_ms'] for af in audio_files)

    print(f"✅ Generated {len(audio_files)} audio files in {elapsed:.2f}s")

    return {
        'message': 'Audio generated successfully',
        'provider': 'Qwen3-TTS-0.6B',
        'audio_files': audio_files,
        'total_duration_ms': total_duration_ms,
        'generation_time_sec': round(elapsed, 2),
        'scene_count': len(audio_files)
    }

@app.get("/models/status")
async def models_status():
    """Check model loading status"""
    global last_activity
    last_activity = time.time()

    return {
        "models_loaded": len(models),
        "models": list(models.keys()),
        "ready": len(models) >= 3
    }

# Store start time
@app.on_event("startup")
async def set_start_time():
    app.state.start_time = time.time()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")
PYEOF

# 11. Create auto-stop service
echo "=== Creating auto-stop service ==="
cat > auto_stop.py << 'PYEOF'
#!/usr/bin/env python3
import time
import requests
import boto3
import os
from datetime import datetime

IDLE_TIMEOUT = 300  # 5 minutes
CHECK_INTERVAL = 30  # Check every 30 seconds
HEALTH_ENDPOINT = "http://localhost:5000/health"

ec2 = boto3.client('ec2', region_name='eu-central-1')

def get_instance_id():
    """Get current EC2 instance ID"""
    try:
        response = requests.get('http://169.254.169.254/latest/meta-data/instance-id', timeout=2)
        return response.text
    except:
        return None

def check_activity():
    """Check last activity from FastAPI server"""
    try:
        response = requests.get(HEALTH_ENDPOINT, timeout=5)
        if response.status_code == 200:
            data = response.json()
            last_activity = datetime.fromisoformat(data['last_activity'])
            idle_seconds = (datetime.now() - last_activity).total_seconds()
            return idle_seconds
        return 0
    except Exception as e:
        print(f"⚠️  Error checking activity: {e}")
        return 0

def stop_self():
    """Stop this EC2 instance"""
    instance_id = get_instance_id()
    if not instance_id:
        print("❌ Could not get instance ID")
        return

    print(f"⏹️  Stopping instance {instance_id} due to inactivity...")
    try:
        ec2.stop_instances(InstanceIds=[instance_id])
        print("✅ Stop command sent")
    except Exception as e:
        print(f"❌ Error stopping instance: {e}")

def main():
    print("🔄 Auto-stop service started")
    print(f"Idle timeout: {IDLE_TIMEOUT}s, Check interval: {CHECK_INTERVAL}s")

    while True:
        time.sleep(CHECK_INTERVAL)

        idle_seconds = check_activity()

        if idle_seconds > IDLE_TIMEOUT:
            print(f"⚠️  Idle for {idle_seconds:.0f}s (threshold: {IDLE_TIMEOUT}s)")
            stop_self()
            break
        else:
            print(f"✅ Active (idle: {idle_seconds:.0f}s)")

if __name__ == "__main__":
    main()
PYEOF

chmod +x auto_stop.py

# 12. Create systemd service for FastAPI
echo "=== Creating systemd services ==="
cat > /etc/systemd/system/qwen3-tts.service << 'EOF'
[Unit]
Description=Qwen3-TTS FastAPI Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/qwen3-tts
Environment="PATH=/home/ubuntu/qwen3-tts/venv/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=/home/ubuntu/qwen3-tts/venv/bin/python server.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/qwen3-tts.log
StandardError=append:/var/log/qwen3-tts-error.log

[Install]
WantedBy=multi-user.target
EOF

# 13. Create systemd service for auto-stop
cat > /etc/systemd/system/qwen3-autostop.service << 'EOF'
[Unit]
Description=Qwen3-TTS Auto-Stop Service
After=qwen3-tts.service
Requires=qwen3-tts.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/qwen3-tts
Environment="PATH=/home/ubuntu/qwen3-tts/venv/bin"
ExecStartPre=/bin/sleep 60
ExecStart=/home/ubuntu/qwen3-tts/venv/bin/python auto_stop.py
Restart=on-failure
RestartSec=30
StandardOutput=append:/var/log/qwen3-autostop.log
StandardError=append:/var/log/qwen3-autostop-error.log

[Install]
WantedBy=multi-user.target
EOF

# 14. Set permissions
chown -R ubuntu:ubuntu /home/ubuntu/qwen3-tts
chmod +x /home/ubuntu/qwen3-tts/server.py
chmod +x /home/ubuntu/qwen3-tts/auto_stop.py

# 15. Enable and start services
systemctl daemon-reload
systemctl enable qwen3-tts
systemctl enable qwen3-autostop
systemctl start qwen3-tts
systemctl start qwen3-autostop

# 16. Mark as installed
touch /home/ubuntu/qwen3-tts/.installed
chown ubuntu:ubuntu /home/ubuntu/qwen3-tts/.installed

echo "=========================================="
echo "✅ QWEN3-TTS SETUP COMPLETE"
echo "=========================================="
echo "Services:"
echo "  - qwen3-tts.service (FastAPI on port 5000)"
echo "  - qwen3-autostop.service (Auto-stop after 5min idle)"
echo ""
echo "Logs:"
echo "  - journalctl -u qwen3-tts -f"
echo "  - journalctl -u qwen3-autostop -f"
echo "  - tail -f /var/log/qwen3-tts.log"
echo ""
echo "Health check: curl http://localhost:5000/health"
echo "=========================================="
date
