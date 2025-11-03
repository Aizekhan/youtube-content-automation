# ⚠️ Terraform vs Існуюча Інфраструктура

## 📊 Поточна ситуація

### Маємо 2 паралельні інфраструктури:

#### 1️⃣ **Існуюча** (створена вручну через AWS CLI)

```
✅ DynamoDB Tables:
   - AIPromptConfigs (2 агенти: theme_agent, narrative_architect)
   - ChannelConfigs (YouTube канали)

✅ Lambda Functions:
   - theme-agent (з OpenAI Responses API)
   - narrative (Narrative Architect)
   - prompts-api (з Function URL)

✅ Secrets Manager:
   - youtube-automation-openai-key (OpenAI API Key)

✅ Step Functions:
   - ContentGenerator (якщо вже створений)
```

#### 2️⃣ **Terraform** (ще НЕ розгорнуто)

```
📝 Terraform конфігурація готова:
   - 4 DynamoDB таблиці (включно з новими: GeneratedVideos, ContentQueue)
   - 7 Lambda функцій (з НОВИМИ назвами: youtube-content-automation-*)
   - Step Functions (новий ARN)
   - IAM roles (нові)
   - Secrets Manager (нові секрети)
```

---

## ❓ Чому Terraform НЕ автоматичний?

**Terraform працює так:**

1. **Створює нові ресурси** - коли робите `terraform apply`, він створює ресурси
2. **НЕ бачить існуючі** - якщо ви створили Lambda через AWS CLI, Terraform про нього не знає
3. **Потрібен terraform.tfstate** - стан зберігається локально

**Приклад:**

```bash
# У вас є Lambda "theme-agent" створена вручну
aws lambda list-functions

# Terraform НЕ бачить її
terraform plan
# Output: Will create aws_lambda_function.content_theme_agent

# Terraform створить НОВУ Lambda з новою назвою!
terraform apply
# Output: Created youtube-content-automation-theme-agent

# Тепер у вас ДВІ Lambda функції:
# 1. theme-agent (стара, вручну)
# 2. youtube-content-automation-theme-agent (нова, через Terraform)
```

---

## 🎯 3 варіанти дій

### ✅ Варіант 1: Продовжити БЕЗ Terraform

**Коли вибирати:**
- Все працює, не хочеш ламати
- Невеликий проект, змін мало
- Не потрібно відтворювати в іншому акаунті

**Плюси:**
- ✅ Нічого не ламається
- ✅ Можна продовжувати через AWS CLI

**Мінуси:**
- ❌ Немає Infrastructure as Code
- ❌ Важко відтворити
- ❌ Ручне управління

**Дії:**
```bash
# Просто видалити папку terraform/
rm -rf terraform/

# Або залишити для майбутнього
```

---

### ✅ Варіант 2: Імпортувати існуючі ресурси (РЕКОМЕНДУЮ)

**Коли вибирати:**
- Хочеш IaC для майбутніх змін
- Є важливі дані в DynamoDB
- Не можна мати downtime

**Плюси:**
- ✅ Зберігаємо всі дані
- ✅ Terraform бачить існуючі ресурси
- ✅ Можна поступово мігрувати

**Мінуси:**
- ⚠️ Треба імпортувати кожен ресурс
- ⚠️ Назви в Terraform мають збігатися

**Дії:**

```bash
cd terraform

# 1. Створити terraform.tfvars
cp terraform.tfvars.example terraform.tfvars
vim terraform.tfvars
# openai_api_key = "sk-..."

# 2. Змінити назви в lambda.tf щоб збігалися
# Замість: youtube-content-automation-theme-agent
# Використати: theme-agent

# 3. Імпортувати DynamoDB
terraform init
terraform import aws_dynamodb_table.ai_prompt_configs AIPromptConfigs
terraform import aws_dynamodb_table.channel_configs ChannelConfigs

# 4. Імпортувати Lambda
terraform import aws_lambda_function.content_theme_agent theme-agent
terraform import aws_lambda_function.content_narrative narrative
terraform import aws_lambda_function.prompts_api prompts-api

# 5. Імпортувати Secrets Manager
terraform import aws_secretsmanager_secret.openai_api_key youtube-automation-openai-key

# 6. Перевірити
terraform plan
# Має показати: "No changes" або minimal changes
```

**Детальна інструкція:** `terraform/SYNC_EXISTING_RESOURCES.md`

---

### ✅ Варіант 3: Створити НОВУ інфраструктуру

**Коли вибирати:**
- Хочеш чистий старт
- Немає важливих даних
- Можна мати короткий downtime

**Плюси:**
- ✅ Чиста інфраструктура
- ✅ Всі назви консистентні
- ✅ Повний контроль через Terraform

**Мінуси:**
- ❌ Втрата даних в DynamoDB (якщо не зробити backup)
- ❌ Downtime під час перемикання
- ❌ Треба оновити prompts-editor.html з новим API URL

**Дії:**

