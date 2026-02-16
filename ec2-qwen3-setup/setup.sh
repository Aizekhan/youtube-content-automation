#!/bin/bash
set -e

echo "🚀 Setting up Qwen3-TTS Production Server"

# Update system
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv libsndfile1

# Create app directory
mkdir -p /home/ubuntu/qwen3-tts
cd /home/ubuntu/qwen3-tts

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install PyTorch with CUDA support
pip install --upgrade pip
pip install torch==2.5.1 torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install dependencies
pip install fastapi uvicorn pydantic soundfile boto3 numpy

# Install Qwen-TTS (if available on PyPI, otherwise from source)
pip install qwen-tts || echo "⚠️ Qwen-TTS not available on PyPI, will need manual installation"

echo "✅ Setup complete!"
echo "📁 App directory: /home/ubuntu/qwen3-tts"
echo "🐍 Virtual env: /home/ubuntu/qwen3-tts/venv"
