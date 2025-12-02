# GitHub Actions Workflows

This directory contains GitHub Actions workflows for CI/CD automation.

## 📁 Workflows

### 1. `deploy-production.yml`
**Purpose:** Automatic deployment to production

**Triggers:**
- Push to `master` branch
- Manual trigger

**What it does:**
- Detects which Lambda functions changed
- Runs tests
- Deploys changed Lambda functions to AWS
- Deploys frontend files (when configured)
- Sends Telegram notifications

**Duration:** ~5-10 minutes

---

### 2. `pr-review.yml`
**Purpose:** Code quality checks on pull requests

**Triggers:**
- Pull request to `master`

**What it does:**
- Code quality checks (flake8, black)
- Security vulnerability scan (bandit)
- Unit tests
- Lambda structure validation
- Secrets detection
- Posts summary comment to PR

**Duration:** ~3-5 minutes

---

## 🔐 Required Secrets

Configure these in: https://github.com/Aizekhan/youtube-content-automation/settings/secrets/actions

| Secret Name | Required | Description |
|-------------|----------|-------------|
| `AWS_ACCESS_KEY_ID` | ✅ Yes | AWS access key for deployment |
| `AWS_SECRET_ACCESS_KEY` | ✅ Yes | AWS secret key for deployment |
| `TELEGRAM_BOT_TOKEN` | ❌ Optional | Telegram bot token for notifications |
| `TELEGRAM_CHAT_ID` | ❌ Optional | Telegram chat ID for notifications |

---

## 🚀 Quick Start

1. **Setup AWS credentials** (see `GITHUB-ACTIONS-SETUP.md`)
2. **Add GitHub Secrets**
3. **Push to master** - deployment runs automatically!

---

## 📊 Monitoring

View workflow runs:
https://github.com/Aizekhan/youtube-content-automation/actions

---

## 📚 Documentation

See `GITHUB-ACTIONS-SETUP.md` for complete setup guide.
