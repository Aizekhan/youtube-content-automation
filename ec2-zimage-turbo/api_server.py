#!/usr/bin/env python3
"""
Z-Image-Turbo API Server for EC2
Fast image generation using Z-Image-Turbo model

Performance:
- Generation time: ~0.5-1 second per image (vs SD3.5: ~5.5 seconds)
- VRAM usage: ~8GB (vs SD3.5: ~13GB)
- Quality: High quality, excellent prompt following
"""

import os
import sys
import time
import shutil
from datetime import datetime
from pathlib import Path

import torch
from flask import Flask, request, send_file, jsonify
from PIL import Image
from diffusers import ZImagePipeline

# Initialize Flask app
app = Flask(__name__)

# Global variables
pipeline = None
model_loaded = False
last_request_time = datetime.now()

# Configuration
MODEL_NAME = "Tongyi-MAI/Z-Image-Turbo"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
API_PORT = 5000
TEMP_DIR = Path("/tmp/zimage-outputs")
TEMP_DIR.mkdir(exist_ok=True)

# Performance tracking
generation_count = 0
total_generation_time = 0.0


def load_model():
    """Load Z-Image-Turbo model into memory"""
    global pipeline, model_loaded

    print(f"🚀 Loading Z-Image-Turbo model on {DEVICE}...")
    start_time = time.time()

    try:
        pipeline = ZImagePipeline.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.bfloat16,
            low_cpu_mem_usage=False,
        )
        pipeline.to(DEVICE)

        # Warm-up generation to compile kernels
        print("🔥 Warming up model...")
        _ = pipeline(
            prompt="test",
            num_inference_steps=9,
            guidance_scale=0.0,
            height=512,
            width=512,
            generator=torch.Generator(DEVICE).manual_seed(42)
        ).images[0]

        load_time = time.time() - start_time
        model_loaded = True

        print(f"✅ Model loaded successfully in {load_time:.2f}s")
        print(f"   Device: {DEVICE}")
        print(f"   Model: {MODEL_NAME}")

        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
            print(f"   GPU: {gpu_name} ({gpu_memory:.1f}GB)")

        return True

    except Exception as e:
        print(f"❌ Failed to load model: {e}")
        import traceback
        traceback.print_exc()
        model_loaded = False
        return False


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    global last_request_time
    last_request_time = datetime.now()

    # Get disk usage
    disk = shutil.disk_usage("/")
    disk_used_gb = disk.used / (1024**3)
    disk_free_gb = disk.free / (1024**3)
    disk_total_gb = disk.total / (1024**3)
    disk_usage_percent = (disk.used / disk.total) * 100

    # Get GPU info if available
    gpu_info = {}
    if torch.cuda.is_available():
        gpu_info = {
            "name": torch.cuda.get_device_name(0),
            "memory_allocated_gb": torch.cuda.memory_allocated(0) / 1024**3,
            "memory_reserved_gb": torch.cuda.memory_reserved(0) / 1024**3,
            "memory_total_gb": torch.cuda.get_device_properties(0).total_memory / 1024**3,
        }

    # Calculate average generation time
    avg_gen_time = (
        total_generation_time / generation_count
        if generation_count > 0
        else 0.0
    )

    return jsonify({
        "status": "healthy",
        "model": "z-image-turbo",
        "model_loaded": model_loaded,
        "device": DEVICE,
        "gpu": gpu_info.get("name", "N/A"),
        "generations_count": generation_count,
        "avg_generation_time_sec": round(avg_gen_time, 2),
        "storage": {
            "ebs_100gb": {
                "total_gb": round(disk_total_gb, 2),
                "used_gb": round(disk_used_gb, 2),
                "free_gb": round(disk_free_gb, 2),
                "usage_percent": round(disk_usage_percent, 1)
            }
        },
        "gpu_memory": gpu_info if gpu_info else None,
        "last_request": last_request_time.isoformat()
    })


