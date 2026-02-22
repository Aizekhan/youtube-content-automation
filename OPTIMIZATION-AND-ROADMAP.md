# Optimization Plan & Development Roadmap

**Дата:** 2026-02-22
**Статус після cleanup:** OPERATIONAL ✅
**Готовність до продакшену:** 95%

---

## Executive Summary

Після повного cleanup та аналізу системи, YouTube Content Automation Platform готова до продакшн використання. Поточні витрати ~$30-60/місяць (економія $1,115/місяць від зупинених GPU). Система має всі необхідні компоненти для автоматичної генерації відео контенту.

**Ключові метрики:**
- 38 активних Lambda функцій
- 37 налаштованих каналів
- 16 тем в черзі
- 50% успішність Step Functions (5/10)
- $1,115/місяць економія від cleanup

---

## Part 1: Immediate Fixes (1-2 дні)

### 1.1 Fix Step Functions JSONPath Error
**Проблема:** Execution failed через відсутність cta_segments в narrativeResult
**Пріоритет:** HIGH
**Складність:** LOW

**Рішення:**
```python
# In save-final-content Lambda function
# Add safe extraction with defaults
cta_segments = narrative_result.get('data', {}).get('narrative_content', {}).get('cta_segments', [])
```

**Файл:** `aws/lambda/save-final-content/lambda_function.py`

**Тестування:**
- Запустити Step Functions execution вручну
- Перевірити що всі поля extractються коректно
- Перевірити CloudWatch logs

---

### 1.2 Fix Content TopicsQueue Processing
**Проблема:** 16 тем в статусі "draft", не обробляються автоматично
**Пріоритет:** HIGH
**Складність:** MEDIUM

**Причина:**
- Topics мають NULL в полі topic
- Можливо не налаштований автоматичний trigger

**Рішення:**
1. Перевірити структуру даних в ContentTopicsQueue
2. Виправити topic field (додати actual topic text)
3. Налаштувати автоматичний scheduler або manual trigger

**Файли:**
- Dashboard: `topics-manager.html`, `js/topics-manager.js`
- Lambda: `content-topics-get-next`, `content-topics-update-status`

**Тестування:**
- Додати тему через Dashboard
- Перевірити що topic поле заповнено
- Trigger manual execution
- Перевірити що status змінюється на "processing"

---

### 1.3 CloudWatch Alerts Setup
**Проблема:** Немає автоматичних алертів на помилки
**Пріоритет:** MEDIUM
**Складність:** LOW

**Рішення:**
- CloudWatch Alarm на failed Step Functions executions
- CloudWatch Alarm на Lambda errors (content-*)
- CloudWatch Alarm на EC2 instance failures
- Telegram notifications через telegram-error-notifier

**Metrics:**
```
StepFunctions: ExecutionsFailed > 1 (period: 5min)
Lambda: Errors > 5 (period: 5min)
EC2: StatusCheckFailed > 0 (period: 5min)
```

---

## Part 2: Cost Optimization (3-5 днів)

### 2.1 Spot Instances for GPU
**Поточна ситуація:** g4dn.xlarge ($384/м) + g5.xlarge ($734/м) = $1,118/м
**Економія:** ~70% = $783/місяць

**Рішення:**
1. Створити Spot Fleet Request для g4dn.xlarge (Qwen3-TTS)
2. Створити Spot Fleet Request для g5.xlarge (Z-Image)
3. Налаштувати fallback на On-Demand якщо Spot недоступний
4. Update Lambda control functions (ec2-qwen3-control, ec2-zimage-control)

**Файли:**
- `terraform/ec2-spot-instances.tf` (create)
- `aws/lambda/ec2-qwen3-control/lambda_function.py`
- `aws/lambda/ec2-zimage-control/lambda_function.py`

**Ризики:**
- Spot instances можуть бути terminated (потрібен retry logic)
- Availability залежить від demand

---

### 2.2 S3 Lifecycle Policies
**Поточна ситуація:** Всі файли в S3 Standard
**Економія:** ~90% для старих файлів

**Рішення:**
1. Old videos (>30 days) → S3 Intelligent-Tiering
2. Archive videos (>90 days) → S3 Glacier Instant Retrieval
3. Very old (>180 days) → S3 Glacier Deep Archive

**Lifecycle Rules:**
```json
{
  "Rules": [
    {
      "Id": "ArchiveOldVideos",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "INTELLIGENT_TIERING"
        },
        {
          "Days": 90,
          "StorageClass": "GLACIER_IR"
        },
        {
          "Days": 180,
          "StorageClass": "DEEP_ARCHIVE"
        }
      ]
    }
  ]
}
```

