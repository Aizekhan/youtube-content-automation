# Z-Image-Turbo NVML Issue & Solution

**Date:** 2026-02-10
**Issue:** RuntimeError during model loading to CUDA
**Status:** Workaround Available

---

## Problem

When loading Z-Image-Turbo model to CUDA device:

```
RuntimeError: NVML_SUCCESS == DriverAPI::get()->nvmlInit_v2_()
INTERNAL ASSERT FAILED at "../c10/cuda/CUDACachingAllocator.cpp":963
```

**Root Cause:** NVIDIA driver/library version mismatch affects NVML initialization

**Impact:**
- PyTorch CUDA works fine for computation ✅
- NVML monitoring library fails ❌
- Model `.to(device)` crashes when PyTorch tries to query GPU via NVML ❌

---

## Solution: Disable NVML Checks

### Option 1: Environment Variables (Applied)

Added to systemd service:

```bash
Environment="PYTORCH_NVML_BASED_CUDA_CHECK=0"
Environment="CUDA_LAUNCH_BLOCKING=0"
```

This tells PyTorch to skip NVML checks and use CUDA directly.

### Option 2: Fix in Code

Modify `api_server.py` line 56:

```python
# Before
pipeline.to(DEVICE)

# After - with error handling
try:
    pipeline.to(DEVICE)
except RuntimeError as e:
    if "NVML" in str(e):
        print("⚠️  NVML error, trying workaround...")
        import os
        os.environ["PYTORCH_NVML_BASED_CUDA_CHECK"] = "0"
        # Reload and retry
        pipeline.to(DEVICE)
    else:
        raise
```

### Option 3: Fix NVIDIA Driver (Most Reliable)

```bash
# Update NVIDIA driver
sudo apt-get update
sudo apt-get install --reinstall nvidia-driver-580

# Reboot
sudo reboot
```

---

## Current Status

✅ **Systemd service updated** with NVML workaround
✅ **Service restarted**
⏳ **Waiting for model to load** (2-3 minutes)

---

## Next Steps

1. **Wait for service to fully start** (check logs)
   ```bash
   sudo journalctl -u zimage-api -f
   ```

2. **Test health endpoint**
   ```bash
   curl http://localhost:5000/health
   ```

3. **If still fails:**
   - Option A: Modify code (api_server.py)
   - Option B: Update NVIDIA driver
   - Option C: Use CPU (slow fallback)

---

## Alternative: Use SD3.5 for Now

If Z-Image continues to have issues:

```bash
# Rollback to SD3.5
sudo systemctl stop zimage-api
sudo systemctl start sd-api  # If exists

# Or manually run SD3.5
cd /home/ubuntu/sd35-api
./venv/bin/python api_server.py
```

SD3.5 works because it was deployed when driver was functional.

---

## Long-term Fix

**Recommendation:** Update NVIDIA driver on next maintenance window

**Why not now?**
- Requires reboot
- SD3.5 working as fallback
- Can complete migration later

**When to do:**
- During low-traffic period
- After backing up current setup
- Test thoroughly after update

---

**Files Modified:**
- `/etc/systemd/system/zimage-api.service` - Added NVML environment vars

**Service Status:** Restarting with workaround...