```bash
# 1. Backup існуючих даних
aws dynamodb scan --table-name AIPromptConfigs > backup-prompts.json
aws dynamodb scan --table-name ChannelConfigs > backup-channels.json

# 2. Розгорнути через Terraform
cd terraform
cp terraform.tfvars.example terraform.tfvars
vim terraform.tfvars  # Додати API keys

terraform init
terraform apply
# Output: Created 20+ resources

# 3. Відновити дані (приклад)
# Потрібен скрипт для імпорту з backup-*.json

# 4. Оновити prompts-editor.html
terraform output prompts_api_url
# Вставити новий URL в prompts-editor.html

# 5. Видалити старі ресурси (опціонально)
aws lambda delete-function --function-name theme-agent
aws lambda delete-function --function-name narrative
aws dynamodb delete-table --table-name AIPromptConfigs  # ОБЕРЕЖНО!
```

---

## 🔑 Missing Secrets - що ще треба додати

### Зараз в Terraform:

```hcl
✅ openai_api_key          # OpenAI API
✅ notion_api_key          # Notion Integration (опціонально)
✅ notion_tasks_database_id
✅ youtube_api_key         # YouTube API (опціонально)
```

### Знайдені credentials в проекті:

**В `.claude/mcp-config.json`:**
```json
"NOTION_TOKEN": "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"
```

⚠️ **НЕБЕЗПЕЧНО!** Цей токен в Git репозиторії!

**Що зробити:**

```bash
# 1. Видалити токен з mcp-config.json
vim .claude/mcp-config.json
# Замінити на: "NOTION_TOKEN": "${NOTION_API_KEY}"

# 2. Додати в terraform.tfvars
notion_api_key = "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"

# 3. terraform apply створить secret в Secrets Manager

# 4. Оновити .gitignore
echo ".claude/mcp-config.json" >> .gitignore
# Або використовувати .claude/mcp-config.json.example
```

---

## 🔄 Terraform Workflow (як працювати далі)

### Якщо вибрали Terraform:

#### 1. Додати нову Lambda функцію:

```bash
# Крок 1: Створити код
mkdir aws/lambda/new-function
vim aws/lambda/new-function/lambda_function.py

# Крок 2: Додати в terraform/lambda.tf
data "archive_file" "new_function" {
  source_dir = "../aws/lambda/new-function"
  ...
}

resource "aws_lambda_function" "new_function" {
  ...
}

# Крок 3: Apply
terraform apply
```

#### 2. Оновити існуючу Lambda:

```bash
# Змінити код
vim aws/lambda/theme-agent/lambda_function.py

# Terraform автоматично виявить зміни
terraform plan
# Output: source_code_hash changed

# Apply
terraform apply
# Output: Lambda function updated
```

#### 3. Додати DynamoDB таблицю:

```bash
# Додати в terraform/dynamodb.tf
resource "aws_dynamodb_table" "new_table" {
  name = "NewTable"
  ...
}

terraform apply
```

---

## 💡 Моя рекомендація

### Для вашого проекту:

**Варіант 2 (Імпорт)** - якщо:
- ✅ Хочете використовувати Terraform в майбутньому
- ✅ Є дані в DynamoDB які не можна втратити
- ✅ Є час на правильну міграцію

**Варіант 1 (БЕЗ Terraform)** - якщо:
- ✅ Все працює і не хочете ризикувати
- ✅ Невеликий проект, зміни рідкі

**Варіант 3 (Новий)** - якщо:
- ✅ Можна почати з чистого аркуша
- ✅ Немає критичних даних

---

## 📋 Чеклист для міграції

### Підготовка:
- [ ] Вибрати варіант (1/2/3)
- [ ] Зробити backup DynamoDB
- [ ] Переглянути всі credentials в проекті
- [ ] Створити terraform.tfvars з усіма секретами

### Якщо Варіант 2 (Імпорт):
- [ ] Змінити назви в *.tf файлах
- [ ] terraform init
- [ ] Імпортувати всі DynamoDB таблиці
- [ ] Імпортувати всі Lambda функції
- [ ] Імпортувати Secrets Manager
- [ ] terraform plan (має показати "No changes")
- [ ] Протестувати

### Якщо Варіант 3 (Новий):
- [ ] Backup всіх даних
- [ ] terraform apply
- [ ] Відновити дані
- [ ] Оновити prompts-editor.html
- [ ] Видалити старі ресурси

### Після міграції:
- [ ] Налаштувати Remote State (S3)
- [ ] Додати secrets в .gitignore
- [ ] Видалити credentials з mcp-config.json
- [ ] Оновити README з Terraform інструкціями

---

## ❓ Питання для прийняття рішення

1. **Чи є критичні дані в DynamoDB?**
   - Так → Варіант 2 (Імпорт)
   - Ні → Варіант 3 (Новий)

2. **Чи плануєте активно розвивати проект?**
   - Так → Варіант 2 або 3 (Terraform)
   - Ні → Варіант 1 (БЕЗ Terraform)

3. **Чи можна мати downtime на 10-30 хвилин?**
   - Так → Варіант 3 (Новий)
   - Ні → Варіант 2 (Імпорт)

4. **Чи є досвід з Terraform?**
   - Так → Будь-який варіант
   - Ні → Варіант 1 або спочатку навчитись

---

**Що обрати?** Дайте знати яку опцію обираєте, і я допоможу з детальним планом!