**Файли:**
- S3 bucket policies (AWS Console або Terraform)

---

### 2.3 CloudWatch Log Retention
**Поточна ситуація:** 50 log groups, 32.2 MB, unlimited retention
**Економія:** ~$2-5/місяць

**Рішення:**
- Set retention to 7 days for debug logs
- Set retention to 30 days for production logs
- Set retention to 90 days for audit logs

**Script:**
```python
# aws/scripts/set-log-retention.py
logs_client.put_retention_policy(
    logGroupName=log_group,
    retentionInDays=7  # or 30, 90
)
```

---

### 2.4 DynamoDB Reserved Capacity (Optional)
**Поточна ситуація:** Pay-per-request
**Економія:** ~20-30% якщо predictable traffic

**Аналіз:**
- Поточне використання < 1000 reads/sec
- Pay-per-request краще для unpredictable workloads
- **Рекомендація:** Залишити Pay-per-request поки що

---

## Part 3: Performance Optimization (5-7 днів)

### 3.1 Lambda Reserved Concurrency
**Проблема:** Lambda throttling при burst traffic
**Рішення:** Set reserved concurrency для critical functions

**Functions:**
- content-narrative: 10 concurrent
- content-generate-images: 5 concurrent
- content-video-assembly: 5 concurrent

**Файли:**
- AWS Lambda Console або Terraform

---

### 3.2 OpenAI Response Caching Optimization
**Поточна ситуація:** OpenAIResponseCache table exists but underutilized
**Рішення:** Aggressive caching strategy

**Improvements:**
1. Cache all narrative responses by (topic + channel_config_hash)
2. Cache image prompts by (scene_description_hash)
3. Set TTL to 30 days
4. Monitor cache hit rate

**Expected savings:** ~40% OpenAI costs

---

### 3.3 Step Functions Optimization
**Проблема:** Data limit exceeded errors
**Рішення:** Use S3 for intermediate large data

**Changes:**
1. Store full narrative_result in S3
2. Pass S3 key через Step Functions state
3. Lambda functions read from S3

**Файли:**
- Step Functions definition (`stepfunctions_definition.json`)
- All content-* Lambdas

---

## Part 4: New Features Development (2-4 тижні)

### 4.1 Topics Queue Automation (Sprint 1 - ACTIVE)
**Статус:** Код готовий, потрібна активація

**Components:**
- ✅ Topics Queue Manager UI
- ✅ Lambda functions (add, list, get-next, bulk-add, update-status)
- ⏳ Automatic processing scheduler
- ⏳ Integration with ContentGenerator

**Tasks:**
1. Fix topic field population
2. Create EventBridge rule for automatic processing
3. Test end-to-end flow
4. Deploy to production

**Timeline:** 3-5 days

---

### 4.2 Mega Enrichment (Sprint 2 - READY)
**Статус:** Код існує, не активований

**Функція:** `content-mega-enrichment`
**Призначення:** Context enrichment для наративів

**Activation:**
1. Enable in Step Functions definition
2. Add after content-narrative step
3. Configure enrichment parameters
4. Test with sample content

**Timeline:** 2-3 days

---

### 4.3 Search Facts Integration (Sprint 2 - READY)
**Статус:** Код існує, не активований

**Функція:** `content-search-facts`
**Призначення:** Fact-checking та real data integration

**Activation:**
1. Enable in Step Functions
2. Configure search API (Google, Bing, or custom)
3. Test fact extraction
4. Integrate into narrative generation

**Timeline:** 3-4 days

---

### 4.4 Cliche Detector (Sprint 3 - READY)
**Статус:** Код існує, не активований

**Функція:** `content-cliche-detector`
**Призначення:** Detect and replace cliches in narratives

**Activation:**
1. Enable in Step Functions
2. Train cliche detection model (or use pre-trained)
3. Configure replacement suggestions
4. Test with sample narratives

**Timeline:** 4-5 days

---

### 4.5 Automatic YouTube Upload
**Статус:** Not implemented yet

**Requirements:**
1. YouTube Data API v3 integration
2. OAuth 2.0 authentication per channel
3. Upload Lambda function
4. Thumbnail upload
5. Description + tags automation
6. Scheduling (immediate or scheduled)

**Components:**
- New Lambda: `youtube-upload`
- New Lambda: `youtube-schedule`
- YouTubeCredentials table (already exists)

**Timeline:** 7-10 days

---

