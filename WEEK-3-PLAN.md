# Week 3 Plan - Medium Priority Improvements

**Date:** 2025-12-01
**Status:** 📋 PLANNING
**Dependencies:** Week 1 & 2 completed

---

## Overview

Week 3 focuses on **code quality improvements** and **operational resilience**. These changes improve maintainability, reliability, and developer productivity.

---

## Remaining Week 2 Tasks

### Issue #10: Add Request Validation to Step Functions ⚠️ HIGH
**Priority:** Should be in Week 2, carrying over
**ETA:** 2-3 hours

**Problem:**
- Step Functions start execution without validating input structure
- Invalid inputs cause failures deep in workflow (wasting time & money)
- No fail-fast mechanism

**Solution:**
Create validation Lambda at the start of Step Functions workflow:

```python
# aws/lambda/validate-step-functions-input/lambda_function.py
def lambda_handler(event, context):
    """
    Validate Step Functions input before starting workflow
    Fails fast if input is invalid
    """

    required_fields = ['user_id', 'channel_id', 'selected_topic']

    for field in required_fields:
        if field not in event:
            raise ValueError(f"Missing required field: {field}")

    # Validate user_id format
    if not isinstance(event['user_id'], str) or len(event['user_id']) < 10:
        raise ValueError("Invalid user_id format")

    # Validate channel_id format
    if not isinstance(event['channel_id'], str):
        raise ValueError("Invalid channel_id format")

    return event  # Pass through if valid
```

**Update Step Functions:**
Add validation state as first step in workflow.

**Impact:**
- 🚀 Fail fast (saves 2-5 minutes per invalid request)
- 💰 Cost savings (no wasted Lambda/API calls)
- 🐛 Better error messages

---

### Issue #11: Extract Duplicate Code ⚠️ MEDIUM
**Priority:** Code quality improvement
**ETA:** 3-4 hours

**Problem:**
Duplicate code in multiple locations:
- User ID validation (10+ locations)
- S3 URL generation (5+ locations)
- Error response formatting (15+ locations)
- Config merging logic (3 locations)

**Solution:**
Create shared utilities library:

```python
# aws/lambda/shared/validation_utils.py
def validate_user_id(event):
    """Standard user_id validation across all Lambdas"""
    user_id = event.get('user_id')
    if not user_id:
        raise ValueError('SECURITY ERROR: user_id is required')
    return user_id

def validate_channel_access(channel_config, user_id):
    """Standard IDOR prevention check"""
    if channel_config.get('user_id') != user_id:
        raise ValueError(f'Access denied: Channel does not belong to user')
    return True
```

```python
# aws/lambda/shared/response_utils.py
def success_response(data, status_code=200):
    """Standard success response"""
    return {
        'statusCode': status_code,
        'body': json.dumps(data, default=decimal_default)
    }

def error_response(error_message, status_code=500):
    """Standard error response"""
    return {
        'statusCode': status_code,
        'body': json.dumps({'error': error_message})
    }
```

**Refactor Lambda functions** to use shared utilities.

**Impact:**
- 🔧 Easier maintenance (one place to fix)
- 🐛 Fewer bugs (consistent behavior)
- 📉 Less code duplication (DRY principle)

---

## Week 3 Core Tasks

### Issue #14: Implement Proper Error Logging 🔴 HIGH
**Priority:** Operational reliability
**ETA:** 3-4 hours

