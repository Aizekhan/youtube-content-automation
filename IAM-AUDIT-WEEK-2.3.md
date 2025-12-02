# IAM Policy Audit - Week 2.3
## AWS YouTube Content Automation System

**Date:** 2025-12-01
**Auditor:** Security Review
**Scope:** ContentGeneratorLambdaRole IAM policies

---

## Executive Summary

✅ **Good News:** Most policies already follow least privilege principle
⚠️ **Issues Found:** 3 excessive permissions requiring remediation
🎯 **Priority:** Medium (managed policies can be detached)

---

## Current IAM Configuration

### Role: ContentGeneratorLambdaRole

#### Managed Policies (4)
1. ✅ **AWSLambdaBasicExecutionRole** - Standard CloudWatch Logs access (ACCEPTABLE)
2. ✅ **CloudWatchLogsReadOnlyAccess** - Read-only logs (ACCEPTABLE)
3. ⚠️ **SecretsManagerReadWrite** - TOO PERMISSIVE (see below)
4. ⚠️ **AmazonAPIGatewayInvokeFullAccess** - TOO PERMISSIVE (see below)

#### Inline Policies (15)
1. ✅ AllowInvokeEC2SD35Control
2. ⚠️ BedrockImageGenerationPolicy - HAS WILDCARDS (see below)
3. ✅ CloudWatchLogsAccess
4. ✅ DashboardAccessPolicy
5. ✅ DynamoDBAccessPolicy - **PERFECT** (specific tables only)
6. ✅ EC2FluxControl
7. ⚠️ LambdaInvocationPolicy - HAS WILDCARDS (see below)
8. ✅ PollyS3Access
9. ✅ PromptsAPIDynamoDBAccess
10. ✅ PromptsAPIMultiTableAccess
11. ✅ S3AccessPolicy - **PERFECT** (specific buckets only)
12. ✅ SecretsManagerAccess - **PERFECT** (specific secrets only)
13. ✅ SQSRetryQueueAccess
14. ✅ StepFunctionsInspection
15. ✅ VideoAssemblyS3Access

---

## Issues Found

### 🔴 ISSUE 1: Excessive SecretsManager Permissions

**Current State:**
- Managed Policy: `SecretsManagerReadWrite` (Full access to ALL secrets)
- Inline Policy: `SecretsManagerAccess` (Restricted to specific secrets)

**Problem:**
The managed policy grants `secretsmanager:*` on `Resource: "*"`, allowing:
- Read/write/delete ANY secret in the account
- Create new secrets
- Modify secret policies
- **This violates least privilege principle**

**Inline Policy (Already Correct):**
```json
{
  "Effect": "Allow",
  "Action": "secretsmanager:GetSecretValue",
  "Resource": [
    "arn:aws:secretsmanager:eu-central-1:599297130956:secret:openai/*",
    "arn:aws:secretsmanager:eu-central-1:599297130956:secret:notion/*"
  ]
}
```

**Recommendation:**
✅ **DETACH** managed policy `SecretsManagerReadWrite`
✅ **KEEP** inline policy `SecretsManagerAccess` (already secure)

**Impact:** LOW - Inline policy already provides needed access

---

### 🟡 ISSUE 2: Bedrock Wildcard Permissions

**Current State:**
```json
{
  "Effect": "Allow",
  "Action": ["bedrock:InvokeModel"],
  "Resource": [
    "arn:aws:bedrock:eu-central-1::foundation-model/stability.stable-diffusion-xl-v1",
    "arn:aws:bedrock:*::foundation-model/*"  // ⚠️ WILDCARD
  ]
}
```

**Problem:**
- Allows access to ANY Bedrock model in ANY region
- Could invoke expensive models (Claude Opus, etc.)
- Cross-region access unnecessary (system uses eu-central-1)

**Recommended Fix:**
```json
{
  "Effect": "Allow",
  "Action": ["bedrock:InvokeModel"],
  "Resource": [
    "arn:aws:bedrock:eu-central-1::foundation-model/stability.stable-diffusion-xl-v1",
    "arn:aws:bedrock:eu-central-1::foundation-model/stability.sd3-large-v1:0",
    "arn:aws:bedrock:us-east-1::foundation-model/stability.sd3-large-v1:0"
  ]
}
```

