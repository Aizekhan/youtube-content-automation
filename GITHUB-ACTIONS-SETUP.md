# GitHub Actions CI/CD Setup Guide

This guide walks you through setting up GitHub Actions for automatic deployment of Lambda functions and infrastructure.

---

## 📋 Prerequisites

1. ✅ Git repository synced with production (completed)
2. ✅ AWS account with Lambda functions deployed
3. ⏳ GitHub repository access with admin permissions
4. ⏳ AWS IAM user with deployment permissions

---

## 🔐 Step 1: Create AWS IAM User for GitHub Actions

### 1.1 Create IAM User

```bash
aws iam create-user --user-name github-actions-deploy
```

### 1.2 Create IAM Policy for Deployment

Create a file `github-actions-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "LambdaDeployment",
      "Effect": "Allow",
      "Action": [
        "lambda:UpdateFunctionCode",
        "lambda:GetFunction",
        "lambda:UpdateFunctionConfiguration",
        "lambda:PublishVersion"
      ],
      "Resource": "arn:aws:lambda:eu-central-1:599297130956:function:*"
    },
    {
      "Sid": "S3Access",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::youtube-automation-*/*",
        "arn:aws:s3:::youtube-automation-*"
      ]
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:eu-central-1:599297130956:*"
    }
  ]
}
```

### 1.3 Attach Policy to User

```bash
# Create the policy
aws iam create-policy \
  --policy-name GitHubActionsDeployPolicy \
  --policy-document file://github-actions-policy.json

# Attach to user
aws iam attach-user-policy \
  --user-name github-actions-deploy \
  --policy-arn arn:aws:iam::599297130956:policy/GitHubActionsDeployPolicy
```

### 1.4 Create Access Keys

```bash
aws iam create-access-key --user-name github-actions-deploy
```

**IMPORTANT:** Save the output! You'll need:
- `AccessKeyId`
- `SecretAccessKey`

---

## 🔑 Step 2: Configure GitHub Secrets

### 2.1 Navigate to GitHub Secrets

1. Go to: https://github.com/Aizekhan/youtube-content-automation/settings/secrets/actions
2. Click **"New repository secret"**

### 2.2 Add Required Secrets

Add the following secrets one by one:

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `AWS_ACCESS_KEY_ID` | AWS Access Key from Step 1.4 | `AKIAIOSFODNN7EXAMPLE` |
| `AWS_SECRET_ACCESS_KEY` | AWS Secret Key from Step 1.4 | `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY` |
| `TELEGRAM_BOT_TOKEN` | (Optional) Telegram bot token for notifications | `123456789:ABCdefGHIjklMNOpqrsTUVwxyz` |
| `TELEGRAM_CHAT_ID` | (Optional) Telegram chat ID for notifications | `-1001234567890` |

### 2.3 Verify Secrets

After adding, you should see:
- ✅ AWS_ACCESS_KEY_ID
- ✅ AWS_SECRET_ACCESS_KEY
- ✅ TELEGRAM_BOT_TOKEN (optional)
- ✅ TELEGRAM_CHAT_ID (optional)

---

## 🚀 Step 3: Test GitHub Actions

### 3.1 Make a Test Change

Edit a Lambda function:

```bash
# Make a small change to trigger deployment
cd E:/youtube-content-automation
echo "# Test deployment $(date)" >> aws/lambda/content-narrative/README.md

# Commit and push
git add aws/lambda/content-narrative/README.md
git commit -m "Test: Trigger GitHub Actions deployment"
git push
```

### 3.2 Monitor Deployment

1. Go to: https://github.com/Aizekhan/youtube-content-automation/actions
2. Click on the latest "Deploy to Production" workflow
3. Watch the deployment progress

### 3.3 Verify Success

Check that:
- ✅ All jobs completed successfully
- ✅ Lambda function was updated
- ✅ Telegram notification received (if configured)

---

## 📊 Step 4: Understand the Workflows

### 4.1 Deploy to Production (`deploy-production.yml`)

**Triggers:**
- Push to `master` branch
- Manual trigger via GitHub Actions UI

**What it does:**
1. **Detects Changes** - Identifies which Lambda functions changed
2. **Runs Tests** - Executes Python tests (when available)
3. **Deploys Lambda Functions** - Updates changed functions only
4. **Deploys Frontend** - Syncs HTML/CSS/JS files (configured later)
5. **Sends Notifications** - Telegram alert on completion

**Key Features:**
- ✅ Smart deployment (only changed functions)
- ✅ Parallel deployment for speed
- ✅ Automatic rollback on failure
- ✅ Telegram notifications

### 4.2 PR Review (`pr-review.yml`)

**Triggers:**
- Pull request to `master` branch

**What it does:**
1. **Code Quality Checks** - Linting with flake8, black
2. **Security Scan** - Bandit vulnerability scan
3. **Unit Tests** - Runs pytest (when tests exist)
4. **Lambda Validation** - Checks function structure
5. **Secrets Check** - Scans for exposed credentials
6. **PR Comment** - Posts summary to PR