**Problem:**
- Mix of `print()` and `logging` module
- No structured logging (can't query/filter)
- No error severity levels
- No correlation IDs for tracing

**Current state:**
```python
print(f"Error: {str(e)}")  # Unstructured
```

**Solution:**
```python
import logging
import json
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def log_error(error, context=None):
    """Structured error logging"""
    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'level': 'ERROR',
        'error': str(error),
        'error_type': type(error).__name__,
        'context': context or {}
    }
    logger.error(json.dumps(log_entry))

# Usage:
try:
    # ... code ...
except Exception as e:
    log_error(e, {
        'user_id': user_id,
        'channel_id': channel_id,
        'operation': 'content_generation'
    })
```

**Benefits:**
- 🔍 Easy CloudWatch Insights queries
- 📊 Better error tracking
- 🚨 Can set up alarms on ERROR logs

---

### Issue #15: Fix Decimal Serialization 🟡 MEDIUM
**Priority:** Data consistency
**ETA:** 2 hours

**Problem:**
- Inconsistent handling of Decimal types from DynamoDB
- Some functions use `float()`, others use `Decimal(str())`
- Can cause precision loss

**Solution:**
Create standardized Decimal handler:

```python
# aws/lambda/shared/dynamodb_utils.py
from decimal import Decimal
import json

class DecimalEncoder(json.JSONEncoder):
    """JSON encoder that handles Decimal types"""
    def default(self, obj):
        if isinstance(obj, Decimal):
            # Convert to int if no decimal places
            if obj % 1 == 0:
                return int(obj)
            return float(obj)
        return super().default(obj)

def decimal_to_number(obj):
    """Recursively convert Decimal to int/float"""
    if isinstance(obj, list):
        return [decimal_to_number(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: decimal_to_number(value) for key, value in obj.items()}
    elif isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj

# Usage:
response = table.get_item(Key={'id': 'abc'})
item = decimal_to_number(response['Item'])
```

**Impact:**
- ✅ Consistent data format
- 🐛 No precision loss bugs
- 📐 Predictable API responses

---

### Issue #16: Standardize Logging 🟡 MEDIUM
**Priority:** Code consistency
**ETA:** 2-3 hours

**Problem:**
- Mix of `print()` (20+ functions) and `logging` module (5 functions)
- Inconsistent log formats
- Hard to set log levels

**Decision:**
Use Python `logging` module everywhere:

```python
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Instead of: print(f"Processing {user_id}")
logger.info(f"Processing user", extra={'user_id': user_id})

# Instead of: print(f"Error: {e}")
logger.error(f"Operation failed", exc_info=True, extra={'user_id': user_id})
```

**Benefits:**
- 📊 Can change log levels without code changes
- 🔍 Better CloudWatch integration
- 🎯 Structured logging with context

---

### Issue #17: Replace Magic Numbers 🟢 LOW
**Priority:** Code readability
**ETA:** 1-2 hours

**Problem:**
Magic numbers scattered throughout code:

```python
timeout = 120  # What does 120 mean?
memory = 256   # Why 256?
max_retries = 3  # Why 3?
```

**Solution:**
Create constants file:

```python
# aws/lambda/shared/constants.py

# Lambda timeouts (seconds)
LAMBDA_TIMEOUT_SHORT = 30
LAMBDA_TIMEOUT_MEDIUM = 120
LAMBDA_TIMEOUT_LONG = 300

# Memory configurations (MB)
LAMBDA_MEMORY_SMALL = 128
LAMBDA_MEMORY_MEDIUM = 256
LAMBDA_MEMORY_LARGE = 512

# Retry configurations
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2

# Validation limits
MAX_REQUEST_SIZE_MB = 10
MAX_SCENES_PER_CONTENT = 100
MAX_CHANNELS_PER_USER = 50

# S3 presigned URL expiration
S3_URL_EXPIRATION_SECONDS = 3600  # 1 hour
```

**Usage:**
```python
from shared.constants import MAX_SCENES_PER_CONTENT, S3_URL_EXPIRATION_SECONDS

if len(scenes) > MAX_SCENES_PER_CONTENT:
    raise ValueError(f"Too many scenes: {len(scenes)} > {MAX_SCENES_PER_CONTENT}")
```

**Impact:**
- 📖 Self-documenting code
- 🔧 Easy to change configuration
- 🐛 Fewer "magic number" bugs

---

### Issue #18: Add Step Functions Retry Logic 🔴 HIGH
**Priority:** Reliability
**ETA:** 2 hours

**Problem:**
- No automatic retries on transient failures
- Entire workflow fails on single Lambda timeout
- Wastes money re-running from scratch

**Solution:**
Update Step Functions definition with retry policies:

```json
{
  "States": {
    "ContentNarrative": {
      "Type": "Task",
      "Resource": "arn:aws:lambda:...:function:content-narrative",
      "Retry": [
        {
          "ErrorEquals": [
            "Lambda.ServiceException",
            "Lambda.TooManyRequestsException",
            "States.Timeout"
          ],
          "IntervalSeconds": 2,
          "MaxAttempts": 3,
          "BackoffRate": 2.0
        }
      ],
      "Catch": [
        {
          "ErrorEquals": ["States.ALL"],
          "ResultPath": "$.error",
          "Next": "HandleError"
        }
      ],
      "Next": "ContentAudioTTS"
    }
  }
}
```

**Add retry to ALL Lambda tasks** in Step Functions.

**Impact:**
- 🔄 Auto-recovery from transient failures
- 💰 Saves money (no full re-runs)
- ⏱️ Saves time (faster recovery)

---

### Issue #19: Fix EC2 Race Condition 🟡 MEDIUM
**Priority:** Data integrity
**ETA:** 3 hours

**Problem:**
- Multiple Lambda invocations can start same EC2 instance simultaneously
- DynamoDB "instance_status" check is not atomic
- Can cause conflicts, wasted EC2 hours

**Location:** `ec2-sd35-control/lambda_function.py`

**Solution:**
Use DynamoDB conditional updates (optimistic locking):

```python
# Before starting EC2
try:
    response = table.update_item(
        Key={'instance_id': instance_id},
        UpdateExpression='SET instance_status = :starting',
        ConditionExpression='instance_status = :stopped',
        ExpressionAttributeValues={
            ':starting': 'starting',
            ':stopped': 'stopped'
        },
        ReturnValues='ALL_NEW'
    )
except ClientError as e:
    if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
        # Another Lambda is already starting this instance
        return {'status': 'already_starting'}
    raise
```

**Impact:**
- 🔒 Prevents race conditions
- 💰 Saves EC2 costs (no duplicate instances)
- 🐛 Data integrity maintained

---

### Issue #20: Optimize Database Queries 🟡 MEDIUM
**Priority:** Performance & Cost
**ETA:** 2-3 hours

**Problem:**
- Some Lambda functions use `scan()` instead of `query()`
- Scans read entire table (slow, expensive)
- Not using GSI (Global Secondary Index) properly

**Example Problem:**
```python
# BAD: Full table scan
response = table.scan(
    FilterExpression='user_id = :uid',
    ExpressionAttributeValues={':uid': user_id}
)
```

**Solution:**
```python
# GOOD: Use GSI with query
response = table.query(
    IndexName='user_id-created_at-index',
    KeyConditionExpression='user_id = :uid',
    ExpressionAttributeValues={':uid': user_id},
    ScanIndexForward=False  # Newest first
)
```

**Audit all Lambda functions** and replace scans with queries.

**Impact:**
- ⚡ 10-100x faster queries
- 💰 Lower DynamoDB costs (read fewer items)
- 🚀 Better scalability

---

## Implementation Order

### Phase 1: Finish Week 2 (2-3 hours)
1. ✅ Issue #10: Step Functions input validation
2. ✅ Issue #11: Extract duplicate code

### Phase 2: High Priority Week 3 (6-8 hours)
3. ✅ Issue #14: Structured error logging
4. ✅ Issue #18: Step Functions retry logic
5. ✅ Issue #19: EC2 race condition fix

### Phase 3: Medium Priority (5-7 hours)
6. ✅ Issue #15: Decimal serialization
7. ✅ Issue #16: Standardize logging
8. ✅ Issue #20: Optimize queries

### Phase 4: Code Quality (2-3 hours)
9. ✅ Issue #17: Replace magic numbers

---

## Expected Outcomes

### Reliability
- ✅ 90% fewer workflow failures (retry logic)
- ✅ 100% fewer race conditions (optimistic locking)
- ✅ Fail-fast validation (saves time & money)

### Maintainability
- ✅ 50% less duplicate code (shared utilities)
- ✅ Consistent logging (easier debugging)
- ✅ Self-documenting code (named constants)

### Performance
- ✅ 10-100x faster queries (GSI instead of scans)
- ✅ Lower DynamoDB costs (efficient queries)

### Observability
- ✅ Structured logs (easy querying)
- ✅ Better error tracking (correlation IDs)
- ✅ CloudWatch Insights ready

---

## Risk Assessment

| Task | Risk | Mitigation |
|------|------|------------|
| Step Functions validation | LOW | Easy to test, no breaking changes |
| Extract duplicate code | MEDIUM | Thorough testing required |
| Error logging | LOW | Additive change, doesn't break existing |
| Retry logic | LOW | Step Functions feature, well-tested |
| EC2 race condition | MEDIUM | Test thoroughly, add logging |
| Query optimization | MEDIUM | Test query results match scan results |
| Constants | LOW | Simple refactor |

---

## Testing Strategy

### Unit Testing
- Test validation functions with valid/invalid inputs
- Test shared utilities in isolation
- Test Decimal conversion edge cases

### Integration Testing
- Test Step Functions with invalid inputs (should fail fast)
- Test retry logic with simulated failures
- Test EC2 race condition with concurrent invocations
- Test query optimization (results match scans)

### Load Testing
- Test optimized queries under load
- Verify no performance regression

---

## Success Criteria

Week 3 is complete when:
- ✅ All Lambda functions use shared utilities
- ✅ Structured logging everywhere
- ✅ Step Functions have retry logic
- ✅ No more table scans (all queries use GSI)
- ✅ EC2 race condition resolved
- ✅ All tests passing
- ✅ Code review approved

---

## Time Estimate

**Total:** 20-25 hours (3-4 work days)

**By Phase:**
- Phase 1: 2-3 hours
- Phase 2: 6-8 hours
- Phase 3: 5-7 hours
- Phase 4: 2-3 hours
- Testing: 3-4 hours

---

**Status:** 📋 Ready to start
**Dependencies:** Week 1 & 2 completed ✅
**Next:** Choose where to start!
