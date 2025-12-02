# Testing Checklist - Week 2 Security Fixes
## YouTube Content Automation System

**Date:** 2025-12-01
**Deployed:** Week 2.1-2.5
**Status:** Ready for Testing

---

## 🎯 Testing Overview

Цей checklist покриває тестування всіх 5 Week 2 security fixes:
- ✅ Week 2.1: Timeout Configuration
- ✅ Week 2.2: Multi-Tenant Cost Tracking
- ✅ Week 2.3: IAM Policy Tightening
- ✅ Week 2.4: CSP Headers (після deployment)
- ✅ Week 2.5: Request Size Validation

---

## Week 2.1: Timeout Configuration Testing

### Test 1.1: Normal Operation ✅ CRITICAL
**Мета:** Переконатися, що timeout не впливає на нормальну роботу

**Кроки:**
1. Відкрити Dashboard → Content
2. Запустити генерацію контенту (повний workflow)
3. Дочекатися завершення

**Очікуваний результат:**
- ✅ Контент згенеровано успішно
- ✅ Всі фази пройшли без помилок
- ✅ У CloudWatch немає "timeout" або "timed out" помилок

**CloudWatch Log Query:**
```
fields @timestamp, @message
| filter @message like /timeout|timed out|ReadTimeout/
| sort @timestamp desc
| limit 50
```

---

### Test 1.2: Timeout Retry Behavior
**Мета:** Переконатися, що retry логіка працює

**Кроки:**
1. Перевірити CloudWatch Logs для будь-якої Lambda функції
2. Шукати "Retrying" або "attempt" у логах

**Очікуваний результат:**
- ℹ️ Якщо є проблеми з AWS сервісами, побачите "Retrying request (attempt X of 3)"
- ✅ Після 3 спроб має бути чітка помилка (не infinite hang)

**CloudWatch Log Query:**
```
fields @timestamp, @message
| filter @message like /[Rr]etry|attempt/
| sort @timestamp desc
| limit 50
```

---

## Week 2.2: Multi-Tenant Cost Tracking Testing

### Test 2.1: Cost Isolation ✅ CRITICAL
**Мета:** Переконатися, що витрати ізольовані per-user

**Кроки:**
1. Згенерувати контент як User A
2. Перевірити CostTracking table в DynamoDB
3. Згенерувати контент як User B
4. Перевірити знову

**DynamoDB Query:**
```bash
# Перевірити, чи всі записи мають user_id
aws dynamodb scan \
  --table-name CostTracking \
  --filter-expression "attribute_not_exists(user_id)" \
  --region eu-central-1

# Має повернути 0 items
```

**Очікуваний результат:**
- ✅ Всі cost записи мають поле `user_id`
- ✅ User A бачить лише свої витрати в Dashboard → Costs
- ✅ User B бачить лише свої витрати
- ❌ User A НЕ бачить витрати User B

**CloudWatch Log Query (content-narrative):**
```
fields @timestamp, @message
| filter @message like /Logged cost|user_id|WARNING.*Cost logged without/
| sort @timestamp desc
| limit 50
```

---

### Test 2.2: Cost Logging Warnings
**Мета:** Перевірити, що warning'и логуються коли user_id відсутній

**Кроки:**
1. Перевірити CloudWatch Logs для content-narrative
2. Шукати "WARNING: Cost logged without user_id"

**Очікуваний результат:**
- ✅ Якщо є legacy код без user_id - побачите WARNING
- ✅ Всі нові запити мають user_id (no warnings)

---

### Test 2.3: IDOR Prevention ✅ CRITICAL
**Мета:** Переконатися, що user не може отримати чужі channel configs

**Кроки:**
1. User A створює channel config (отримує config_id)
2. User B намагається згенерувати контент для config_id User A

**Очікуваний результат:**
- ❌ Має провалитися з помилкою:
  ```
  SECURITY ERROR: Channel config does not belong to user {user_id}
  ```
- ✅ User B може генерувати лише для своїх channels

**CloudWatch Log Query:**
```
fields @timestamp, @message
| filter @message like /SECURITY ERROR.*belong/
| sort @timestamp desc
| limit 50
```

---

## Week 2.3: IAM Policy Testing

### Test 3.1: Lambda Functions Still Work ✅ CRITICAL
**Мета:** Переконатися, що обмежені IAM policies не ламають функціональність

**Кроки:**
1. Запустити повний content generation workflow
2. Перевірити всі фази: theme → narrative → audio → images → save

**Очікуваний результат:**
- ✅ Всі Lambda функції виконуються успішно
- ✅ Немає "AccessDenied" помилок у CloudWatch
- ✅ Step Functions execution завершується successfully

**CloudWatch Log Query (всі Lambda):**
```
fields @timestamp, @message
| filter @message like /AccessDenied|Access Denied|Forbidden|403/
| sort @timestamp desc
| limit 50
```

---

