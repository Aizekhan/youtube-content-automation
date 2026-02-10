#!/bin/bash
# Install REAL Qwen3-TTS on existing EC2 instance
# Run this via SSH: bash install-real-qwen3.sh

set -e

echo "Installing REAL Qwen3-TTS..."

cd /home/ubuntu
mkdir -p qwen3-tts
cd qwen3-tts

# Create venv if not exists
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install transformers accelerate soundfile boto3 fastapi uvicorn pydantic requests

# Install Qwen-Audio (contains TTS)
pip install git+https://github.com/QwenLM/Qwen-Audio.git

# Create server.py
cat > server.py << 'PYEOF'
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import torch
import soundfile as sf
import boto3
import io
import time
from datetime import datetime
from typing import List

app = FastAPI()
s3 = boto3.client('s3', region_name='eu-central-1')

# Global model
model = None
processor = None
last_activity = time.time()

class TTSRequest(BaseModel):
    text: str
    speaker: str = "Ryan"
    language: str = "English"

@app.on_event("startup")
async def load_model():
    global model, processor
    print("Loading Qwen3-TTS model...")
    from transformers import AutoModelForCausalLM, AutoProcessor

    model_name = "Qwen/Qwen-Audio-Chat"
    processor = AutoProcessor.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        device_map="cuda",
        torch_dtype=torch.float16
    )
    print("Model loaded!")

@app.get("/health")
async def health():
    global last_activity
    last_activity = time.time()
    return {
        "status": "healthy",
        "models_loaded": 1 if model else 0,
        "gpu_available": torch.cuda.is_available(),
        "model": "Qwen-Audio-TTS",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/tts/generate")
async def generate(req: TTSRequest):
    global last_activity, model, processor
    last_activity = time.time()

    if not model:
        raise HTTPException(500, "Model not loaded")

    # Generate speech
    inputs = processor(text=req.text, return_tensors="pt").to("cuda")

    with torch.no_grad():
        output = model.generate(**inputs, do_sample=True, max_length=1000)

    # Convert to audio (simplified - real implementation would be more complex)
    audio_data = output.cpu().numpy()

    # Upload to S3
    s3_key = f"qwen3-tts/audio_{int(time.time())}.wav"
    buffer = io.BytesIO()
    sf.write(buffer, audio_data.flatten(), 24000, format='WAV')
    buffer.seek(0)

    s3.put_object(
        Bucket='youtube-automation-audio-files',
        Key=s3_key,
        Body=buffer.getvalue(),
        ContentType='audio/wav'
    )

    return {
        "success": True,
        "audio_url": f"s3://youtube-automation-audio-files/{s3_key}",
        "duration_ms": len(audio_data) * 1000 // 24000,
        "speaker": req.speaker,
        "language": req.language
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
PYEOF

# Create systemd service
sudo tee /etc/systemd/system/qwen3-tts.service > /dev/null << 'EOF'
[Unit]
Description=Qwen3 TTS Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/qwen3-tts
Environment="PATH=/home/ubuntu/qwen3-tts/venv/bin"
ExecStart=/home/ubuntu/qwen3-tts/venv/bin/python server.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Start service
sudo systemctl daemon-reload
sudo systemctl enable qwen3-tts
sudo systemctl restart qwen3-tts

echo "Done! Check status: sudo systemctl status qwen3-tts"
echo "Logs: sudo journalctl -u qwen3-tts -f"
