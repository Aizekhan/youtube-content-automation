# Week 4 Plan - Monitoring, Testing & Automation

**Date:** 2025-12-01
**Status:** 📋 PLANNING
**Dependencies:** Week 1, 2, 3 completed ✅

---

## Overview

Week 4 focuses on **operational excellence** - monitoring, testing, automation, and cost optimization. These improvements ensure long-term system health and easier maintenance.

---

## Priority Assessment

After completing Weeks 1-3, the system now has:
- ✅ Security fixes (Weeks 1 & 2)
- ✅ Code quality improvements (Week 3)
- ❌ **Limited monitoring** - no dashboards, alerts
- ❌ **No automated testing** - manual testing only
- ❌ **No CI/CD pipeline** - manual deployments
- ❌ **Unknown cost patterns** - no cost analysis

---

## Week 4 Tasks

### Issue #21: CloudWatch Dashboards 🔴 HIGH
**Priority:** Observability & monitoring
**ETA:** 2-3 hours

**Problem:**
- No centralized view of system health
- Can't see Lambda errors, duration, costs in one place
- Manual log searching is slow
- No historical performance tracking

**Solution:**
Create CloudWatch Dashboard with key metrics:

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/Lambda", "Invocations", {"stat": "Sum"}],
          [".", "Errors", {"stat": "Sum"}],
          [".", "Duration", {"stat": "Average"}],
          [".", "Throttles", {"stat": "Sum"}]
        ],
        "period": 300,
        "stat": "Average",
        "region": "eu-central-1",
        "title": "Lambda Health"
      }
    },
    {
      "type": "log",
      "properties": {
        "query": "fields @timestamp, level, message, error | filter level = 'ERROR' | sort @timestamp desc | limit 20",
        "region": "eu-central-1",
        "title": "Recent Errors"
      }
    }
  ]
}
```

**Widgets to create:**
1. **Lambda Health** - Invocations, Errors, Duration, Throttles
2. **Step Functions** - Executions, Failed, Succeeded, Duration
3. **DynamoDB** - Read/Write capacity, Throttles, Latency
4. **EC2 Instances** - State, CPU, Network
5. **Cost Tracking** - Daily spend by service
6. **Security Events** - IDOR blocks, validation failures
7. **Recent Errors** - Last 20 errors across all Lambdas
8. **Content Generation Stats** - Content created per day

**Impact:**
- 📊 Real-time system health visibility
- 🚨 Quick error detection
- 📈 Performance tracking over time

---

### Issue #22: CloudWatch Alarms 🔴 HIGH
**Priority:** Proactive issue detection
**ETA:** 1-2 hours

**Problem:**
- No alerts when things break
- Find out about issues too late (user reports)
- Can't respond quickly to problems

**Solution:**
Create CloudWatch Alarms for critical metrics:

```python
# Create alarm for Lambda errors
cloudwatch.put_metric_alarm(
    AlarmName='content-narrative-high-errors',
    ComparisonOperator='GreaterThanThreshold',
    EvaluationPeriods=2,
    MetricName='Errors',
    Namespace='AWS/Lambda',
    Period=300,
    Statistic='Sum',
    Threshold=5.0,  # Alert if >5 errors in 5 minutes
    ActionsEnabled=True,
    AlarmActions=['arn:aws:sns:eu-central-1:...:alerts'],
    Dimensions=[
        {'Name': 'FunctionName', 'Value': 'content-narrative'}
    ]
)
```

**Alarms to create:**
1. **Lambda Errors** - >5 errors in 5 minutes
2. **Lambda Duration** - >80% of timeout
3. **Step Functions Failures** - >2 failed executions in 1 hour
4. **DynamoDB Throttles** - Any throttling events
5. **EC2 Instance Down** - Instance not running when expected
6. **High Costs** - Daily spend >$50 (configurable)

**Notification:**
- Create SNS topic for alerts
- Subscribe email/Telegram to SNS topic

**Impact:**
- 🚨 Immediate notification of issues
- ⏱️ Faster response time
- 📉 Reduced downtime

---

### Issue #23: Automated Testing 🟡 MEDIUM
**Priority:** Code reliability
**ETA:** 4-5 hours

**Problem:**
- All testing is manual
- Easy to miss bugs before deployment
- No confidence in deployments
- Regression risks

**Solution:**
Create pytest test suite for Lambda functions:

```python
# tests/test_validation_utils.py
import pytest
from validation_utils import validate_user_id, validate_channel_access

