# 🚀 Terraform Quickstart для YouTube Content Automation

Швидкий старт для розгортання AWS інфраструктури за допомогою Terraform.

## ✅ Передумови

- [x] AWS Account
- [x] AWS CLI встановлено і налаштовано
- [x] Terraform >= 1.0 встановлено
- [x] OpenAI API Key

## 📦 Що буде створено

Terraform автоматично створить:

✅ **4 DynamoDB таблиці**: AIPromptConfigs, ChannelConfigs, GeneratedVideos, ContentQueue
✅ **7 Lambda функцій**: Get Channels, Theme Agent, Narrative, Select Topic, Query Titles, Save Result, Prompts API
✅ **1 Step Functions**: Content Generator workflow з retry логікою
✅ **IAM Roles & Policies**: З мінімальними необхідними правами
✅ **Secrets Manager**: Для OpenAI API Key
✅ **Lambda Function URL**: Публічний API для редагування промптів
✅ **EventBridge**: Щоденний автоматичний запуск о 10:00 AM UTC
✅ **CloudWatch Logs**: Для всіх сервісів з retention 7 днів

## 🎯 Quick Start (5 хвилин)

### 1. Налаштувати AWS Credentials

```bash
aws configure
# Введіть: Access Key ID, Secret Access Key, Region (eu-central-1)
```

### 2. Створити terraform.tfvars

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Відредагувати `terraform.tfvars` (можна через vim, nano, або notepad):

```hcl
aws_region     = "eu-central-1"
environment    = "prod"
project_name   = "youtube-content-automation"
openai_api_key = "sk-YOUR-OPENAI-API-KEY-HERE"  # 👈 Замінити на свій ключ!
notion_api_key = ""  # Опціонально
```

### 3. Розгорнути інфраструктуру

```bash
# Ініціалізація Terraform
terraform init

# Перевірити план (що буде створено)
terraform plan

# Розгорнути (займе ~2-3 хвилини)
terraform apply
```

Введіть `yes` для підтвердження.

### 4. Зберегти outputs

Після успішного apply, Terraform покаже важливу інформацію:

```
Outputs:

prompts_api_url = "https://abc123xyz.lambda-url.eu-central-1.on.aws"
step_functions_arn = "arn:aws:states:eu-central-1:123456789:stateMachine:youtube-content-automation-content-generator"

quick_commands = {
  "test_prompts_api" = "curl https://abc123xyz.lambda-url.eu-central-1.on.aws/prompts"
  "invoke_stepfunctions" = "aws stepfunctions start-execution --state-machine-arn arn:aws:..."
}
```

**Збережіть `prompts_api_url` для використання в prompts-editor.html!**

## 🧪 Тестування

### Перевірити Prompts API

```bash
# Отримати URL з outputs
PROMPTS_API_URL=$(terraform output -raw prompts_api_url)

# Список всіх агентів
curl "$PROMPTS_API_URL/prompts"

# Має повернути: {"agents": [...], "count": 2}
```

### Запустити Step Functions вручну

```bash
aws stepfunctions start-execution \
  --state-machine-arn $(terraform output -raw step_functions_arn) \
  --region eu-central-1
```

### Подивитися логи Lambda

```bash
# Theme Agent
aws logs tail /aws/lambda/youtube-content-automation-theme-agent --follow --region eu-central-1

# Narrative Architect
aws logs tail /aws/lambda/youtube-content-automation-narrative --follow --region eu-central-1
```

## 🔧 Оновлення коду Lambda

Якщо ви змінили код Lambda функцій:

```bash
cd terraform

# Terraform автоматично виявить зміни в Python коді
terraform apply
```

Terraform створить нові zip архіви і оновить Lambda функції.

## 🔐 Оновити OpenAI API Key

```bash
# Варіант 1: Через terraform.tfvars
vim terraform.tfvars  # Змінити openai_api_key
terraform apply

# Варіант 2: Безпосередньо в AWS Secrets Manager
aws secretsmanager update-secret \
  --secret-id youtube-content-automation/openai-api-key \
  --secret-string "sk-NEW-API-KEY" \
  --region eu-central-1
```

## 📊 Моніторинг

### CloudWatch Dashboard

```bash
# Відкрити CloudWatch Logs в браузері
open "https://eu-central-1.console.aws.amazon.com/cloudwatch/home?region=eu-central-1#logsV2:log-groups"
```

### Step Functions Console

```bash
# Відкрити Step Functions в браузері
terraform output step_functions_console_url
```

### DynamoDB Console

```bash
open "https://eu-central-1.console.aws.amazon.com/dynamodbv2/home?region=eu-central-1#tables"
```

## 💰 Вартість

При ~10,000 відео/місяць:

- DynamoDB (Pay-per-request): ~$2-3/міс
- Lambda (7 функцій): ~$1-2/міс
- Step Functions: ~$1/міс
- Secrets Manager: $0.40/міс
- CloudWatch Logs: ~$0.50/міс

**Загалом: $5-10/місяць**

## 🗑️ Видалення інфраструктури

⚠️ **УВАГА**: Це видалить ВСЕ, включно з даними в DynamoDB!

```bash
terraform destroy
```

Введіть `yes` для підтвердження.

Якщо хочете зберегти дані, спочатку експортуйте DynamoDB:

```bash
# Експорт DynamoDB перед видаленням
aws dynamodb scan --table-name AIPromptConfigs > backup-prompts.json
aws dynamodb scan --table-name ChannelConfigs > backup-channels.json
aws dynamodb scan --table-name GeneratedVideos > backup-videos.json
```

## 🐛 Troubleshooting

### Error: "Failed to create Lambda function"

```
Error: InvalidParameterValueException: The role defined for the function cannot be assumed by Lambda.
```

**Fix**: Просто запустіть ще раз (IAM role потребує часу для propagation):

```bash
terraform apply
```

### Error: "DynamoDB table already exists"

```
Error: ResourceInUseException: Table already exists: AIPromptConfigs
```

**Fix**: Імпортуйте існуючу таблицю:

```bash
terraform import aws_dynamodb_table.ai_prompt_configs AIPromptConfigs
terraform import aws_dynamodb_table.channel_configs ChannelConfigs
terraform import aws_dynamodb_table.generated_videos GeneratedVideos
terraform import aws_dynamodb_table.content_queue ContentQueue
```

### Lambda архів не оновлюється

```bash
# Видалити кеш
rm -rf .terraform/archives/

# Переапply
terraform apply
```

### Забув зберегти outputs

```bash
# Подивитися знову всі outputs
terraform output

# Конкретний output
terraform output prompts_api_url
terraform output -json quick_commands
```

## 📁 Наступні кроки

Після успішного розгортання:

1. **Оновити prompts-editor.html** - вставити новий `prompts_api_url`
2. **Додати Initial Data** - створити початкові AI Prompt конфіги
3. **Налаштувати Channels** - додати YouTube канали в ChannelConfigs
4. **Протестувати Workflow** - запустити Step Functions вручну
5. **Налаштувати Monitoring** - додати CloudWatch Alarms

## 📚 Детальна документація

Детальна документація в `terraform/README.md`:

- Архітектура рішення
- Опис кожного ресурсу
- Best practices для безпеки
- CI/CD інтеграція
- Додаткові налаштування

---

**Questions?** Створіть issue або перегляньте `terraform/README.md`.
