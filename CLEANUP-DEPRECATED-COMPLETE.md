# Cleanup Deprecated Resources - Complete Guide

**Date:** 2026-02-21
**Status:** READY TO EXECUTE

---

## 📋 Summary

This cleanup removes **9 DynamoDB tables** and **8 Lambda functions** that are deprecated and not used in production workflow.

### DynamoDB Tables (9)
- NarrativeTemplates
- ThemeTemplates
- VideoEditingTemplates
- CTATemplates
- DescriptionTemplates
- ThumbnailTemplates
- PromptTemplatesV2
- EC2InstanceLocks
- Users

**Reason:** Template System was designed but not implemented. These tables are empty or unused.

### Lambda Functions (8)
- content-cta-audio → Replaced by content-audio-qwen3tts
- ssml-generator → SSML moved to content-narrative
- merge-image-batches → Old batching system
- prepare-image-batches → Old batching system
- save-phase1-to-s3 → S3 intermediate storage removed
- load-phase1-from-s3 → S3 intermediate storage removed
- queue-failed-ec2 → Retry logic in Step Functions
- retry-ec2-queue → Retry logic in Step Functions

---

## ✅ What's Been Done (Local)

### 1. Backup Scripts Created
- `backup-before-cleanup.sh` - Backs up all resources before deletion
- `cleanup-deprecated-resources.sh` - AWS deletion script with dry-run mode

### 2. Lambda Functions Archived
Moved to `archive/deprecated-lambda-2026-02-21/`:
```
✓ content-cta-audio
✓ ssml-generator
✓ merge-image-batches
✓ prepare-image-batches
✓ save-phase1-to-s3
✓ load-phase1-from-s3
✓ queue-failed-ec2
✓ retry-ec2-queue
```

### 3. GitHub Actions Matrix Updated
- **Before:** 26 functions (10 deprecated)
- **After:** 44 functions (all active)
- **Added:** 24 missing Lambda functions
- **Instructions:** See `GITHUB-ACTIONS-MATRIX-UPDATE.md`

---

## 🚀 Execution Steps

### Step 1: Review What Will Be Deleted

```bash
# Dry-run mode (no changes)
./cleanup-deprecated-resources.sh --dry-run
```

Output will show:
- List of 9 DynamoDB tables
- List of 8 Lambda functions
- No resources will be deleted

### Step 2: Backup Resources (IMPORTANT!)

```bash
# Create backup before deletion
./backup-before-cleanup.sh
```

This will create:
- `backups/cleanup-YYYYMMDD-HHMMSS/dynamodb/` - Table scans
- `backups/cleanup-YYYYMMDD-HHMMSS/lambda/` - Function code + config
- `backups/cleanup-YYYYMMDD-HHMMSS/MANIFEST.md` - Backup details

### Step 3: Execute Cleanup (AWS Deletion)

```bash
# Execute deletion (requires confirmation)
./cleanup-deprecated-resources.sh --execute
```

You will be prompted to type `DELETE` to confirm.

### Step 4: Update GitHub Actions (Manual)

1. Open `.github/workflows/deploy-production.yml`
2. Follow instructions in `GITHUB-ACTIONS-MATRIX-UPDATE.md`
3. Replace Lambda matrix (lines 87-115)

---

## 📊 Impact Analysis

### What WON'T Break:
- ✅ Content generation workflow (uses different Lambdas)
- ✅ Topics Queue (Sprint 1)
- ✅ Dashboard/API
- ✅ Cost tracking
- ✅ Authentication (Cognito)

### What WILL Change:
- ❌ Deprecated Lambda functions deleted from AWS
- ❌ Template tables deleted from DynamoDB
- ✅ GitHub Actions will deploy all 44 active Lambdas (instead of 26)
- ✅ Cleaner IAM policies (after manual update)

### Cost Savings:
- **DynamoDB:** ~$0/month (tables were mostly empty)
- **Lambda:** ~$0/month (functions were not invoked)
- **Maintainability:** Significant improvement

---

## ⚠️ Warnings

1. **This is a ONE-WAY operation** - Deleted AWS resources cannot be easily restored
2. **Backup first** - Always run `backup-before-cleanup.sh` before executing
3. **Production system** - Test in dev/staging first if available
4. **IAM policies** - Manual update needed after deletion to remove references

---

## 🔄 Rollback (If Needed)

If something goes wrong, you can restore from backup:

### DynamoDB Table
```bash
# Restore table from backup
aws dynamodb create-table --cli-input-json file://backup/table-definition.json
aws dynamodb batch-write-item --request-items file://backup/dynamodb/<table>.json
```

### Lambda Function
```bash
# Restore function from backup
aws lambda update-function-code \
  --function-name <function-name> \
  --zip-file fileb://backup/lambda/<function-name>.zip
```

---

## 📝 Post-Cleanup Tasks

After successful cleanup:

1. **Update IAM Policies**
   - Remove references to deleted tables
   - Remove references to deleted Lambdas

2. **Update Documentation**
   - Mark tables as deleted in PRODUCTION-SYSTEM-DOCUMENTATION.md
   - Update architecture diagrams

3. **Monitor Production**
   - Check CloudWatch for errors
   - Verify workflows still run
   - Check Dashboard functionality

4. **Delete CloudWatch Log Groups** (optional)
   ```bash
   aws logs delete-log-group --log-group-name /aws/lambda/content-cta-audio
   aws logs delete-log-group --log-group-name /aws/lambda/ssml-generator
   # ... etc
   ```

---

## 🎯 Next Steps

**Immediate:**
1. Run `backup-before-cleanup.sh`
2. Review backup in `backups/cleanup-*/`
3. Run `cleanup-deprecated-resources.sh --dry-run`

**After Confirmation:**
4. Run `cleanup-deprecated-resources.sh --execute`
5. Update GitHub Actions matrix (see GITHUB-ACTIONS-MATRIX-UPDATE.md)
6. Commit changes to Git
7. Monitor production for 24-48 hours

**Optional:**
8. Update IAM policies
9. Delete CloudWatch log groups
10. Update documentation

---

## 📞 Support

If cleanup causes issues:
1. Check CloudWatch Logs
2. Review Step Functions execution history
3. Restore from backup if needed
4. Check GitHub Actions workflow runs

**Files for reference:**
- `backup-before-cleanup.sh` - Backup script
- `cleanup-deprecated-resources.sh` - Deletion script
- `GITHUB-ACTIONS-MATRIX-UPDATE.md` - Matrix update instructions
- `archive/deprecated-lambda-2026-02-21/` - Archived Lambda code
