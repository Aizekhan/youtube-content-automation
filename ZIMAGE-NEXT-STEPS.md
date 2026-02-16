# Z-Image-Turbo Deployment - Next Steps

**Date:** 2026-02-10
**Status:** Installation Complete, Testing Pending
**EC2 IP:** 63.178.201.66

---

## ✅ Completed

1. **Code Created**
   - FastAPI server (`api_server.py`)
   - Deployment scripts
   - Full documentation

2. **EC2 Installation**
   - Created `/home/ubuntu/zimage-api/`
   - Python venv with all dependencies
   - PyTorch 2.5.1+cu121 with CUDA support
   - Diffusers 0.37.0.dev0 (from source)
   - All other dependencies installed

3. **Verification**
   - ✅ CUDA available: True
   - ✅ GPU detected: NVIDIA A10G
   - ✅ All imports working

---

## ⚠️ Current Issues

### 1. SD3.5 Service Auto-Starting

**Problem:** Old SD3.5 service (`sd-api.service`) is running and occupying port 5000

**Evidence:**
```bash
curl http://63.178.201.66:5000/health
# Returns: {"model":"sd-3.5-medium","model_loaded":true}
```

**Solution:**
```bash
ssh -i E:/youtube-content-automation/n8n-key.pem ubuntu@63.178.201.66
sudo systemctl stop sd-api
sudo systemctl disable sd-api
```

### 2. Disk Space Critical

**Problem:** 91.9% disk usage (88.87GB / 96.73GB used)

**Breakdown:**
- SD3.5 model: ~12GB
- Z-Image model: ~6GB (downloading)
- Python venvs: ~16GB (2 venvs)
- Logs/cache: ~54GB

**Immediate Actions:**
```bash
# Clean up logs (should free 2-10GB)
sudo journalctl --vacuum-time=7d
sudo find /var/log -type f -mtime +7 -delete

# Clean pip cache
pip cache purge

# Remove old Hugging Face downloads
rm -rf ~/.cache/huggingface/hub/.locks
```

**After Z-Image Verified:**
```bash
# Remove SD3.5 installation (frees ~30GB)
rm -rf /home/ubuntu/sd35-api
```

### 3. Systemd Service Not Created

**Problem:** Z-Image server started manually with `nohup`, will not survive reboot

**Solution:**
```bash
# Create systemd service
sudo tee /etc/systemd/system/zimage-api.service > /dev/null <<'EOF'
[Unit]
Description=Z-Image-Turbo API Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/zimage-api
Environment="PATH=/home/ubuntu/zimage-api/venv/bin"
ExecStart=/home/ubuntu/zimage-api/venv/bin/python /home/ubuntu/zimage-api/api_server.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=zimage-api

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable zimage-api
sudo systemctl start zimage-api
```

---

## 📋 Next Session Action Plan

### Phase 1: Clean Up and Switch Services (10 min)

```bash
# 1. SSH to EC2
ssh -i E:/youtube-content-automation/n8n-key.pem ubuntu@63.178.201.66

# 2. Stop old SD3.5 service
sudo systemctl stop sd-api
sudo systemctl disable sd-api

# 3. Clean disk space
sudo journalctl --vacuum-time=7d
sudo apt-get clean
pip cache purge

# 4. Check space freed
df -h /

# 5. Kill any Z-Image processes
pkill -f "python.*api_server.py"

# 6. Create systemd service for Z-Image
sudo tee /etc/systemd/system/zimage-api.service > /dev/null <<'EOF'
[Unit]
Description=Z-Image-Turbo API Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/zimage-api
Environment="PATH=/home/ubuntu/zimage-api/venv/bin"
ExecStart=/home/ubuntu/zimage-api/venv/bin/python /home/ubuntu/zimage-api/api_server.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=zimage-api

[Install]
WantedBy=multi-user.target
EOF

# 7. Enable and start Z-Image service
sudo systemctl daemon-reload
sudo systemctl enable zimage-api
sudo systemctl start zimage-api

# 8. Wait for model to load (2-3 minutes)
sleep 180

# 9. Check status
sudo systemctl status zimage-api
sudo journalctl -u zimage-api -n 50
```

### Phase 2: Test Z-Image API (5 min)

```bash
# 1. Health check
curl http://localhost:5000/health

# Expected response:
# {
#   "status": "healthy",
#   "model": "z-image-turbo",
#   "model_loaded": true,
#   "device": "cuda",
#   "gpu": "NVIDIA A10G"
# }

# 2. Test image generation
curl -X POST http://localhost:5000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A beautiful sunset over mountains", "width": 1024, "height": 1024}' \
  --output test.png

# 3. Check image
ls -lh test.png  # Should be 2-5MB

# 4. Check generation time
# Should be in response header X-Generation-Time: ~0.5-1.0 seconds
```