def test_validate_user_id_valid():
    event = {'user_id': 'user-12345678'}
    result = validate_user_id(event)
    assert result == 'user-12345678'

def test_validate_user_id_missing():
    event = {}
    with pytest.raises(ValueError, match='user_id is required'):
        validate_user_id(event)

def test_validate_user_id_too_short():
    event = {'user_id': 'abc'}
    with pytest.raises(ValueError, match='too short'):
        validate_user_id(event)

def test_validate_channel_access_success():
    channel_config = {'user_id': 'user-123'}
    result = validate_channel_access(channel_config, 'user-123')
    assert result == True

def test_validate_channel_access_idor():
    channel_config = {'user_id': 'user-123'}
    with pytest.raises(ValueError, match='Access denied'):
        validate_channel_access(channel_config, 'user-456')
```

**Test categories:**
1. **Unit tests** - Test individual functions
2. **Integration tests** - Test Lambda handlers
3. **Security tests** - Test IDOR prevention, validation
4. **Performance tests** - Test query optimization

**Test coverage targets:**
- Shared utilities: 90%+
- Critical Lambdas: 70%+
- Overall: 60%+

**Impact:**
- 🐛 Catch bugs before deployment
- 🔒 Ensure security fixes work
- 📈 Higher confidence in changes

---

### Issue #24: Cost Analysis & Optimization 🟡 MEDIUM
**Priority:** Cost management
**ETA:** 3-4 hours

**Problem:**
- Don't know actual system costs
- No cost breakdown by service/feature
- Can't identify cost optimization opportunities
- CostTracking table not analyzed

**Solution:**

**1. Create cost analysis script:**
```python
# scripts/analyze_costs.py
import boto3
from datetime import datetime, timedelta
from collections import defaultdict

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
cost_table = dynamodb.Table('CostTracking')

def analyze_costs(days=30):
    """Analyze costs for last N days"""
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    # Query costs by service
    response = cost_table.scan()
    items = response['Items']

    # Aggregate by service
    by_service = defaultdict(float)
    by_user = defaultdict(float)
    by_date = defaultdict(float)

    for item in items:
        if item['date'] >= start_date:
            by_service[item['service']] += float(item['cost_usd'])
            by_user[item.get('user_id', 'unknown')] += float(item['cost_usd'])
            by_date[item['date']] += float(item['cost_usd'])

    return {
        'by_service': dict(by_service),
        'by_user': dict(by_user),
        'by_date': dict(by_date),
        'total': sum(by_service.values())
    }
```

**2. Cost optimization opportunities:**
- **Lambda memory optimization** - Right-size memory for each function
- **DynamoDB on-demand vs provisioned** - Analyze which is cheaper
- **S3 lifecycle policies** - Move old data to Glacier
- **EC2 reserved instances** - If usage is predictable
- **CloudWatch log retention** - Reduce retention for low-value logs

**3. Create cost dashboard widget:**
```python
# Show daily costs over time
{
  "type": "metric",
  "properties": {
    "metrics": [
      ["AWS/Billing", "EstimatedCharges", {"stat": "Maximum"}]
    ],
    "period": 86400,
    "stat": "Maximum",
    "region": "us-east-1",
    "title": "Daily AWS Costs"
  }
}
```

**Impact:**
- 💰 Identify cost savings (target: 20-30%)
- 📊 Cost transparency
- 🎯 Budget tracking

---

### Issue #25: CI/CD Pipeline 🟢 LOW
**Priority:** Deployment automation
**ETA:** 4-6 hours

**Problem:**
- Manual deployments are slow
- Easy to forget steps (zip, upload, update config)
- No automatic testing before deploy
- No deployment history

**Solution:**
Create GitHub Actions workflow:

```yaml
# .github/workflows/deploy-lambda.yml
name: Deploy Lambda Functions

