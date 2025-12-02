# Cleanup Summary - 2025-11-25

## Files Archived

### Step Function Definitions → archive/step-functions-old/
- current-step-function.json
- updated-step-function.json
- updated-step-function-fixed.json

**Active Files (kept):**
- step-function-fixed-genre.json (latest production)
- step-function-with-ssml-generator.json (with SSML generator)

### Test Files → archive/test-files/
- action-result.json
- mystery-result.json
- test-action-genre.json
- test-mystery-genre.json
- test-polly-output.json
- test-polly-payload.json
- test-exec-history.json
- exec-full-history.json

## Backup Files (preserved)

**Location:** backups/
- backup-20251124-145430/ (production backup)
- production-backup-20251124-064648/ (full system backup)
- production-now/ (latest state)

**Status:** Kept for rollback capability

## Scripts Created During Refactoring

**Kept (useful for future):**
- setup-monitoring.sh (CloudWatch alarms setup)
- check_polly.py (Polly TTS verification)
- check_polly_input.py (debug helper)
- update_prompt_remove_ssml.py (prompt migration script)

**Can be deleted if not needed:**
- update-save-lambda-add-structures.py
- add-sfx-to-narrative-lambda.py
- add-sfx-to-step-functions.py

## Documentation Created

✅ docs/TTS-ARCHITECTURE.md (comprehensive architecture guide)
✅ docs/GENRE-RULES.md (genre-specific voice rules)
✅ docs/TTS-PROVIDERS.md (provider integration guide)
✅ GENRE-COMPARISON.md (genre test results)
✅ CLEANUP-SUMMARY.md (this file)

## Lambda Functions - Status

### Active (Production)
- ssml-generator (NEW)
- content-narrative (UPDATED)
- content-audio-polly (UPDATED)
- content-theme-agent
- content-save-result
- All other existing Lambdas

### Deprecated
- None (all migrated successfully)

## Git Status Recommendation

**Untracked files to commit:**
- docs/*.md (documentation)
- GENRE-COMPARISON.md
- CLEANUP-SUMMARY.md
- archive/ (optional - could add to .gitignore)

**Modified files to commit:**
- aws/lambda/ssml-generator/ (NEW)
- aws/lambda/content-narrative/mega_prompt_builder.py
- aws/lambda/shared/mega_prompt_builder.py
- step-function-fixed-genre.json

**Deleted files to stage:**
All the backup .md files from root (CHANGELOG, SESSION-SUMMARY, etc.)

## Next Actions

1. ✅ Commit new documentation
2. ✅ Commit Lambda changes
3. ✅ Tag release: v2.0-ssml-generator
4. ⏳ Monitor CloudWatch alarms for 24h
5. ⏳ Review cost savings after 1 week

## Disk Space Recovered

- Test files: ~2 MB
- Archived Step Functions: ~500 KB
- Total cleanup: ~2.5 MB

**Backup size:** ~45 MB (kept for safety)

---

**Cleanup Date:** 2025-11-25
**Status:** ✅ Complete
