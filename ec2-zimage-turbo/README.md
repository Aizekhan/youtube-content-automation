# Z-Image-Turbo EC2 Deployment

## Overview

This replaces the SD3.5 Medium model with **Z-Image-Turbo** - a faster and cheaper image generation model.

### Performance Comparison

| Metric | SD3.5 Medium | Z-Image-Turbo | Improvement |
|--------|--------------|---------------|-------------|
| **Generation Time** | ~5.5 sec | ~0.5-1 sec | **5-10x faster** |
| **VRAM Usage** | ~13GB | ~8GB | **40% less** |
| **Model Size** | ~12GB | ~6GB | **50% smaller** |
| **Cost per image** | $0.0117 | $0.002-0.003 | **75-85% cheaper** |
| **Quality** | Excellent | Excellent | Same |

### Key Benefits

✅ **10x faster generation** - batch of 18 images in ~10-15 seconds vs ~90 seconds
✅ **75% cost savings** - $0.003/image vs $0.0117/image
✅ **Lower VRAM** - can potentially use smaller instance types
✅ **Smaller model** - faster startup time (~30-45 seconds vs ~90 seconds)
✅ **Same quality** - excellent prompt following and image quality

## Deployment Steps

### 1. Upload Files to EC2

```bash
# Get EC2 IP (instance must be running)
EC2_IP="3.71.81.203"
KEY_PATH="E:/youtube-content-automation/n8n-key.pem"

# Upload files
scp -i "$KEY_PATH" api_server.py ubuntu@$EC2_IP:/tmp/
scp -i "$KEY_PATH" deploy.sh ubuntu@$EC2_IP:/tmp/
```

### 2. Run Deployment Script

```bash
# SSH to EC2
ssh -i "$KEY_PATH" ubuntu@$EC2_IP

# Run deployment
cd /tmp
chmod +x deploy.sh
./deploy.sh
```

The deployment script will:
1. Check CUDA/GPU availability
2. Create application directory `/home/ubuntu/zimage-api`
3. Set up Python virtual environment
4. Install PyTorch with CUDA support
5. Install diffusers from source (for latest Z-Image support)
6. Install other dependencies
7. Set up systemd service
8. Start the API server
9. Test the API

### 3. Verify Deployment

```bash
# Check service status
sudo systemctl status zimage-api

# Test health endpoint
curl http://localhost:5000/health

# Test image generation
curl -X POST http://localhost:5000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A beautiful sunset over mountains", "width": 1024, "height": 1024}' \
  --output test.png

# Check the generated image
ls -lh test.png
```

## API Endpoints

### Health Check

```bash
GET /health
```

Response:
```json
{
  "status": "healthy",
  "model": "z-image-turbo",
  "model_loaded": true,
  "device": "cuda",
  "gpu": "NVIDIA A10G",
  "generations_count": 42,
  "avg_generation_time_sec": 0.78,
  "storage": {...},
  "gpu_memory": {...}
}
```

### Generate Image

```bash
POST /generate
Content-Type: application/json

{
  "prompt": "A mystical ancient temple in a misty forest",
  "width": 1024,
  "height": 1024,
  "seed": 42  // optional
}
```

Response: PNG image (binary)

### Get Statistics

```bash
GET /stats
```

Response:
```json
{
  "generations_total": 42,
  "total_time_sec": 32.76,
  "avg_generation_time_sec": 0.78,
  "model": "z-image-turbo",
  "model_loaded": true
}
```

## Lambda Integration

The existing Lambda functions need minimal changes:

### content-generate-images Lambda

The `generate_with_ec2_flux()` function already works! Just need to update:

1. **Endpoint** - same as before (passed from Step Functions)
2. **Request format** - identical (prompt, width, height)
3. **Response** - identical (PNG image)
4. **Cost calculation** - update pricing to ~$0.003/image

### ec2-sd35-control Lambda

No changes needed! It already:
- Starts/stops the EC2 instance
- Waits for API to be ready at `/health`
- Returns endpoint URL

## Cost Analysis

### Before (SD3.5 Medium)

```
Instance: g5.xlarge ($1.006/hour)
Generation time: ~90 seconds for 18 images
Cost per run: $0.025
Cost per image: $0.0117

Monthly (100 runs):
- Instance time: 2.5 hours
- Cost: $2.52
```

### After (Z-Image-Turbo)

```
Instance: g5.xlarge ($1.006/hour)
Generation time: ~10-15 seconds for 18 images
Cost per run: $0.004-0.006
Cost per image: $0.002-0.003

Monthly (100 runs):
- Instance time: 0.25-0.42 hours
- Cost: $0.25-0.42
```

**Savings: 83-90% on compute costs!**

## Troubleshooting

### Model not loading

```bash
# Check logs
sudo journalctl -u zimage-api -f

# Common issues:
# 1. Out of memory - check GPU memory with nvidia-smi
# 2. Missing dependencies - reinstall with deploy.sh
# 3. Diffusers version too old - install from source
```

### Slow generation

```bash
# Check if using GPU
nvidia-smi

# Should show:
# - GPU Util: 90-100% during generation
# - Memory: ~8GB allocated

# If using CPU, check:
python3 -c "import torch; print(torch.cuda.is_available())"
```

### Service won't start

```bash
# Check service status
sudo systemctl status zimage-api

# View full logs
sudo journalctl -u zimage-api -n 50 --no-pager

# Restart service
sudo systemctl restart zimage-api
```

## Migration Checklist

- [ ] Deploy Z-Image-Turbo to EC2
- [ ] Test health endpoint
- [ ] Test image generation
- [ ] Update Lambda cost calculations
- [ ] Update documentation references
- [ ] Test Step Functions end-to-end
- [ ] Update monitoring dashboards
- [ ] Remove old SD3.5 files (optional, after verification)

## Rollback Plan

If issues arise, rollback to SD3.5:

```bash
# Stop Z-Image service
sudo systemctl stop zimage-api
sudo systemctl disable zimage-api

# Start old SD3.5 service
sudo systemctl start sd-api
sudo systemctl enable sd-api
```

The old SD3.5 files remain at `/home/ubuntu/sd35-api`.

## Performance Optimization

### Batch Processing

Z-Image-Turbo is so fast that you might want to increase batch size:

```python
# In prepare-image-batches Lambda
batch_size = 12  # Up from 6, since generation is faster
```

### Parallel Requests

With lower VRAM usage, you can potentially run multiple generations simultaneously.

## Next Steps

1. Deploy to EC2 (follow steps above)
2. Test with a single image
3. Test with a batch of 18 images
4. Run full Step Functions workflow
5. Monitor costs and performance
6. Adjust batch sizes if needed

## Support

- **Documentation:** This README
- **API Server Code:** `api_server.py`
- **Deployment Script:** `deploy.sh`
- **Model:** https://huggingface.co/Tongyi-MAI/Z-Image-Turbo