@app.route('/generate', methods=['POST'])
def generate_image():
    """
    Generate image from text prompt

    Request body:
    {
        "prompt": "A beautiful sunset over mountains",
        "height": 1024,
        "width": 1024,
        "seed": 42  // optional
    }

    Note: Z-Image-Turbo uses fixed num_inference_steps=9 and guidance_scale=0.0
    """
    global last_request_time, generation_count, total_generation_time
    last_request_time = datetime.now()

    if not model_loaded:
        return jsonify({"error": "Model not loaded"}), 500

    try:
        # Parse request
        data = request.get_json()
        prompt = data.get('prompt', '')
        height = data.get('height', 1024)
        width = data.get('width', 1024)
        seed = data.get('seed', int(time.time()))

        if not prompt:
            return jsonify({"error": "No prompt provided"}), 400

        print(f"\n🎨 Generating image:")
        print(f"   Prompt: {prompt[:100]}...")
        print(f"   Size: {width}x{height}")
        print(f"   Seed: {seed}")

        start_time = time.time()

        # Generate image with Z-Image-Turbo optimal settings
        # Note: Z-Image-Turbo uses 9 steps (8 DiT forwards) and guidance_scale=0.0
        image = pipeline(
            prompt=prompt,
            num_inference_steps=9,  # Fixed for Z-Image-Turbo
            guidance_scale=0.0,      # Fixed for Z-Image-Turbo
            height=height,
            width=width,
            generator=torch.Generator(DEVICE).manual_seed(seed)
        ).images[0]

        generation_time = time.time() - start_time

        # Update statistics
        generation_count += 1
        total_generation_time += generation_time

        print(f"✅ Generated in {generation_time:.2f}s")

        # Save to temporary file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = TEMP_DIR / f"zimage_{timestamp}_{seed}.png"
        image.save(output_path, format='PNG')

        # Return image file
        response = send_file(
            output_path,
            mimetype='image/png',
            as_attachment=False
        )

        # Add generation time to response headers
        response.headers['X-Generation-Time'] = f"{generation_time:.2f}"

        return response

    except Exception as e:
        print(f"❌ Generation failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/stats', methods=['GET'])
def get_stats():
    """Get generation statistics"""
    avg_gen_time = (
        total_generation_time / generation_count
        if generation_count > 0
        else 0.0
    )

    return jsonify({
        "generations_total": generation_count,
        "total_time_sec": round(total_generation_time, 2),
        "avg_generation_time_sec": round(avg_gen_time, 2),
        "model": "z-image-turbo",
        "model_loaded": model_loaded
    })


def cleanup_old_images():
    """Clean up temporary images older than 1 hour"""
    try:
        current_time = time.time()
        for img_path in TEMP_DIR.glob("*.png"):
            if current_time - img_path.stat().st_mtime > 3600:  # 1 hour
                img_path.unlink()
                print(f"🗑️  Cleaned up old image: {img_path.name}")
    except Exception as e:
        print(f"⚠️  Cleanup failed: {e}")


if __name__ == '__main__':
    print("="*60)
    print("🚀 Z-Image-Turbo API Server")
    print("="*60)

    # Check CUDA availability
    if torch.cuda.is_available():
        print(f"✅ CUDA available: {torch.cuda.get_device_name(0)}")
        print(f"   CUDA version: {torch.version.cuda}")
        print(f"   PyTorch version: {torch.__version__}")
    else:
        print("⚠️  CUDA not available, using CPU (slow!)")

    # Load model
    if not load_model():
        print("❌ Failed to load model, exiting...")
        sys.exit(1)

    # Clean up old images on startup
    cleanup_old_images()

    print(f"\n✅ Server starting on port {API_PORT}")
    print(f"   Health check: http://0.0.0.0:{API_PORT}/health")
    print(f"   Generate: http://0.0.0.0:{API_PORT}/generate")
    print(f"   Stats: http://0.0.0.0:{API_PORT}/stats")
    print("="*60)

    # Start Flask server
    app.run(
        host='0.0.0.0',
        port=API_PORT,
        debug=False,
        threaded=True
    )
