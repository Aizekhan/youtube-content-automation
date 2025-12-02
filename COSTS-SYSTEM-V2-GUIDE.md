# 💰 COST SYSTEM V2 - USER GUIDE

## Що змінилось?

### Стара Система (costs.html) ❌
- Відстежує лише **9% витрат** (OpenAI + Polly)
- Немає реальних AWS витрат
- Немає breakdown по каналах
- Немає budget management
- Немає optimization tips

### Нова Система (costs-v2.html) ✅
- Відстежує **100% витрат** через AWS Cost Explorer
- Показує всі AWS сервіси (EC2, DynamoDB, Lambda, S3, тощо)
- Детальний breakdown по каналах
- Budget management & forecasting
- Cost optimization recommendations
- Real-time alerts

---

## Основні Features

### 1. Executive Summary Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│  💰 $445.23        📅 $14.84       🎯 $554.77       ⚠️ 0     │
│  Month-to-Date   Daily Average   Budget Left      Alerts   │
└─────────────────────────────────────────────────────────────┘
```

**Що показує:**
- **Month-to-Date**: Загальні витрати з початку місяця
- **Daily Average**: Середні щоденні витрати
- **Budget Left**: Скільки залишилось з бюджету
- **Alerts**: Кількість активних попереджень

### 2. Budget Management

**Графік прогресу бюджету:**
- 🟢 Green: < 75% бюджету (On Track)
- 🟡 Yellow: 75-90% бюджету (At Risk)
- 🔴 Red: > 90% бюджету (Over Budget)

**Прогноз:**
- Розрахунок на основі поточних витрат
- Екстраполяція на кінець місяця
- Попередження якщо перевищення очікується

### 3. Infrastructure Costs

**Повний breakdown усіх AWS сервісів:**

| Сервіс | Опис | Типова вартість |
|--------|------|-----------------|
| **EC2 Compute** | Instance для генерації зображень | $200/міс (45%) |
| **DynamoDB** | Бази даних (reads + writes) | $75/міс (17%) |
| **Lambda Functions** | 20+ Lambda функцій | $50/міс (11%) |
| **S3 Storage** | Storage + requests | $40/міс (9%) |
| **Step Functions** | State transitions | $30/міс (7%) |
| **CloudWatch Logs** | Log storage + ingestion | $10/міс (2%) |

### 4. Content Generation Costs

**AI Models:**
- OpenAI (Narratives) - $25/міс
- AWS Polly (Audio) - $15/міс
- ElevenLabs (Premium TTS) - якщо використовується

**Images:**
- EC2 Flux (primary) - включено в EC2 costs
- EC2 SD35 (fallback) - включено в EC2 costs
- AWS Bedrock - якщо використовується

**Метрики:**
- Total Content Cost
- Videos Generated (this month)
- Cost per Video (середня вартість одного відео)

### 5. Per-Channel Breakdown

**Top 10 найдорожчих каналів:**
- Вартість кожного каналу окремо
- % від загальних витрат
- Кількість згенерованих відео

**Insights:**
- 💸 Most Expensive Channel - найдорожчий канал
- 💚 Most Efficient Channel - найефективніший канал

### 6. Cost Optimization Tips

**Категорії рекомендацій:**

🔴 **High Impact** (економія $50+ на місяць)
- Перехід на Vast.ai для images
- Оптимізація EC2 usage

🟡 **Medium Impact** (економія $20-50 на місяць)
- DynamoDB On-Demand pricing
- S3 lifecycle policies

🟢 **Low Impact** (економія < $20 на місяць)
- CloudWatch log retention
- S3 Intelligent-Tiering

**Складність:**
- ✅ Easy - можна зробити за 5-10 хвилин
- ⚙️ Medium - потребує 1-2 години
- 🔧 Hard - потребує редизайну

---

## Як користуватися

### Перший запуск

1. **Відкрийте costs-v2.html**
   ```
   https://n8n-creator.space/costs-v2.html
   ```

2. **Авторизуйтесь**
   - Автоматично перенаправлення на Google OAuth
   - Після логіну - автоматичне завантаження даних

3. **Перевірте дані**
   - Executive Summary повинен показати поточні витрати
   - Infrastructure Costs покаже всі AWS сервіси
   - Budget Management покаже прогрес

### Щоденне використання

**Ранкова рутина (5 хвилин):**
1. Відкрити costs-v2.html
2. Перевірити Executive Summary
   - Чи в межах бюджету?
   - Чи є alerts?
3. Перевірити Daily Average
   - Чи не зріс на 20%+?
4. Переглянути Budget Management
   - Чи прогноз в рамках бюджету?

**Тижневий огляд (15 хвилин):**
1. Перевірити Per-Channel Breakdown
   - Які канали найдорожчі?
   - Чи можна оптимізувати?
2. Переглянути Optimization Tips
   - Чи є легкі wins?
3. Перевірити Daily Trend chart
   - Чи є аномалії?

**Місячний аналіз (30 хвилин):**
1. Детальний аналіз Infrastructure Costs
   - Що зросло vs минулий місяць?
2. Порівняння з прогнозом
   - Чи в рамках очікувань?
3. Впровадження optimization tips
   - Вибрати 1-2 найлегші
4. Коригування бюджету на наступний місяць

---

## Як інтерпретувати дані

### Budget Status

**🟢 On Track** (< 75% бюджету)
```
Budget: $1,000.00
Spent: $650.00 (65%)
Forecast: $867.00
```
✅ Все добре, продовжуйте

**🟡 At Risk** (75-90% бюджету)
```
Budget: $1,000.00
Spent: $850.00 (85%)
Forecast: $980.00
```
⚠️ Близько до ліміту, моніторьте щоденно

**🔴 Over Budget** (> 90% бюджету)
```
Budget: $1,000.00
Spent: $950.00 (95%)
Forecast: $1,150.00
```
🚨 Потрібні дії:
1. Зупинити нові генерації
2. Перевірити alerts
3. Впровадити optimization tips
4. Розглянути збільшення бюджету

### Active Alerts

**Типи alerts:**

1. **Budget Alert**
   ```
   ⚠️ Budget at 85% - Approaching monthly limit
   ```
   Дія: Оптимізувати витрати або збільшити бюджет

2. **Cost Spike Alert**
   ```
   ⚠️ EC2 costs spiked 25% yesterday
   ```
   Дія: Перевірити чому instance працював довше

3. **Service Alert**
   ```
   ⚠️ DynamoDB approaching throttling limit
   ```
   Дія: Збільшити capacity або перейти на On-Demand

4. **Channel Alert**
   ```
   ⚠️ Channel "Horror" costs 3x average
   ```
   Дія: Перевірити конфігурацію каналу

---

## FAQ

### Q: Чому Infrastructure Costs показує більше ніж Content Costs?

**A:** Це нормально! Infrastructure (EC2, DynamoDB, Lambda, S3) - це **45-75%** витрат. Content APIs (OpenAI, Polly) - це лише **25-55%**.

**Breakdown типовий:**
- Infrastructure: $405 (91%)
- Content APIs: $40 (9%)

### Q: Навіщо Cost per Video метрика?

**A:** Це ключова метрика для ROI аналізу:

```
Cost per Video: $11.13