**Benefits:**
- ✅ Catch bugs before merge
- ✅ Enforce code quality standards
- ✅ Security vulnerability detection
- ✅ Automated code review

---

## 🛠️ Step 5: Customize Workflows (Optional)

### 5.1 Add More Lambda Functions

Edit `.github/workflows/deploy-production.yml`:

```yaml
strategy:
  matrix:
    function:
      # ... existing functions ...
      - your-new-lambda-function  # Add here
```

### 5.2 Configure Frontend Deployment

Update the `deploy-frontend` job with your server details:

```yaml
- name: Deploy to production server
  run: |
    # Option 1: SSH deployment
    ssh user@your-server.com "cd /var/www && git pull"

    # Option 2: S3 + CloudFront
    aws s3 sync . s3://your-bucket/ --exclude "*.git*"
    aws cloudfront create-invalidation --distribution-id YOUR_ID --paths "/*"
```

### 5.3 Add Telegram Notifications

Create a Telegram bot:

```bash
# 1. Message @BotFather on Telegram
# 2. Send /newbot
# 3. Follow instructions to get bot token
# 4. Add bot to your channel/group
# 5. Get chat ID from https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
```

Add to GitHub Secrets:
- `TELEGRAM_BOT_TOKEN`: Your bot token
- `TELEGRAM_CHAT_ID`: Your chat/channel ID

---

## 🔄 Step 6: Workflow for Future Changes

### Daily Development Flow:

```bash
# 1. Make changes to Lambda function
nano aws/lambda/content-narrative/lambda_function.py

# 2. Test locally (optional)
python aws/lambda/content-narrative/lambda_function.py

# 3. Commit changes
git add aws/lambda/content-narrative/lambda_function.py
git commit -m "feat: Update narrative generation logic"

# 4. Push to GitHub
git push

# 5. GitHub Actions automatically:
#    - Runs tests
#    - Deploys to AWS Lambda
#    - Sends notification
```

**Deployment time:** ~5-10 minutes (depends on number of changed functions)

---

## 🧪 Step 7: Add Tests (Recommended)

### 7.1 Create Test File

Create `aws/lambda/content-narrative/test_lambda_function.py`:

```python
import pytest
from lambda_function import lambda_handler

def test_lambda_handler():
    """Test Lambda handler with mock event"""
    event = {
        "channel_id": "test-channel",
        "topic": "Test Topic"
    }
    context = {}

    result = lambda_handler(event, context)

    assert result is not None
    assert "statusCode" in result
```

### 7.2 Run Tests Locally

```bash
# Install pytest
pip install pytest boto3 moto

# Run tests
pytest aws/lambda/*/test_*.py -v
```

### 7.3 Tests Run Automatically

GitHub Actions will now run tests on every push!

---

## 📈 Step 8: Monitor Deployments

### 8.1 GitHub Actions Dashboard

View all deployments:
https://github.com/Aizekhan/youtube-content-automation/actions

### 8.2 AWS Lambda Console

Check deployed functions:
```bash
aws lambda list-functions --region eu-central-1 | grep FunctionName
```

### 8.3 CloudWatch Logs

View deployment logs:
```bash
aws logs tail /aws/lambda/content-narrative --follow
```

---

## ⚠️ Troubleshooting

### Problem: Workflow fails with "Access Denied"

**Solution:** Check IAM permissions

```bash
# Verify user permissions
aws iam list-attached-user-policies --user-name github-actions-deploy

# Test AWS credentials
aws sts get-caller-identity
```

### Problem: Lambda deployment timeout

**Solution:** Increase timeout or deploy fewer functions in parallel

Edit `.github/workflows/deploy-production.yml`:

```yaml
strategy:
  max-parallel: 5  # Reduce from default
```

### Problem: No Telegram notifications

**Solution:** Verify bot token and chat ID

```bash
# Test Telegram notification
curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/sendMessage" \
  -d chat_id="<YOUR_CHAT_ID>" \
  -d text="Test message"
```

---

## 🎯 Next Steps

After GitHub Actions is working:

1. ✅ **Add Terraform workflow** (when Terraform is installed)
2. ✅ **Create staging environment** for testing before production
3. ✅ **Add integration tests** for end-to-end testing
4. ✅ **Setup monitoring** with CloudWatch alarms
5. ✅ **Add rollback automation** for failed deployments

---

## 📚 Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [AWS Lambda Deployment Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [Terraform GitHub Actions](https://developer.hashicorp.com/terraform/tutorials/automation/github-actions)

---

## ✅ Checklist

Before going live with GitHub Actions:

- [ ] AWS IAM user created with deployment permissions
- [ ] GitHub Secrets configured (AWS keys)
- [ ] Test deployment successful
- [ ] Telegram notifications working (optional)
- [ ] Team notified about new CI/CD process
- [ ] Documentation updated
- [ ] Rollback plan documented

---

**Status:** Ready to deploy! 🚀

Once you've added the GitHub Secrets, every push to `master` will automatically deploy your changes to production.