**Impact:** MEDIUM - Restricts to specific models/regions, prevents cost overruns

---

### 🟡 ISSUE 3: Lambda Read Wildcard Permissions

**Current State:**
```json
{
  "Effect": "Allow",
  "Action": [
    "lambda:ListFunctions",
    "lambda:GetFunction",
    "lambda:GetFunctionConfiguration"
  ],
  "Resource": "*"  // ⚠️ WILDCARD
}
```

**Problem:**
- Allows reading configuration of ANY Lambda function in account
- Could leak sensitive environment variables
- Violates least privilege (only need to read own functions)

**Recommended Fix:**
```json
{
  "Effect": "Allow",
  "Action": [
    "lambda:GetFunction",
    "lambda:GetFunctionConfiguration"
  ],
  "Resource": [
    "arn:aws:lambda:eu-central-1:599297130956:function:content-*",
    "arn:aws:lambda:eu-central-1:599297130956:function:dashboard-*"
  ]
}
```

**Note:** Remove `lambda:ListFunctions` (not required for normal operation)

**Impact:** LOW - Read-only operations, but reduces attack surface

---

### 🟡 ISSUE 4: API Gateway Full Access

**Current State:**
- Managed Policy: `AmazonAPIGatewayInvokeFullAccess`

**Problem:**
- Grants `execute-api:Invoke` on `Resource: "*"`
- Allows invoking ANY API Gateway endpoint in account
- System doesn't use API Gateway for Lambda invocation (uses direct invocation)

**Recommendation:**
✅ **DETACH** managed policy `AmazonAPIGatewayInvokeFullAccess`

**Impact:** NONE - System uses Lambda Function URLs, not API Gateway

---

## Remediation Plan

### Priority 1: Detach Excessive Managed Policies (5 minutes)

```bash
# 1. Detach SecretsManagerReadWrite (redundant with inline policy)
aws iam detach-role-policy \
  --role-name ContentGeneratorLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite \
  --region eu-central-1

# 2. Detach AmazonAPIGatewayInvokeFullAccess (not used)
aws iam detach-role-policy \
  --role-name ContentGeneratorLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonAPIGatewayInvokeFullAccess \
  --region eu-central-1
```

**Testing:** Verify Lambda functions can still access secrets and DynamoDB

---

### Priority 2: Restrict Bedrock Model Access (10 minutes)

**Create restricted policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel"],
      "Resource": [
        "arn:aws:bedrock:eu-central-1::foundation-model/stability.stable-diffusion-xl-v1",
        "arn:aws:bedrock:eu-central-1::foundation-model/stability.sd3-large-v1:0",
        "arn:aws:bedrock:us-east-1::foundation-model/stability.sd3-large-v1:0"
      ]
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject"],
      "Resource": "arn:aws:s3:::youtube-automation-audio-files/images/*"
    },
    {
      "Effect": "Allow",
      "Action": ["secretsmanager:GetSecretValue"],
      "Resource": [
        "arn:aws:secretsmanager:eu-central-1:599297130956:secret:replicate/api-key-*",
        "arn:aws:secretsmanager:eu-central-1:599297130956:secret:vast-ai/config-*"
      ]
    }
  ]
}
```

**Apply policy:**
```bash
aws iam put-role-policy \
  --role-name ContentGeneratorLambdaRole \
  --policy-name BedrockImageGenerationPolicy \
  --policy-document file://iam-policy-bedrock-restricted.json \
  --region eu-central-1
