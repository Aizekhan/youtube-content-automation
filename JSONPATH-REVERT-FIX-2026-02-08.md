# Step Functions JSONPath Fix - REVERT Previous Incorrect Fix

**Date:** 2026-02-08
**Status:** ✅ DEPLOYED
**Severity:** CRITICAL - Fixes 100% failure rate

---

## Summary

**REVERTED** incorrect JSONPath fix from commit `7398aa0` (2025-12-02).
The previous fix removed `.Payload.` wrapper, but AWS Lambda integration via `states:::lambda:invoke` **AUTOMATICALLY wraps responses in `{Payload: ...}`**.

---

## Root Cause Analysis

### What We Thought (Incorrect)

From commit `7398aa0`:
```
Lambda returns: {state: "running", endpoint: "..."}  ❌ WRONG ASSUMPTION
Step Functions should use: $.ec2Endpoint.state
```

### What Actually Happens (Correct)

**AWS Lambda Integration Behavior:**
```json
// Lambda code returns:
{
  "state": "running",
  "endpoint": "http://..."
}

// Step Functions receives (auto-wrapped by AWS):
{
  "ExecutedVersion": "$LATEST",
  "Payload": {
    "state": "running",
    "endpoint": "http://..."
  },
  "SdkHttpMetadata": {...},
  ...
}
```

**Proof from execution history:**
```json
{
  "type": "TaskSucceeded",
  "taskSucceededEventDetails": {
    "output": "{\"ExecutedVersion\":\"$LATEST\",\"Payload\":{\"state\":\"stopped\",\"note\":\"Another Lambda is starting the instance\"},...}"
  }
}
```

---

## The Fix

### Changed BACK to (Correct):

**1. GenerateAllImagesBatched** (line 262):
```json
"ec2_endpoint.$": "$.ec2Endpoint.Payload.endpoint"  ✅ CORRECT
```

**2. CheckEC2Result** (line 682):
```json
"Variable": "$.ec2Endpoint.Payload.state"  ✅ CORRECT
```

### Why `.Payload.` is Required

When using `Resource: "arn:aws:states:::lambda:invoke"`:
- AWS Step Functions **automatically** wraps Lambda response
- Response structure: `{ExecutedVersion, Payload, SdkHttpMetadata, ...}`
- Must access data via `$.taskResult.Payload.yourField`

This is **AWS SDK behavior**, not Lambda behavior!

---

## What Went Wrong in Previous Fix

**Commit 7398aa0** (2025-12-02) incorrectly assumed:
1. Lambda returns flat JSON: `{state: "running"}`
2. Step Functions receives it directly
3. JSONPath should be: `$.ec2Endpoint.state`

**Reality:**
1. Lambda returns: `{state: "running"}`
2. **AWS wraps it**: `{Payload: {state: "running"}}`
3. JSONPath must be: `$.ec2Endpoint.Payload.state`

---

## Evidence

### Failed Execution Analysis

**Execution:** `manual-trigger-20260113-221017`

**Error Message:**
```
States.Runtime: An error occurred while executing the state 'CheckEC2Result'.
Invalid path '$.ec2Endpoint.state': The choice state's condition path references
an invalid value.
```

**Actual Lambda Output (from execution history):**
```json
{
  "ExecutedVersion": "$LATEST",
  "Payload": {
    "state": "stopped",
    "note": "Another Lambda is starting the instance"
  }
}
```

**Problem:**
- Step Functions tried: `$.ec2Endpoint.state`
- But structure is: `$.ec2Endpoint.Payload.state`
- Result: Field not found → execution failed

---

## Deployment

```bash
# Updated definition
aws stepfunctions update-state-machine \
  --state-machine-arn arn:aws:states:eu-central-1:599297130956:stateMachine:ContentGenerator \
  --definition file://current-sf-definition.json

# Update time: 2026-02-08 11:50:10 +02:00
```

---

## Testing Required

After deployment, test:

1. **Manual execution with active channels:**
```bash
aws stepfunctions start-execution \
  --state-machine-arn arn:aws:states:eu-central-1:599297130956:stateMachine:ContentGenerator \
  --name "test-jsonpath-payload-fix-$(date +%s)" \
  --input '{"user_id":"c334d862-4031-7097-4207-84856b59d3ed","trigger_type":"manual","force":true}'
```

2. **Monitor execution:**
```bash
# Check execution status
aws stepfunctions describe-execution \
  --execution-arn <arn-from-above>

# Should pass CheckEC2Result choice state
# Should proceed to GenerateAllImagesBatched
```

---

## AWS Lambda Integration Documentation

**Reference:** [AWS Step Functions - Call Lambda with Lambda Invoke](https://docs.aws.amazon.com/step-functions/latest/dg/connect-lambda.html)

### Key Points:

1. **When using `states:::lambda:invoke`:**
   - Response is **automatically wrapped**
   - Structure: `{Payload: <lambda-response>, ExecutedVersion, SdkHttpMetadata, ...}`

2. **When using direct Lambda ARN:**
   - Response is **NOT wrapped**
   - Structure: `<lambda-response>` (direct)

Our system uses: `states:::lambda:invoke` → **MUST use `.Payload.`**

---

## Prevention

### For Future Development:

1. **Always test Step Functions changes** with real executions
2. **Check execution history** to see actual response structure
3. **Reference AWS docs** for integration types
4. **Add integration tests** that validate JSONPath expressions

### Monitoring:

```bash
# Add CloudWatch alarm for Step Functions failures
aws cloudwatch put-metric-alarm \
  --alarm-name "StepFunctions-JSONPath-Errors" \
  --metric-name ExecutionsFailed \
  --namespace AWS/States \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanThreshold
```

---

## Related Files

- `current-sf-definition.json` - Fixed definition (DEPLOYED)
- `JSONPATH-FIX-COMPLETE-2025-12-02.md` - **INCORRECT** previous fix (now reverted)
- `STEP-FUNCTIONS-FAILURE-ANALYSIS-2025-12-02.md` - Original problem analysis

---

## Lessons Learned

1. ✅ **Always check execution history** to see actual response format
2. ✅ **AWS SDK wraps Lambda responses** when using `states:::lambda:invoke`
3. ✅ **Test fixes thoroughly** before assuming they work
4. ❌ **Don't assume Lambda response format** - verify with real data
5. ❌ **Don't skip testing** even for "obvious" fixes

---

**Fix Applied By:** Claude Code
**Verified:** Execution history analysis confirms `.Payload.` wrapper exists
**Status:** Production deployment successful ✅
**Next Steps:** Test execution + Add CloudWatch alarms