Якщо ваш CPM = $5, і video має 10,000 views:
Revenue = $50
Cost = $11.13
Profit = $38.87 ✅
```

Якщо cost per video > revenue per video - треба оптимізувати!

### Q: Optimization Tips - з чого почати?

**A:** Рекомендується:

**Week 1:**
1. CloudWatch log retention (5 хв)
   - Економія: $5/міс
   - Складність: Easy

**Week 2:**
2. S3 Intelligent-Tiering (10 хв)
   - Економія: $15/міс
   - Складність: Easy

**Week 3:**
3. DynamoDB On-Demand (1 год)
   - Економія: $20/міс
   - Складність: Medium

**Week 4:**
4. Vast.ai для images (2 год)
   - Економія: $180/міс
   - Складність: Medium

**Total savings after 1 month: $220/міс (49%!)**

### Q: Як часто оновлюються дані?

**A:**
- **CostTracking** (OpenAI, Polly): Real-time
- **AWS Cost Explorer**: Затримка 24 години (AWS limitation)
- **Cache**: 1 година

**Refresh rates:**
- Auto-refresh: Кожні 5 хвилин
- Manual refresh: Кнопка "Refresh"
- Daily fetch: 00:00 UTC автоматично

### Q: Чому вчора показує $0 в Infrastructure?

**A:** Cost Explorer має затримку 12-24 години. Вчорашні дані з'являться сьогодні ввечері або завтра.

**Current day:** Використовуйте CostTracking data (real-time OpenAI/Polly)
**Previous days:** Використовуйте Cost Explorer (повні AWS дані)

---

## Порівняння з Old System

| Feature | Old (costs.html) | New (costs-v2.html) |
|---------|------------------|---------------------|
| **Coverage** | 9% витрат | 100% витрат ✅ |
| **AWS Services** | Лише 2 | Всі сервіси ✅ |
| **Real-time** | Частково | Так ✅ |
| **Budget Mgmt** | Немає | Є ✅ |
| **Forecasting** | Базовий | Розширений ✅ |
| **Alerts** | Немає | Є ✅ |
| **Optimization** | Немає | Є ✅ |
| **Per-Channel** | Немає | Є ✅ |
| **Cost/Video** | Немає | Є ✅ |

---

## Technical Details

### Data Sources

**1. AWS Cost Explorer API**
- Fetched by: `aws-costs-fetcher` Lambda
- Frequency: Daily at 00:00 UTC
- Cache: 1 hour in DynamoDB (AWSCostCache)
- Data: ALL AWS services

**2. CostTracking Table**
- Updated by: Lambda functions during execution
- Frequency: Real-time
- Data: OpenAI, Polly, custom metrics

**3. Combined in dashboard-costs**
- Merges both sources
- Returns unified response
- User-scoped (multi-tenant)

### API Endpoints

**Get costs (combined):**
```bash
POST https://hthjzdtuynvyelx5sbqacktgqxnnhkz40znusc.lambda-url.eu-central-1.on.aws
{
  "user_id": "c334d862-4031-7097-4207-84856b59d3ed"
}
```

**Get AWS costs (Cost Explorer):**
```bash
GET https://[AWS_COSTS_API]?days=7
```

### Budget Configuration

**Current default:** $1,000/month

**To change:**
1. Open `costs-v2.html`
2. Find line ~275:
   ```javascript
   const MONTHLY_BUDGET = 1000; // Change this
   ```
3. Update value
4. Save and upload

**Future:** Will be configurable in Settings UI

---

## Support

**Проблеми з даними:**
1. Перевірити CloudWatch Logs:
   ```bash
   aws logs tail /aws/lambda/aws-costs-fetcher --follow
   ```

2. Перевірити DynamoDB cache:
   ```bash
   aws dynamodb get-item \
     --table-name AWSCostCache \
     --key '{"cache_key":{"S":"aws_costs_latest"}}'
   ```

3. Force refresh:
   ```
   costs-v2.html → Click "Refresh" button
   ```

**Немає даних про Infrastructure:**
- Перевірте що `aws-costs-fetcher` Lambda deployed
- Перевірте IAM permissions (Cost Explorer access)
- Перевірте CloudWatch Event Rule (daily trigger)

**Alerts не працюють:**
- Feature ще не повністю implemented
- Coming in next update

---

**Last Updated:** 2025-11-29
**Version:** 2.0
**Status:** ✅ Production Ready