### Phase 3: Update Lambda (5 min)

On local machine:

```bash
cd E:/youtube-content-automation/aws/lambda/content-generate-images

# Edit lambda_function.py:
# Line 273: cost = 0.003  # Updated from 0.0117
# Line 280: provider = 'ec2-zimage-turbo'

# Deploy
python create_zip.py
aws lambda update-function-code \
  --function-name content-generate-images \
  --zip-file fileb://function.zip \
  --region eu-central-1
```

### Phase 4: End-to-End Test (10 min)

```bash
# 1. Start Step Functions execution
aws stepfunctions start-execution \
  --state-machine-arn "arn:aws:states:eu-central-1:599297130956:stateMachine:ContentGenerator" \
  --region eu-central-1 \
  --name "test-zimage-$(date +%s)" \
  --input '{
    "channel_ids":["UCRmO5HB89GW_zjX3dJACfzw"],
    "user_id":"user_test_zimage",
    "max_scenes":3
  }'

# 2. Monitor (should complete in 2-3 min vs 4-5 min)
EXEC_ARN="<from above>"
watch -n 10 "aws stepfunctions describe-execution --execution-arn $EXEC_ARN --region eu-central-1 --query status"

# 3. Verify results
aws dynamodb scan \
  --table-name GeneratedContent \
  --region eu-central-1 \
  --filter-expression "channel_id = :chid" \
  --expression-attribute-values '{":chid":{"S":"UCRmO5HB89GW_zjX3dJACfzw"}}' \
  --limit 1
```

### Phase 5: Cleanup (Optional, after verification)

```bash
# After 24h of successful Z-Image operation:

# 1. Remove SD3.5 installation (frees ~30GB)
rm -rf /home/ubuntu/sd35-api

# 2. Clean up old backups
sudo journalctl --vacuum-size=100M
```

---

## 🎯 Success Criteria

- [ ] Z-Image service running and auto-starting
- [ ] Health endpoint returns `model: z-image-turbo`
- [ ] Test image generated in < 2 seconds
- [ ] Image quality acceptable
- [ ] Disk usage < 80%
- [ ] End-to-end workflow succeeds
- [ ] Cost per image reduced to $0.003

---

## 📂 Files Created

All files in `E:\youtube-content-automation\ec2-zimage-turbo\`:

- `api_server.py` - FastAPI server ✅
- `requirements.txt` - Python dependencies ✅
- `deploy.sh` - Deployment script ✅
- `zimage-api.service` - Systemd service template ✅
- `quick-deploy.bat` - Windows deployment script ✅
- `README.md` - Full documentation ✅

Documentation:
- `ZIMAGE-TURBO-MIGRATION.md` - Migration plan ✅
- `ZIMAGE-NEXT-STEPS.md` - This file ✅

---

## 🔍 Troubleshooting

### Model Not Loading

**Check logs:**
```bash
sudo journalctl -u zimage-api -f
```

**Common issues:**
- Out of memory → Clean up disk space
- Import errors → Reinstall dependencies
- CUDA errors → Check nvidia-smi (warning is OK, CUDA still works)

### Port Already in Use

**Check what's using port 5000:**
```bash
sudo lsof -i:5000
sudo systemctl stop sd-api
```

### Slow Generation

**Verify GPU usage:**
```bash
# In sd35-api venv (which has working PyTorch):
/home/ubuntu/sd35-api/venv/bin/python -c "import torch; print('CUDA:', torch.cuda.is_available())"
```

---

## 📞 Quick Commands

```bash
# SSH to EC2
ssh -i E:/youtube-content-automation/n8n-key.pem ubuntu@63.178.201.66

# Service management
sudo systemctl status zimage-api
sudo systemctl restart zimage-api
sudo journalctl -u zimage-api -f

# Test health
curl http://localhost:5000/health

# Check disk
df -h /

# Monitor GPU (from SD35 venv since nvidia-smi has issues)
watch -n 1 /home/ubuntu/sd35-api/venv/bin/python -c "import torch; print('CUDA:', torch.cuda.is_available())"
```

---

**Total Time Required:** ~30 minutes
**Risk Level:** Low (easy rollback to SD3.5)
**Expected Savings:** 83-90% on compute costs

**Ready to continue!** 🚀
