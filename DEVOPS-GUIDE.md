# 🚀 DevOps Guide - YouTube Content Automation

Повна інструкція по роботі з новою CI/CD системою.

**Дата створення:** 2025-12-02
**Версія:** 1.0
**Статус:** Production Ready

---

## 📋 Зміст

1. [Огляд системи](#огляд-системи)
2. [Як робити зміни в Lambda](#як-робити-зміни-в-lambda)
3. [Як робити зміни в інфраструктурі](#як-робити-зміни-в-інфраструктурі)
4. [Моніторинг deployment](#моніторинг-deployment)
5. [Rollback процедури](#rollback-процедури)
6. [Troubleshooting](#troubleshooting)
7. [Emergency процедури](#emergency-процедури)

---

## 🎯 Огляд системи

### Що у нас є:

**CI/CD Pipeline (GitHub Actions):**
- ✅ Автоматичний deployment Lambda функцій
- ✅ Code quality checks
- ✅ Security scanning
- ✅ Terraform validation

**Infrastructure as Code (Terraform):**
- ✅ 4 DynamoDB таблиці під Terraform
- ✅ Remote state на S3
- ✅ State locking через DynamoDB

**Telegram Notifications:**
- ✅ Error alerts
- ✅ Deployment notifications (TODO: додати)

### Архітектура:

```
Developer (Ти або Claude)
    ↓
Git Commit + Push
    ↓
GitHub Actions ─────┬─── Tests & Validation
    │               ├─── Terraform Plan
    │               └─── Security Scan
    ↓
Deploy to AWS ──────┬─── Lambda Functions
    │               ├─── DynamoDB (via Terraform)
    │               └─── S3 State Update
    ↓
Telegram Notification
```

---

## 💻 Як робити зміни в Lambda

### Через Claude (рекомендовано):

**Крок 1:** Попроси Claude
```
"Додай валідацію в content-narrative Lambda"
```

**Крок 2:** Claude:
1. Редагує код
2. Git commit
3. Git push
4. Каже тобі: "✅ Запушено, GitHub Actions деплоїть"

**Крок 3:** Переглянь deployment
- Перейди на: https://github.com/Aizekhan/youtube-content-automation/actions
- Знайди останній workflow run
- Дочекайся зеленого ✅ (або червоного ❌)

**Час deployment:** ~5-10 хвилин

### Вручну (якщо треба):

```bash
# 1. Відредагуй файл
nano aws/lambda/content-narrative/lambda_function.py

# 2. Закоміть
git add aws/lambda/content-narrative/lambda_function.py
git commit -m "feat: Add validation to content-narrative"

# 3. Запуш
git push

# 4. Дочекайся deployment
# Переглянь: https://github.com/Aizekhan/youtube-content-automation/actions
```

### Що деплоїться автоматично:

GitHub Actions детектить зміни в `aws/lambda/*` і деплоїть ТІЛЬКИ змінені функції паралельно.

**Приклад:**
- Змінив `content-narrative` → деплоїться тільки вона
- Змінив 3 Lambda → деплояться всі 3 паралельно

---

## 🏗️ Як робити зміни в інфраструктурі

### DynamoDB таблиці (через Terraform):

**Крок 1:** Попроси Claude
```
"Додай новий GSI в GeneratedContent таблицю"
```

**Крок 2:** Claude:
1. Редагує `terraform/dynamodb.tf`
2. Запускає `terraform plan` (показує що зміниться)
3. Git commit + push
4. GitHub Actions запускає Terraform validation

**Крок 3:** Застосування змін
```bash
# Локально (якщо треба зараз):
cd terraform
terraform apply

# Або чекай наступного PR merge (якщо не терміново)
```

⚠️ **ВАЖЛИВО:** Terraform state на S3, тому можна працювати з будь-якого комп'ютера!

---

## 📊 Моніторинг Deployment

### GitHub Actions:

**URL:** https://github.com/Aizekhan/youtube-content-automation/actions

**Що дивитися:**
- ✅ Зелена галочка = успіх
- ❌ Червоний хрестик = помилка
- 🟡 Жовте коло = в процесі

**Деталі:**
1. Клікни на workflow run
2. Подивись які Lambda деплоїлись
3. Переглянь логи якщо щось зламалось

### Terraform Validation:

Кожен PR автоматично отримує коментар з `terraform plan`:

```
#### Terraform Format and Style 🖌✅
#### Terraform Initialization ⚙️✅
#### Terraform Validation 🤖✅
#### Terraform Plan 📖✅

Show Plan
```

### Telegram Notifications:

Якщо щось зламалось - отримаєш повідомлення в Telegram:

```
🚨 YouTube Automation Alert

Type: Lambda Execution Error
Time: 2025-12-02T10:30:00Z
Execution: test-execution-123

Error: ValidationError
Details: Invalid input parameters

⚠️ Check AWS Console for full details
```

---

## ⏮️ Rollback Процедури

### Rollback Lambda:

**Метод 1: Git Revert (рекомендовано)**

```bash
# 1. Знайди коміт який треба відмінити
git log --oneline

# 2. Зроби revert
git revert <commit-hash>

# 3. Запуш (автоматично задеплоїть стару версію)
git push
```

**Метод 2: AWS Console (швидко, але не Git)**

```bash
# В AWS Lambda Console:
1. Відкрий Lambda функцію
2. Versions → Попередня версія
3. Aliases → Update 'production' to previous version
```

### Rollback Terraform:

**Повний rollback infrastructure:**

```bash
cd terraform

# 1. Подивись Git history
git log -- terraform/

# 2. Повернись до попереднього коміту
git checkout <commit-hash> -- terraform/

# 3. Застосуй
terraform plan  # перевір що повертається
terraform apply

# 4. Закоміть rollback
git commit -m "rollback: Revert infrastructure to <commit>"
git push
```

---

## 🔧 Troubleshooting

### GitHub Actions не запускається:

**Перевір:**
1. AWS credentials в GitHub Secrets:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
2. Чи є зміни в `aws/lambda/*`?
3. Чи не заблокований workflow в Settings?

**Фікс:**
```bash
# Переконайся що secrets налаштовані
# GitHub → Settings → Secrets → Actions
```

### Terraform plan показує зміни які не очікував:

**Причини:**
1. Хтось змінив інфраструктуру напряму в AWS
2. State file застарів
3. Конфлікт версій

**Фікс:**
```bash
# Оновити state з AWS
terraform refresh

# Або імпортувати ресурс заново
terraform import aws_dynamodb_table.name TableName
```

### Lambda deployment failed:

**Перевір:**
1. Логи в GitHub Actions
2. Чи правильний ZIP packaging?
3. Чи не перевищений розмір (50 MB)?

**Фікс:**
```bash
# Локальний deploy для debug
cd aws/lambda/function-name
./create_zip.py  # якщо є
aws lambda update-function-code \
  --function-name function-name \
  --zip-file fileb://function.zip
```

---

## 🚨 Emergency Процедури

### Production Down - КРИТИЧНО

**Якщо Lambda не працює ЗАРАЗ:**

```bash
# 1. НЕГАЙНИЙ HOTFIX (bypass CI/CD)
aws lambda update-function-code \
  --function-name <FUNCTION> \
  --zip-file fileb://function.zip

# 2. ПІСЛЯ фіксу - закоміть зміни в Git!
git add .
git commit -m "hotfix: Emergency fix for production issue"
git push

# 3. Повідом команду що був hotfix
```

### DynamoDB Table Down:

```bash
# 1. Перевір статус
aws dynamodb describe-table --table-name GeneratedContent

# 2. Якщо потрібен restore
aws dynamodb restore-table-to-point-in-time \
  --source-table-name GeneratedContent \
  --target-table-name GeneratedContent-restored \
  --restore-date-time 2025-12-02T10:00:00Z

# 3. Update Terraform після restore
terraform import aws_dynamodb_table.generated_content GeneratedContent-restored
```

### Terraform State Corruption:

```bash
# 1. Backup поточного state
aws s3 cp s3://terraform-state-599297130956/production/terraform.tfstate ./backup-state.tfstate

# 2. Відновити попередню версію
aws s3api list-object-versions \
  --bucket terraform-state-599297130956 \
  --prefix production/terraform.tfstate

aws s3api get-object \
  --bucket terraform-state-599297130956 \
  --key production/terraform.tfstate \
  --version-id <VERSION-ID> \
  ./restored-state.tfstate

# 3. Закинути назад
aws s3 cp ./restored-state.tfstate s3://terraform-state-599297130956/production/terraform.tfstate
```

---

## ⚙️ Налаштування GitHub Secrets

### Telegram Notifications

GitHub Actions вже налаштовані для відправки Telegram сповіщень про deployment. Потрібно додати secrets:

**Крок 1:** Перейди на GitHub Settings
```
https://github.com/Aizekhan/youtube-content-automation/settings/secrets/actions
```

**Крок 2:** Додай 2 secrets

1. **TELEGRAM_BOT_TOKEN**
   - Name: `TELEGRAM_BOT_TOKEN`
   - Value: `8222377088:AAGoRh5ST40ci05SbxS953_tnA5jD4lH2ts`

2. **TELEGRAM_CHAT_ID**
   - Name: `TELEGRAM_CHAT_ID`
   - Value: `784661667`

**Крок 3:** Перевір

Після додавання secrets, кожен deployment автоматично буде відправляти повідомлення:
- ✅ Успішний deployment
- ❌ Помилка deployment
- Список змінених Lambda функцій
- Посилання на workflow run

### AWS Credentials

AWS credentials вже налаштовані в GitHub Secrets:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

⚠️ **ВАЖЛИВО:** Ніколи не commit'ь ці значення в Git!

---

## 📞 Контакти і Ресурси

**GitHub Repository:**
https://github.com/Aizekhan/youtube-content-automation

**GitHub Actions:**
https://github.com/Aizekhan/youtube-content-automation/actions

**AWS Console:**
https://eu-central-1.console.aws.amazon.com/lambda

**Terraform State:**
s3://terraform-state-599297130956/production/terraform.tfstate

**Telegram Bot:**
Налаштований в SystemSettings DynamoDB table

---

## 📝 Best Practices

### DO ✅:
- Завжди робити зміни через Git
- Дочекатися GitHub Actions перед мерджем PR
- Тестувати локально перед push
- Писати чіткі commit messages
- Дивитися terraform plan перед apply

### DON'T ❌:
- Не змінювати AWS напряму (тільки через Terraform/CI/CD)
- Не робити force push на master
- Не пропускати GitHub Actions перевірки
- Не видаляти Terraform state вручну
- Не деплоїти в production без тестування

---

**Останнє оновлення:** 2025-12-02
**Автор:** Claude Code
**Версія:** 1.0
