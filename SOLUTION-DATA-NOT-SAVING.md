# РІШЕННЯ: Чому Дані Не Зберігаються

**Дата**: 2026-02-12 00:50
**Статус**: ROOT CAUSE ЗНАЙДЕНО ✅
**Рішення**: ГОТОВЕ

---

## 🎯 ROOT CAUSE

**Проблема**: Після зміни `ResultPath: null` в Map state, дані перестали зберігатися в DynamoDB.

**Чому**:
1. `Phase3AudioAndSave` - це Map state
2. `SaveFinalContent` знаходиться ВСЕРЕДИНІ Map iterator
3. `ResultPath: null` відкидає ВСІ результати Map iterations
4. SaveFinalContent ВИКОНУЄТЬСЯ, але workflow НЕ ЗНАЄ про його результат
5. Якщо SaveFinalContent має validation error - workflow все одно SUCCEEDED

**Доказ**:
- ✅ Lambda `content-save-result` ПРАЦЮЄ (протестовано вручну)
- ✅ Мануальний виклик Lambda зберіг дані в DynamoDB
- ✅ Workflow показує SUCCEEDED
- ❌ Але дані НЕ зберігаються

**Висновок**: SaveFinalContent НЕ ОТРИМУЄ правильні дані від Step Functions.

---

## 🔧 РІШЕННЯ

### Option A: Повернути ResultPath (ШВИДКО, АЛЕ НЕ ІДЕАЛЬНО)

**Що робити:**
```python
# У Step Functions definition:
phase3['ResultPath'] = '$.finalResults'  # Було: None
```

**Переваги:**
- Одна строчка коду
- SaveFinalContent отримає всі дані
- Все запрацює

**Недоліки:**
- DataLimitExceeded вернеться для великих workflow (18+ scenes)
- Не масштабується

**Коли використовувати:**
- Для швидкого fix
- Для тестування з невеликою кількістю scenes (1-5)

---

### Option B: ResultSelector для Compact Output (РЕКОМЕНДОВАНО ⭐)

**Що робити:**
```json
{
  "Type": "Map",
  "ResultPath": "$.saveResults",
  "ResultSelector": {
    "saved.$": "$[*].status",
    "content_ids.$": "$[*].content_id"
  },
  ...
}
```

**Переваги:**
- Map зберігає результати, але тільки важливі поля
- Уникаємо DataLimitExceeded
- SaveFinalContent працює

**Недоліки:**
- Потрібно тестувати
- Може не працювати якщо SaveFinalContent fails

**Коли використовувати:**
- Для production
- Для великих workflow

---

### Option C: Catch Block для SaveFinalContent (НАЙКРАЩЕ 🏆)

**Що робити:**
Додати Catch block до SaveFinalContent, щоб errors не ігнорувалися:

```json
{
  "SaveFinalContent": {
    "Type": "Task",
    "Resource": "...",
    "Catch": [{
      "ErrorEquals": ["States.ALL"],
      "ResultPath": "$.saveError",
      "Next": "SaveFailed"
    }],
    "Next": "..."
  },
  "SaveFailed": {
    "Type": "Fail",
    "Error": "SaveContentFailed",
    "Cause": "Failed to save content to DynamoDB"
  }
}
```

**І** використовувати ResultPath з ResultSelector:
```json
{
  "ResultPath": "$.saveResults",
  "ResultSelector": {
    "count.$": "States.ArrayLength($)",
    "summary.$": "$[*].status"
  }
}
```

**Переваги:**
- Workflow FAIL якщо SaveFinalContent має error
- Зберігаємо тільки summary (уникаємо DataLimit)
- Production-ready

**Недоліки:**
- Більше конфігурації

---

## 🚀 ШВИДКИЙ FIX (Зараз)

Для НЕГАЙНОГО вирішення проблеми:

```python
import json, boto3

# 1. Get current definition
sf = boto3.client('stepfunctions', region_name='eu-central-1')
response = sf.describe_state_machine(
    stateMachineArn='arn:aws:states:eu-central-1:599297130956:stateMachine:ContentGenerator'
)

definition = json.loads(response['definition'])

# 2. Change ResultPath
phase3 = definition['States']['Phase3AudioAndSave']
phase3['ResultPath'] = '$.saveResults'
phase3['ResultSelector'] = {
    'saved_count': {
        'StringToJson': 'States.ArrayLength($)'
    }
}

# 3. Update
sf.update_state_machine(
    stateMachineArn='arn:aws:states:eu-central-1:599297130956:stateMachine:ContentGenerator',
    definition=json.dumps(definition)
)
```

Але для невеликих тестів (1-3 scenes) просто:
```python
phase3['ResultPath'] = '$.saveResults'  # Без ResultSelector
```

---

## ✅ ТЕСТУВАННЯ

Після fix:

1. **Запустити тест з 1 scene**:
```bash
aws stepfunctions start-execution \
  --state-machine-arn "arn:aws:states:eu-central-1:599297130956:stateMachine:ContentGenerator" \
  --name "test-save-fix-$(date +%s)" \
  --input '{"channel_ids":["UCRmO5HB89GW_zjX3dJACfzw"],"user_id":"c334d862-4031-7097-4207-84856b59d3ed","max_scenes":1}' \
  --region eu-central-1
```

2. **Перевірити DynamoDB**:
```bash
aws dynamodb scan \
  --table-name GeneratedContent \
  --filter-expression "begins_with(created_at, :now)" \
  --expression-attribute-values '{":now":{"S":"2026-02-12"}}' \
  --limit 5
```

3. **Якщо збереглося** - SUCCESS!
4. **Якщо DataLimitExceeded** - use ResultSelector (Option B)

---

## 📋 Чому Це Сталося

**Timeline:**
1. До змін: ResultPath був встановлений, все працювало
2. Ми змінили на `ResultPath: null` щоб виправити DataLimitExceeded
3. Це ВИПРАВИЛО DataLimitExceeded ✅
4. Але ЗЛАМАЛО SaveFinalContent ❌

**Урок**: ResultPath: null відкидає ВСІ результати, включно з успішністю/неуспішністю операцій всередині Map iterator.

---

## 🎬 Наступні Кроки

1. **ЗАРАЗ**: Змінити ResultPath назад або додати ResultSelector
2. **Протестувати** з 1 scene
3. **Якщо працює**: Протестувати з 3 scenes
4. **Якщо DataLimit**: Імплементувати ResultSelector properly
5. **Додати Catch blocks** для production reliability

---

## 💡 Додаткові Перевірки

Якщо після fix дані ВСЕ ОДНО не зберігаються, перевірити:

1. **CloudWatch Logs** для content-save-result:
```bash
aws logs tail /aws/lambda/content-save-result --follow
```

2. **Input до SaveFinalContent** в execution history
3. **Validation errors** у Lambda (missing config_id, etc)

---

**ПІДСУМОК**: Lambda працює. Проблема в Step Functions ResultPath. Рішення: Option A (швидко) або Option C (production).
