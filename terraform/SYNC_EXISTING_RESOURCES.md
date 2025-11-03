# Синхронізація існуючих AWS ресурсів з Terraform

## Проблема

У нас є **дві паралельні інфраструктури**:

1. **Існуюча** (створена через AWS CLI/консоль)
   - Lambda: theme-agent, narrative, prompts-api
   - DynamoDB: AIPromptConfigs, ChannelConfigs
   - Secrets Manager: OpenAI API Key

2. **Terraform конфігурація** (ще не задеплоєна)
   - Нові назви Lambda функцій
   - Нові DynamoDB таблиці

## Рішення: 2 варіанти

### ✅ Варіант 1: Імпортувати існуючі ресурси (РЕКОМЕНДОВАНО)

**Переваги:**
- Зберігаємо існуючі дані в DynamoDB
- Не треба перестворювати Lambda
- Мінімальний downtime

**Недоліки:**
- Потрібно імпортувати кожен ресурс вручну

**Кроки:**

```bash
cd terraform

# 1. Змінити назви ресурсів у Terraform щоб вони збігалися з існуючими
# Відредагувати lambda.tf, dynamodb.tf

# 2. Імпортувати DynamoDB таблиці
terraform import aws_dynamodb_table.ai_prompt_configs AIPromptConfigs
terraform import aws_dynamodb_table.channel_configs ChannelConfigs

# 3. Імпортувати Lambda функції
terraform import aws_lambda_function.content_theme_agent theme-agent
terraform import aws_lambda_function.content_narrative narrative
terraform import aws_lambda_function.prompts_api prompts-api

# 4. Імпортувати IAM ролі (якщо існують)
terraform import aws_iam_role.lambda_execution_role existing-lambda-role-name

# 5. Імпортувати Secrets Manager
terraform import aws_secretsmanager_secret.openai_api_key youtube-automation-openai-key
terraform import aws_secretsmanager_secret_version.openai_api_key youtube-automation-openai-key

# 6. Перевірити стан
terraform plan
# Має показати "No changes"
```

---

### ✅ Варіант 2: Створити нову інфраструктуру (ЧИСТИЙ СТАРТ)

**Переваги:**
- Чиста інфраструктура
- Всі ресурси мають консистентні назви
- Повний контроль через Terraform

**Недоліки:**
- Втрата даних в існуючих DynamoDB таблицях
- Downtime під час перемикання

**Кроки:**

```bash
# 1. Експортувати дані з існуючих таблиць
aws dynamodb scan --table-name AIPromptConfigs > backup-ai-prompts.json
aws dynamodb scan --table-name ChannelConfigs > backup-channels.json

# 2. Видалити старі ресурси (опціонально, можна залишити)
# aws lambda delete-function --function-name theme-agent
# aws lambda delete-function --function-name narrative
# aws lambda delete-function --function-name prompts-api

# 3. Розгорнути через Terraform
cd terraform
terraform init
terraform apply

# 4. Відновити дані в нові таблиці
# (скрипт для імпорту з backup-*.json)

# 5. Оновити prompts-editor.html з новим API URL
terraform output prompts_api_url
# Вставити в prompts-editor.html
```

---

## 🔑 Missing Secrets - що ще потрібно додати

### Поточні secrets в Terraform:
- ✅ OpenAI API Key

### Missing secrets:
- ❌ Notion API Key
- ❌ Notion Database IDs
- ❌ YouTube API credentials (якщо використовуєте)
- ❌ Інші API ключі

### Додати missing secrets:

```hcl
# terraform/iam.tf - додати після openai_api_key

# Notion Integration
resource "aws_secretsmanager_secret" "notion_integration" {
  name        = "${var.project_name}/notion-integration"
  description = "Notion API credentials"
}

resource "aws_secretsmanager_secret_version" "notion_integration" {
  secret_id = aws_secretsmanager_secret.notion_integration.id
  secret_string = jsonencode({
    api_key           = var.notion_api_key
    tasks_database_id = var.notion_tasks_database_id
  })
}

# YouTube API (якщо потрібно)
resource "aws_secretsmanager_secret" "youtube_credentials" {
  count       = var.youtube_api_key != "" ? 1 : 0
  name        = "${var.project_name}/youtube-credentials"
  description = "YouTube Data API credentials"
}

resource "aws_secretsmanager_secret_version" "youtube_credentials" {
  count         = var.youtube_api_key != "" ? 1 : 0
  secret_id     = aws_secretsmanager_secret.youtube_credentials[0].id
  secret_string = var.youtube_api_key
}
```