### Test 3.2: Secrets Access Still Works
**Мета:** Перевірити, що після detach SecretsManagerReadWrite доступ до secrets працює

**Кроки:**
1. Перевірити CloudWatch Logs для content-narrative або content-theme-agent
2. Шукати "API key retrieved" або "GetSecretValue"

**Очікуваний результат:**
- ✅ "✅ API key retrieved successfully"
- ❌ НЕМАЄ "AccessDenied" для GetSecretValue

---

### Test 3.3: Bedrock Model Access
**Мета:** Перевірити, що обмежений Bedrock policy дозволяє використовувати дозволені моделі

**Кроки:**
1. Згенерувати контент з images (викличе Bedrock або Replicate)
2. Перевірити CloudWatch Logs

**Очікуваний результат:**
- ✅ Якщо використовується Bedrock SD3.5 - працює
- ✅ Якщо використовується інший провайдер - працює
- ❌ Якщо спробувати невалідну модель - AccessDenied

---

## Week 2.4: CSP Headers Testing (Після Deployment)

### Test 4.1: Check Headers Present
**Мета:** Переконатися, що CSP headers додані

**Кроки:**
```bash
# З командного рядка
curl -I https://YOUR_DOMAIN/

# Або у браузері: DevTools → Network → Headers
```

**Очікуваний результат:**
```
Content-Security-Policy: default-src 'self'; ...
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), ...
```

---

### Test 4.2: Pages Load Correctly ✅ CRITICAL
**Мета:** CSP не ламає існуючу функціональність

**Тестувати ВСІ сторінки:**
- [ ] index.html (main landing)
- [ ] login.html (Google OAuth)
- [ ] callback.html (OAuth callback)
- [ ] dashboard.html (main dashboard)
- [ ] channels.html (channel management)
- [ ] content.html (content display)
- [ ] costs.html (costs display)
- [ ] prompts-editor.html (prompt editing)
- [ ] settings.html (user settings)
- [ ] documentation.html (docs)
- [ ] audio-library.html (audio library)

**Очікуваний результат:**
- ✅ Всі сторінки завантажуються
- ✅ Всі скрипти виконуються
- ✅ Всі стилі застосовані
- ✅ Google OAuth працює
- ✅ API calls працюють

---

### Test 4.3: Check Console for CSP Violations
**Мета:** Знайти CSP порушення

**Кроки:**
1. Відкрити DevTools (F12)
2. Перейти на Console tab
3. Шукати повідомлення: "Refused to load... violates CSP"

**Очікуваний результат:**
- ✅ Немає CSP violations
- ⚠️ Якщо є - записати URL блокованого ресурсу
- 🔧 Додати дозволений URL до CSP policy

**Приклад CSP violation:**
```
Refused to load the script 'https://example.com/script.js'
because it violates the following Content Security Policy directive:
"script-src 'self' https://cdn.jsdelivr.net"
```

---

### Test 4.4: Security Headers Grade
**Мета:** Отримати оцінку безпеки

**Кроки:**
1. Перейти на https://securityheaders.com/
2. Ввести YOUR_DOMAIN
3. Натиснути "Scan"

**Очікуваний результат:**
- 🎯 **Grade A** або **A+**
- ✅ Всі headers present
- ✅ CSP score high

---

## Week 2.5: Request Size Validation Testing

### Test 5.1: Normal Requests Succeed ✅ CRITICAL
**Мета:** Звичайні запити не блокуються

**Кроки:**
1. Згенерувати звичайний контент (1-20 scenes)
2. Перевірити, що генерація пройшла успішно

**Очікуваний результат:**
- ✅ Генерація пройшла без помилок
- ✅ У CloudWatch логах:
  ```
  ✅ Request size: 45.23KB (limit: 10MB)
  ✅ Field 'scenes' count: 15 (limit: 100)
  ```

**CloudWatch Log Query (content-narrative):**
```
fields @timestamp, @message
| filter @message like /Request size|Field.*count/
| sort @timestamp desc
| limit 50
```

---

### Test 5.2: Oversized Requests Blocked ✅ CRITICAL
**Мета:** Надто великі запити блокуються

**Тест для content-narrative (10MB limit):**

**Як протестувати:**
1. Створити тестовий запит з 101+ scenes (більше limit=100)
2. АБО створити запит з дуже великими scene descriptions (>10MB)

**Очікуваний результат:**
- ❌ Запит має провалитися
- 📝 Повернути HTTP 413 (Payload Too Large)
- 📝 Error message:
  ```json
  {
    "statusCode": 413,
    "error": "Request too large: Field 'scenes' has 101 items, exceeds limit of 100"
  }
  ```

**CloudWatch Log Query:**
```
fields @timestamp, @message
| filter @message like /❌ Request validation failed|Request too large|exceeds limit/
| sort @timestamp desc
| limit 50
```

---

### Test 5.3: content-save-result Size Limit
**Мета:** content-save-result має вищий ліміт (20MB)