on:
  push:
    branches: [main]
    paths:
      - 'aws/lambda/**'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install pytest boto3
      - run: pytest tests/

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: eu-central-1

      - name: Deploy Lambda functions
        run: |
          for dir in aws/lambda/*/; do
            cd $dir
            if [ -f lambda_function.py ]; then
              zip function.zip lambda_function.py
              aws lambda update-function-code \
                --function-name $(basename $dir) \
                --zip-file fileb://function.zip
            fi
            cd -
          done
```

**Pipeline features:**
1. **Automatic testing** - Run pytest on every commit
2. **Automated deployment** - Deploy to Lambda on push to main
3. **Deployment gates** - Only deploy if tests pass
4. **Rollback capability** - Keep previous versions
5. **Slack/Email notifications** - Notify on deploy success/failure

**Impact:**
- ⚡ Faster deployments (5 min vs 30 min)
- 🔒 Safer deployments (tests first)
- 📝 Deployment history
- 🤖 Less manual work

---

### Issue #26: Performance Monitoring 🟢 LOW
**Priority:** Long-term optimization
**ETA:** 2-3 hours

**Problem:**
- Don't know if Week 3 optimizations actually helped
- Can't track performance over time
- No baseline metrics

**Solution:**

**1. Create performance metrics script:**
```python
# scripts/performance_metrics.py
import boto3
from datetime import datetime, timedelta

cloudwatch = boto3.client('cloudwatch', region_name='eu-central-1')

def get_lambda_metrics(function_name, days=7):
    """Get Lambda performance metrics"""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=days)

    # Get average duration
    duration = cloudwatch.get_metric_statistics(
        Namespace='AWS/Lambda',
        MetricName='Duration',
        Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
        StartTime=start_time,
        EndTime=end_time,
        Period=3600,
        Statistics=['Average', 'Maximum']
    )

    # Get error rate
    errors = cloudwatch.get_metric_statistics(
        Namespace='AWS/Lambda',
        MetricName='Errors',
        Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
        StartTime=start_time,
        EndTime=end_time,
        Period=3600,
        Statistics=['Sum']
    )

    return {
        'duration': duration,
        'errors': errors
    }
```

**2. Track key metrics:**
- **Lambda duration** - Average, P99, Max
- **DynamoDB read latency** - Before/after query optimization
- **Step Functions execution time** - Overall workflow duration
- **Error rates** - Errors per 1000 invocations
- **Cost per execution** - Track cost trends

**3. Generate performance reports:**
```bash
# Weekly performance report
python scripts/performance_report.py --period 7days
# Output:
# content-narrative:
#   Avg duration: 2.3s (was 2.8s, -18%)
#   Errors: 2 (0.1% error rate)
#   Cost: $1.23 (down from $1.45, -15%)
```

**Impact:**
- 📈 Prove optimization value
- 🎯 Identify further improvements
- 📊 Trend analysis

---

## Implementation Order

### Phase 1: Monitoring (4-5 hours) - HIGHEST ROI
1. ✅ Issue #22: CloudWatch Alarms (critical alerts)
2. ✅ Issue #21: CloudWatch Dashboards (visibility)

### Phase 2: Cost Optimization (3-4 hours)
3. ✅ Issue #24: Cost Analysis & Optimization

### Phase 3: Testing (4-5 hours)
4. ✅ Issue #23: Automated Testing

### Phase 4: Automation (6-9 hours) - OPTIONAL
5. ⏳ Issue #25: CI/CD Pipeline
6. ⏳ Issue #26: Performance Monitoring

---

## Expected Outcomes

### Monitoring
- ✅ Real-time system health visibility
- ✅ Proactive issue detection (alerts)
- ✅ Historical performance tracking

### Cost Optimization
- ✅ 20-30% cost reduction
- ✅ Cost transparency by service/user
- ✅ Budget tracking and forecasting

### Testing
- ✅ 60%+ test coverage
- ✅ Automated testing on every deploy
- ✅ Higher confidence in changes

### Automation
- ✅ 80% faster deployments
- ✅ Reduced manual work
- ✅ Deployment history and rollback

---

## Success Criteria

Week 4 is complete when:
- ✅ CloudWatch Dashboard created with 8+ widgets
- ✅ CloudWatch Alarms configured for critical metrics
- ✅ Cost analysis script created and run
- ✅ Test suite created with 60%+ coverage
- ✅ CI/CD pipeline working (optional)
- ✅ Performance baseline established

---

## Time Estimate

**Minimum (Monitoring + Cost):** 7-9 hours (1-2 days)
**Recommended (+ Testing):** 11-14 hours (2-3 days)
**Full (+ Automation):** 17-23 hours (3-4 days)

**By Phase:**
- Phase 1 (Monitoring): 4-5 hours ⭐ HIGH ROI
- Phase 2 (Cost): 3-4 hours ⭐ HIGH ROI
- Phase 3 (Testing): 4-5 hours
- Phase 4 (Automation): 6-9 hours

---

**Recommendation:** Start with **Phase 1 (Monitoring)** - highest ROI, immediate value!

**Status:** 📋 Ready to start
**Dependencies:** Week 1-3 completed ✅
**Next:** Choose where to start! Recommend Issue #22 (Alarms) for immediate value.