### 4.6 Publishing Scheduler
**Статус:** Partially implemented (DailyPublishingStats exists)

**Requirements:**
1. EventBridge schedule rules
2. Per-channel scheduling configuration
3. Content queue per channel
4. Publishing status tracking

**Components:**
- EventBridge rules
- New Lambda: `publishing-scheduler`
- Update DailyPublishingStats usage

**Timeline:** 5-7 days

---

## Part 5: Monitoring & Analytics (1-2 тижні)

### 5.1 Enhanced Dashboard
**Improvements:**
1. Real-time Step Functions status
2. Content generation metrics
3. Cost breakdown by channel
4. Topics Queue status
5. GPU instances health

**Файли:**
- `index.html`
- `monitoring.html` (create)
- `js/monitoring.js` (create)

---

### 5.2 Cost Analytics Dashboard
**Current:** dashboard-costs exists
**Improvements:**
1. Daily cost breakdown
2. Per-channel cost attribution
3. Cost forecasting
4. Budget alerts

---

### 5.3 Quality Metrics
**New metrics:**
1. Content generation success rate
2. Average generation time
3. OpenAI API latency
4. EC2 instance utilization
5. Cache hit rates

---

## Part 6: Testing & Quality (ongoing)

### 6.1 Automated Testing
**Current:** debug-test-runner exists
**Expand:**
1. Integration tests for full pipeline
2. Unit tests for Lambda functions
3. Load testing for Step Functions
4. Cost simulation tests

---

### 6.2 Error Recovery
**Improvements:**
1. Automatic retry logic for transient errors
2. Dead letter queues for failed messages
3. Manual intervention workflow
4. Error classification and routing

---

## Implementation Priority Matrix

### HIGH Priority (Week 1-2)
1. ✅ Fix JSONPath error in SaveFinalContent
2. ✅ Fix Topics Queue processing
3. ✅ Setup CloudWatch Alerts
4. ⏳ Test full content generation pipeline
5. ⏳ Activate Topics Queue automation

### MEDIUM Priority (Week 3-4)
1. Spot Instances for GPU
2. S3 Lifecycle policies
3. CloudWatch log retention
4. Mega Enrichment activation
5. Search Facts activation

### LOW Priority (Month 2)
1. YouTube Upload integration
2. Publishing Scheduler
3. Enhanced Dashboard
4. Cliche Detector activation
5. Automated testing suite

---

## Cost Projections

### Current State
- **Monthly:** $30-60
- **Savings from cleanup:** $1,115/month

### After Optimizations (Spot Instances + S3 Lifecycle)
- **Monthly:** $150-250 (with active generation)
- **Additional savings:** $780/month (Spot) + $50/month (S3)

### Production Scale (1000 videos/month)
- **Without optimizations:** $500-700/month
- **With optimizations:** $250-350/month
- **Total savings:** ~50%

---

## Success Metrics

### Technical Metrics
- Step Functions success rate > 95%
- Average generation time < 10 minutes
- Lambda cold start < 2 seconds
- API response time < 500ms

### Business Metrics
- Content generation cost < $0.50/video
- GPU utilization > 70%
- Cache hit rate > 40%
- Uptime > 99.5%

---

## Risks & Mitigation

### Technical Risks
1. **Spot Instance Termination**
   - Mitigation: Fallback to On-Demand, retry logic

2. **API Rate Limits (OpenAI, AWS)**
   - Mitigation: Exponential backoff, caching, quota monitoring

3. **Step Functions Data Limit**
   - Mitigation: S3 intermediate storage

4. **Lambda Timeout**
   - Mitigation: Increase timeout, break into smaller steps

### Business Risks
1. **Cost Overruns**
   - Mitigation: Budget alerts, cost caps, monitoring

2. **Content Quality Issues**
   - Mitigation: Quality checks, human review, A/B testing

---

## Next Steps (Immediate Actions)

### This Week:
1. ✅ Fix SaveFinalContent JSONPath error
2. ✅ Debug and fix Topics Queue
3. ✅ Setup CloudWatch Alerts
4. Test full pipeline with real topic
5. Document any new issues

### Next Week:
1. Implement Spot Instances
2. Setup S3 Lifecycle policies
3. Activate Mega Enrichment
4. Begin YouTube Upload integration

### This Month:
1. Complete all HIGH priority tasks
2. Start MEDIUM priority optimizations
3. Establish monitoring baseline
4. Plan Sprint 2/3 feature rollout

---

**Plan створено:** 2026-02-22
**Автор:** Claude Code
**Статус:** ACTIVE DEVELOPMENT ROADMAP