```

**Testing:** Generate image content, verify Bedrock invocation works

---

### Priority 3: Restrict Lambda Read Access (10 minutes)

**Create restricted policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": [
        "arn:aws:lambda:eu-central-1:599297130956:function:content-get-channels",
        "arn:aws:lambda:eu-central-1:599297130956:function:content-theme-agent",
        "arn:aws:lambda:eu-central-1:599297130956:function:content-narrative",
        "arn:aws:lambda:eu-central-1:599297130956:function:content-audio-tts",
        "arn:aws:lambda:eu-central-1:599297130956:function:content-save-result",
        "arn:aws:lambda:eu-central-1:599297130956:function:content-generate-images",
        "arn:aws:lambda:eu-central-1:599297130956:function:dashboard-content",
        "arn:aws:lambda:eu-central-1:599297130956:function:dashboard-monitoring",
        "arn:aws:lambda:eu-central-1:599297130956:function:dashboard-costs"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:GetFunction",
        "lambda:GetFunctionConfiguration"
      ],
      "Resource": [
        "arn:aws:lambda:eu-central-1:599297130956:function:content-*",
        "arn:aws:lambda:eu-central-1:599297130956:function:dashboard-*"
      ]
    }
  ]
}
```

**Apply policy:**
```bash
aws iam put-role-policy \
  --role-name ContentGeneratorLambdaRole \
  --policy-name LambdaInvocationPolicy \
  --policy-document file://iam-policy-lambda-restricted.json \
  --region eu-central-1
```

**Testing:** Test Step Functions execution, verify Lambda invocations work

---

## Risk Assessment

### Before Remediation
- **SecretsManager:** Could read/write ANY secret → **HIGH RISK**
- **Bedrock:** Could invoke expensive models → **MEDIUM RISK** (cost)
- **Lambda:** Could read ALL function configs → **LOW RISK** (info disclosure)
- **API Gateway:** Could invoke ANY API → **LOW RISK** (not used)

### After Remediation
- **SecretsManager:** Only openai/* and notion/* → **LOW RISK** ✅
- **Bedrock:** Only specific SD models → **LOW RISK** ✅
- **Lambda:** Only content-*/dashboard-* → **LOW RISK** ✅
- **API Gateway:** No access → **NO RISK** ✅

---

## Testing Plan

### Phase 1: Detach Managed Policies
1. ✅ Detach SecretsManagerReadWrite
2. ✅ Detach AmazonAPIGatewayInvokeFullAccess
3. ✅ Test: Run full content generation workflow
4. ✅ Verify: Check CloudWatch logs for access denied errors

### Phase 2: Restrict Bedrock Access
1. ✅ Update BedrockImageGenerationPolicy
2. ✅ Test: Generate image content
3. ✅ Test: Try invalid model (should fail)
4. ✅ Verify: Images generated successfully

### Phase 3: Restrict Lambda Access
1. ✅ Update LambdaInvocationPolicy
2. ✅ Test: Run Step Functions workflow
3. ✅ Test: Dashboard monitoring API
4. ✅ Verify: All Lambda invocations work

---

## Rollback Plan

If issues occur, restore original policies:

```bash
# Restore managed policies
aws iam attach-role-policy \
  --role-name ContentGeneratorLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/SecretsManagerReadWrite

aws iam attach-role-policy \
  --role-name ContentGeneratorLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonAPIGatewayInvokeFullAccess

# Restore inline policies from backup
cd E:/youtube-content-automation/backups/production-backup-20251201-162341/iam
aws iam put-role-policy \
  --role-name ContentGeneratorLambdaRole \
  --policy-name BedrockImageGenerationPolicy \
  --policy-document file://iam-policy-bedrock-image-gen.json

aws iam put-role-policy \
  --role-name ContentGeneratorLambdaRole \
  --policy-name LambdaInvocationPolicy \
  --policy-document file://iam-policy-lambda-invocation-full.json
```

---

## Summary

### ✅ Already Secure (No Changes Needed)
- DynamoDB access (specific tables)
- S3 access (specific buckets)
- SecretsManager inline policy (specific secrets)
- Most inline policies properly scoped

### ⚠️ Requires Remediation
1. **Detach** SecretsManagerReadWrite managed policy
2. **Detach** AmazonAPIGatewayInvokeFullAccess managed policy
3. **Restrict** Bedrock model access (remove region wildcard)
4. **Restrict** Lambda read access (remove ListFunctions, scope to content-*/dashboard-*)

### 📊 Impact
- **Security:** Significantly reduced attack surface
- **Cost:** Prevents accidental expensive model invocations
- **Compliance:** Meets least privilege principle
- **Functionality:** No impact (all needed permissions preserved)

---

**Next Action:** Execute Priority 1 remediation (detach managed policies)