**Кроки:**
1. Згенерувати контент з багатьма images та audio files
2. Результат має проходити через save-result

**Очікуваний результат:**
- ✅ Великі payloads (до 20MB) приймаються
- ✅ У CloudWatch:
  ```
  ✅ Request size: 15.67MB (limit: 20MB)
  ```
- ❌ Якщо >20MB - блокується з помилкою

---

## 🔍 CloudWatch Logs Monitoring

### Quick Links (Replace with actual Log Groups)
```bash
# content-narrative logs
aws logs tail /aws/lambda/content-narrative \
  --follow --format short --region eu-central-1

# content-save-result logs
aws logs tail /aws/lambda/content-save-result \
  --follow --format short --region eu-central-1

# content-audio-tts logs
aws logs tail /aws/lambda/content-audio-tts \
  --follow --format short --region eu-central-1
```

---

### Key Search Patterns

**Security Issues:**
```
fields @timestamp, @message
| filter @message like /SECURITY|AccessDenied|Forbidden|unauthorized/
| sort @timestamp desc
| limit 100
```

**Validation Errors:**
```
fields @timestamp, @message
| filter @message like /validation failed|too large|exceeds limit/
| sort @timestamp desc
| limit 100
```

**Cost Tracking:**
```
fields @timestamp, @message
| filter @message like /Logged.*cost|user_id/
| sort @timestamp desc
| limit 100
```

**Timeout Issues:**
```
fields @timestamp, @message
| filter @message like /timeout|timed out|ReadTimeout|retry/
| sort @timestamp desc
| limit 100
```

---

## 🚨 Critical Issues to Watch

### HIGH Priority

1. **AccessDenied Errors**
   - Означає IAM policies занадто обмежені
   - 🔧 Fix: Розширити IAM policy для конкретного ресурсу

2. **Missing user_id in Costs**
   - Означає cost tracking не ізольований
   - 🔧 Fix: Перевірити, чи user_id передається в event

3. **CSP Breaking Pages**
   - Означає CSP policy занадто строга
   - 🔧 Fix: Додати потрібний домен до CSP

4. **Normal Requests Blocked by Size Validation**
   - Означає ліміти занадто низькі
   - 🔧 Fix: Збільшити limit в validate_content_generation_request()

---

### MEDIUM Priority

1. **Timeout Warnings**
   - Можливі тимчасові проблеми з AWS
   - ✅ Retry логіка має обробити автоматично

2. **CSP Violations in Console**
   - CDN або external resource блокується
   - 🔧 Fix: Додати до CSP whitelist

---

## ✅ Testing Sign-Off

### Week 2.1: Timeout Configuration
- [ ] Test 1.1: Normal Operation ✅
- [ ] Test 1.2: Retry Behavior
- [ ] CloudWatch logs checked - no timeout errors
- [ ] **Sign-off:** ________________ Date: ________

### Week 2.2: Multi-Tenant Cost Tracking
- [ ] Test 2.1: Cost Isolation ✅ CRITICAL
- [ ] Test 2.2: Cost Logging Warnings
- [ ] Test 2.3: IDOR Prevention ✅ CRITICAL
- [ ] DynamoDB scan - all records have user_id
- [ ] **Sign-off:** ________________ Date: ________

### Week 2.3: IAM Policy Tightening
- [ ] Test 3.1: Lambda Functions Work ✅ CRITICAL
- [ ] Test 3.2: Secrets Access Works
- [ ] Test 3.3: Bedrock Model Access
- [ ] CloudWatch logs - no AccessDenied errors
- [ ] **Sign-off:** ________________ Date: ________

### Week 2.4: CSP Headers
- [ ] Test 4.1: Headers Present
- [ ] Test 4.2: All Pages Load ✅ CRITICAL (11 pages)
- [ ] Test 4.3: No CSP Violations
- [ ] Test 4.4: Security Grade A/A+
- [ ] **Sign-off:** ________________ Date: ________

### Week 2.5: Request Size Validation
- [ ] Test 5.1: Normal Requests Succeed ✅ CRITICAL
- [ ] Test 5.2: Oversized Requests Blocked ✅ CRITICAL
- [ ] Test 5.3: content-save-result Limit
- [ ] CloudWatch logs - validation working
- [ ] **Sign-off:** ________________ Date: ________

---

## 📊 Testing Summary

**Total Tests:** 15
**Critical Tests:** 8
**Estimated Time:** 2-3 hours

**Priority Order:**
1. Week 2.2 (Cost Isolation - найбільший security risk)
2. Week 2.5 (Size Validation - може блокувати legitimate requests)
3. Week 2.3 (IAM - може ламати функціональність)
4. Week 2.4 (CSP - може ламати frontend)
5. Week 2.1 (Timeout - найменший impact)

---

**Generated:** 2025-12-01
**Status:** Ready for Testing
**Next Review:** After production testing complete
