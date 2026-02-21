# GitHub Actions Matrix Update

**File:** `.github/workflows/deploy-production.yml`

## Summary

- **Before:** 26 Lambda functions (including 10 deprecated)
- **After:** 44 Lambda functions (all active)
- **Added:** 24 new functions
- **Removed:** 10 deprecated functions

## Changes

### REMOVED (Deprecated):
- `content-theme-agent` - missing Lambda
- `content-audio-tts` - replaced by content-audio-qwen3tts
- `content-audio-polly` - deprecated
- `content-audio-elevenlabs` - deprecated
- `prompts-api` - should be system-settings-api
- `collect-all-image-prompts` - renamed to collect-image-prompts
- `prepare-image-batches` - deprecated (old batching)
- `merge-image-batches` - deprecated (old batching)
- `save-phase1-to-s3` - deprecated (no more S3 intermediate storage)
- `load-phase1-from-s3` - deprecated (no more S3 intermediate storage)
- `ec2-sd35-control` - renamed to ec2-zimage-control

### ADDED (Active):
- `content-audio-qwen3tts` - current TTS pipeline
- `content-mega-enrichment` - Sprint 2
- `content-search-facts` - Sprint 2
- `content-cliche-detector` - Sprint 3
- `save-final-content` - wrapper for content-save-result
- `collect-audio-scenes` - batch orchestration
- `collect-image-prompts` - batch orchestration
- `distribute-audio` - batch orchestration
- `merge-channel-data` - batch orchestration
- `merge-parallel-results` - batch orchestration
- `system-settings-api` - Node.js API
- `ec2-qwen3-control` - Qwen3-TTS management
- `ec2-zimage-control` - Z-Image management
- `check-qwen3-health` - health check
- `aws-costs-fetcher` - cost import
- `backfill-costs` - retrospective costs
- `audio-library-manager` - SFX management
- `update-sfx-library` - SFX updates
- `log-execution-error` - error logging
- `schema-validator` - validation
- `validate-step-functions-input` - validation
- `debug-test-runner` - testing

## Updated Matrix (Lines 86-115)

Replace lines 87-115 with:

```yaml
        function:
          # Content Generation Pipeline
          - content-narrative
          - content-generate-images
          - content-audio-qwen3tts
          - content-video-assembly
          - content-build-master-config
          - content-mega-enrichment
          - content-search-facts
          - content-cliche-detector
          - content-save-result
          - save-final-content

          # Orchestration (Batching)
          - collect-audio-scenes
          - collect-image-prompts
          - distribute-audio
          - distribute-images
          - merge-channel-data
          - merge-parallel-results

          # Topics Queue (Sprint 1)
          - content-topics-get-next
          - content-topics-list
          - content-topics-add
          - content-topics-bulk-add
          - content-topics-update-status

          # Dashboard/API
          - content-get-channels
          - content-trigger
          - dashboard-content
          - dashboard-costs
          - dashboard-monitoring
          - system-settings-api

          # Infrastructure
          - ec2-qwen3-control
          - ec2-zimage-control
          - check-qwen3-health
          - aws-costs-fetcher
          - backfill-costs
          - audio-library-manager
          - update-sfx-library

          # Support
          - telegram-error-notifier
          - log-execution-error
          - schema-validator
          - validate-step-functions-input
          - debug-test-runner
```

## Manual Update Instructions

1. Open `.github/workflows/deploy-production.yml`
2. Find line 87 (`- content-narrative`)
3. Select lines 87-115 (entire function list)
4. Replace with the matrix above
5. Save file

## Automated Update (if needed)

```bash
# Backup original
cp .github/workflows/deploy-production.yml .github/workflows/deploy-production.yml.backup

# Apply patch manually or use sed/awk
```