```hcl
# terraform/variables.tf - додати

variable "notion_api_key" {
  description = "Notion API Key"
  type        = string
  sensitive   = true
  default     = ""
}

variable "notion_tasks_database_id" {
  description = "Notion Tasks Database ID"
  type        = string
  sensitive   = true
  default     = ""
}

variable "youtube_api_key" {
  description = "YouTube Data API Key"
  type        = string
  sensitive   = true
  default     = ""
}
```

---

## 🔄 Terraform Workflow (як працювати далі)

### Коли додаєте нові ресурси:

#### 1. Нова Lambda функція

```bash
# 1. Створити код
mkdir aws/lambda/new-function
vim aws/lambda/new-function/lambda_function.py

# 2. Додати в terraform/lambda.tf
data "archive_file" "new_function" {
  type        = "zip"
  source_dir  = "../aws/lambda/new-function"
  output_path = "${path.module}/.terraform/archives/new-function.zip"
}

resource "aws_lambda_function" "new_function" {
  filename         = data.archive_file.new_function.output_path
  function_name    = "${var.project_name}-new-function"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = var.lambda_runtime
  source_code_hash = data.archive_file.new_function.output_base64sha256
}

# 3. Apply
terraform apply
```

#### 2. Нова DynamoDB таблиця

```bash
# terraform/dynamodb.tf
resource "aws_dynamodb_table" "new_table" {
  name         = "NewTable"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }
}

# Apply
terraform apply
```

#### 3. Оновлення існуючої Lambda

```bash
# 1. Змінити код
vim aws/lambda/theme-agent/lambda_function.py

# 2. Terraform автоматично виявить зміни
terraform plan
# Shows: source_code_hash changed

# 3. Apply (оновить Lambda)
terraform apply
```

---

## ⚠️ ВАЖЛИВО: Terraform State

Terraform зберігає стан у файлі `terraform.tfstate`.

**НЕ КОМІТЬТЕ** `terraform.tfstate` в Git!

Для production використовуйте **Remote State**:

```hcl
# terraform/main.tf
terraform {
  backend "s3" {
    bucket         = "youtube-automation-terraform-state"
    key            = "terraform.tfstate"
    region         = "eu-central-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}
```

Створити S3 bucket для state:

```bash
# Один раз вручну
aws s3 mb s3://youtube-automation-terraform-state --region eu-central-1
aws s3api put-bucket-versioning \
  --bucket youtube-automation-terraform-state \
  --versioning-configuration Status=Enabled

# DynamoDB для state locking
aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region eu-central-1
```

---

## 🎯 Рекомендація для вашого проекту

### Варіант A: Продовжити без Terraform (якщо все працює)

**Pros:**
- Все вже працює
- Немає ризику зламати

**Cons:**
- Немає Infrastructure as Code
- Важко відтворити в іншому регіоні/акаунті

### Варіант B: Імпортувати існуючі ресурси (КРАЩЕ)

**Pros:**
- IaC для майбутніх змін
- Зберігаємо існуючі дані
- Можна поступово мігрувати

**Cons:**
- Потрібен час на імпорт

### Варіант C: Створити паралельну інфраструктуру

**Pros:**
- Чисто
- Можна тестувати без ризику

**Cons:**
- Подвійні витрати
- Треба перемикатися

---

## 📋 Checklist для синхронізації

- [ ] Вибрати варіант (A/B/C)
- [ ] Експортувати дані з DynamoDB (backup)
- [ ] Імпортувати або створити ресурси
- [ ] Додати missing secrets (Notion, YouTube)
- [ ] Оновити `.tf` файли з реальними назвами
- [ ] Протестувати `terraform plan`
- [ ] Apply і перевірити
- [ ] Оновити prompts-editor.html з новими URLs
- [ ] Налаштувати Remote State (S3)

---

**Питання для вас:**

1. Чи хочете зберегти існуючі дані в DynamoDB?
2. Чи можна мати короткий downtime?
3. Чи будемо використовувати Terraform для майбутніх змін?

На основі відповідей я можу допомогти з конкретним планом міграції.
