# YouTube Automation - Quick Reference Guide
**Last Updated:** December 1, 2025

---

## 🚀 Quick Start

### Access Points
- **Dashboard:** https://n8n-creator.space/dashboard.html
- **Content:** https://n8n-creator.space/content.html
- **Channels:** https://n8n-creator.space/channels.html
- **Costs:** https://n8n-creator.space/costs.html
- **Full Docs:** https://n8n-creator.space/docs/PRODUCTION-SYSTEM-DOCUMENTATION.md

### Login
1. Go to https://n8n-creator.space
2. Click "Login with Google"
3. Redirect to Cognito
4. Callback with tokens

---

## 📊 System Status (Week 5)

### Production Ready Components
✅ **Content Generation:** 11 Lambdas
✅ **Dashboard/API:** 5 Lambdas
✅ **DynamoDB Tables:** 22 tables
✅ **S3 Buckets:** 5 buckets
✅ **CloudWatch Alarms:** 28 alarms
✅ **Step Functions:** 1 workflow

### Active Channels: 38
### Generated Content: 276 videos
### Cache Entries: 2 (gpt-4o-mini)

---

## 🔑 Key Lambdas

### Content Generation
| Function | Purpose | Timeout |
|----------|---------|---------|
| `content-theme-agent` | Select topic | 60s |
| `content-narrative` | **Generate story (GPT-4o-mini)** | 120s |
| `content-generate-images` | Create images (SD3.5) | 900s |
| `content-audio-tts` | Generate audio (Polly/ElevenLabs) | 300s |
| `content-video-assembly` | Assemble video (FFmpeg) | 900s |
| `content-save-result` | Save to DynamoDB | 30s |

### Critical Support
| Function | Purpose |
|----------|---------|
| `ec2-sd35-control` | Start/stop EC2 for images |
| `content-get-channels` | Get active channels |
| `telegram-error-notifier` | Send alerts |

---

## 💾 Key Tables

### Most Important
- **GeneratedContent** - All created videos (276 items, 2.2MB)
- **ChannelConfigs** - Channel settings (38 items)
- **CostTracking** - Per-generation costs (264 items)
- **OpenAIResponseCache** - Week 5 caching (0 items - new)

### Templates (10 tables)
- NarrativeTemplates
- ThemeTemplates
- TTSTemplates
- ImageGenerationTemplates
- SFXTemplates
- CTATemplates
- DescriptionTemplates
- ThumbnailTemplates
- VideoEditingTemplates
- PromptTemplatesV2

---

## 💰 Week 5 Cost Optimizations

### 1. GPT-4o-mini (94% savings)
```
Before: $2.50 per 1M tokens (GPT-4o)
After:  $0.150 per 1M tokens (GPT-4o-mini)
Savings: $2.35 per 1M tokens
```

### 2. OpenAI Cache (up to 100% on hits)
```
Table: OpenAIResponseCache
TTL: 7 days
Expected hit rate: 10-20%
```

### 3. Combined Savings
```
100 generations:
- Before: $5.50
- After: $3.25
- Savings: 40%
```

---

## 🔧 Common Commands

### Check Lambda Status
```bash
aws lambda get-function --function-name content-narrative --region eu-central-1
```

### Check Error Rates
```bash
python scripts/check_cache_stats.py
```

### Check Cache
```bash
aws dynamodb scan --table-name OpenAIResponseCache --select COUNT --region eu-central-1
```

### Deploy Lambda
```bash
cd aws/lambda/content-narrative
python create_zip.py
aws lambda update-function-code --function-name content-narrative --zip-file fileb://function.zip --region eu-central-1
```

### Check EC2
```bash
aws ec2 describe-instances --instance-ids i-0bce93f5d4f0a8c8e --region eu-central-1
```

### View Logs
```bash
aws logs tail /aws/lambda/content-narrative --since 1h --region eu-central-1
```

---

## 🚨 Monitoring

### SNS Alerts
- **Topic:** `cloudwatch-alarms-critical`
- **Email:** hrytsenkomaksym@gmail.com (PENDING)
- **Telegram:** Chat ID 784661667 (ACTIVE)

### Key Metrics
- Lambda errors: <1% target
- Cache hit rate: 10-20% expected
- Daily costs: <$50
- Video assembly: <1% error target

### Dashboard
All metrics visible at:
https://n8n-creator.space/documentation.html

---

## 🔐 Security

### Auth
- **Provider:** AWS Cognito
- **Pool:** youtube-automation-1764343453
- **Tokens:** LocalStorage (1h TTL)

### Multi-tenant
- All data filtered by `user_id`
- Row-level security in DynamoDB
- API validation in all Lambdas

---

## 🐛 Quick Troubleshooting

### Content Generation Fails
1. Check EC2: `aws ec2 describe-instances`
2. Check Lambda logs: `aws logs tail /aws/lambda/content-narrative`
3. Check Step Functions: Dashboard → Monitoring

### Login Issues
1. Clear browser cache
2. Check Cognito status
3. Verify callback URL

### High Costs
1. Check running EC2: `aws ec2 describe-instances --filters "Name=instance-state-name,Values=running"`
2. Verify gpt-4o-mini in use
3. Review CostTracking table

### Cache Not Working
1. Check IAM permissions
2. Verify cache table: `aws dynamodb scan --table-name OpenAIResponseCache`
3. Check Lambda logs for "cache" messages

---

## 📞 Support

**Email:** hrytsenkomaksym@gmail.com
**Telegram:** 784661667
**AWS Account:** 599297130956
**Region:** eu-central-1

---

## 📚 Full Documentation
See: `PRODUCTION-SYSTEM-DOCUMENTATION.md` for complete details

**Week 1:** Multi-tenancy & Auth
**Week 2:** Error handling
**Week 3:** Variation sets
**Week 4:** Image batching
**Week 5:** Cost optimization ← Current

---

*Generated: December 1, 2025*
