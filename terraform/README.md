# Terraform Infrastructure для YouTube Content Automation

Ця Terraform конфігурація розгортає всю AWS інфраструктуру для автоматизації створення YouTube контенту.

## 📋 Що розгортається

### DynamoDB Tables
- **AIPromptConfigs** - конфігурації AI агентів (Theme Agent, Narrative Architect)
- **ChannelConfigs** - налаштування YouTube каналів з GSI по channel_id
- **GeneratedVideos** - зберігання згенерованих відео з GSI по channel_id та status
- **ContentQueue** - черга завдань для генерації з TTL

### Lambda Functions
- **content-get-channels** - отримання активних каналів
- **content-theme-agent** - генерація тем відео (OpenAI GPT-4)
- **content-narrative** - генерація наративу (OpenAI GPT-4)
- **content-select-topic** - вибір теми з варіантів
- **content-query-titles** - перевірка існуючих назв
- **content-save-result** - збереження результату в DynamoDB
- **prompts-api** - CRUD API для AIPromptConfigs з Lambda Function URL

### Step Functions
- **content-generator** - State Machine для оркестрації генерації контенту
  - Map state для паралельної обробки каналів
  - Retry логіка для AI викликів
  - Error handling

### IAM
- Lambda Execution Role з доступом до DynamoDB, Secrets Manager, CloudWatch
- Step Functions Execution Role з правами на invoke Lambda
- EventBridge Role для запуску Step Functions

### Secrets Manager
- OpenAI API Key
- Notion API Key (опціонально)

### EventBridge
- Daily trigger для автоматичного запуску (cron: 10:00 AM UTC)

### CloudWatch
- Log Groups для всіх Lambda функцій (retention: 7 днів)
- Log Group для Step Functions

## 🚀 Швидкий старт

### 1. Встановити Terraform

```bash
# Windows (через Chocolatey)
choco install terraform

# macOS (через Homebrew)
brew install terraform

# Linux
wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
unzip terraform_1.6.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/
```

### 2. Налаштувати AWS Credentials

```bash
# Опція 1: AWS CLI
aws configure

# Опція 2: Environment Variables
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="eu-central-1"
```

### 3. Створити terraform.tfvars

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Відредагувати `terraform.tfvars`:

```hcl
aws_region     = "eu-central-1"
environment    = "prod"
project_name   = "youtube-content-automation"
openai_api_key = "sk-your-openai-api-key"
```

### 4. Ініціалізувати Terraform

```bash
terraform init
```

### 5. Подивитися план змін

```bash
terraform plan
```

### 6. Розгорнути інфраструктуру

```bash
terraform apply
```

Підтвердіть: `yes`

## 📊 Outputs

Після успішного `terraform apply` ви побачите:

```
Outputs:

dynamodb_tables = {
  "ai_prompt_configs" = "AIPromptConfigs"
  "channel_configs" = "ChannelConfigs"
  "generated_videos" = "GeneratedVideos"
  "content_queue" = "ContentQueue"
}

lambda_functions = {
  "content_get_channels" = "youtube-content-automation-get-channels"
  "content_theme_agent" = "youtube-content-automation-theme-agent"
  ...
}

prompts_api_url = "https://abc123.lambda-url.eu-central-1.on.aws"

step_functions_arn = "arn:aws:states:eu-central-1:123456789:stateMachine:youtube-content-automation-content-generator"

quick_commands = {
  "invoke_stepfunctions" = "aws stepfunctions start-execution --state-machine-arn ..."
  "test_prompts_api" = "curl https://abc123.lambda-url.eu-central-1.on.aws/prompts"
  "tail_lambda_logs" = "aws logs tail /aws/lambda/... --follow"
}
```

## 🧪 Тестування

### 1. Протестувати Prompts API

```bash
# List all agents
curl https://YOUR_FUNCTION_URL/prompts

# Get specific agent
curl https://YOUR_FUNCTION_URL/prompts/theme_agent

# Update agent
curl -X PUT https://YOUR_FUNCTION_URL/prompts/theme_agent \
  -H "Content-Type: application/json" \
  -d '{"system_instructions": "New instructions...", "temperature": "0.9"}'
```

### 2. Запустити Step Functions вручну

```bash
aws stepfunctions start-execution \
  --state-machine-arn $(terraform output -raw step_functions_arn) \
  --region eu-central-1
```

### 3. Подивитися логи Lambda

```bash
# Theme Agent
aws logs tail /aws/lambda/youtube-content-automation-theme-agent --follow

# Narrative Architect
aws logs tail /aws/lambda/youtube-content-automation-narrative --follow
```

### 4. Перевірити DynamoDB

```bash
# Scan AIPromptConfigs
aws dynamodb scan --table-name AIPromptConfigs --region eu-central-1

# Get specific agent
aws dynamodb get-item \
  --table-name AIPromptConfigs \
  --key '{"agent_id": {"S": "theme_agent"}}' \
  --region eu-central-1
```

## 🔧 Управління інфраструктурою

### Оновлення конфігурації

```bash
# Змінити variables.tf або *.tf файли
vim lambda.tf

# Подивитися зміни
terraform plan

# Застосувати зміни
terraform apply
```

### Оновлення Lambda функцій

```bash
# Terraform автоматично виявить зміни в коді Lambda
# і оновить функції при apply

terraform apply
```

### Видалити всю інфраструктуру

```bash
terraform destroy
```

⚠️ **УВАГА**: Це видалить ВСІ ресурси, включно з DynamoDB таблицями!

## 📁 Структура файлів

```
terraform/
├── main.tf              # Provider & backend configuration
├── variables.tf         # Input variables
├── outputs.tf           # Output values
├── dynamodb.tf          # DynamoDB tables
├── lambda.tf            # Lambda functions
├── iam.tf               # IAM roles & policies
├── stepfunctions.tf     # Step Functions state machine
├── terraform.tfvars.example  # Example variables
├── .gitignore           # Git ignore
└── README.md            # Ця документація
```

## 🔐 Безпека

### Secrets Management

Terraform зберігає `openai_api_key` в AWS Secrets Manager, а НЕ в terraform.tfstate як plaintext.

Lambda функції отримують ключ через Secrets Manager ARN:

```python
import boto3
secrets_client = boto3.client('secretsmanager')
secret_name = os.environ['OPENAI_API_KEY_SECRET']
response = secrets_client.get_secret_value(SecretId=secret_name)
api_key = response['SecretString']
```

### IAM Best Practices

- Кожна Lambda має мінімальні необхідні права (Principle of Least Privilege)
- Lambda може читати тільки свої DynamoDB таблиці
- Step Functions може викликати тільки свої Lambda функції
- CloudWatch Logs мають retention period (7 днів)

### Sensitive Outputs

```bash
# Outputs з sensitive=true не показуються в terraform apply
terraform output openai_api_key_secret_arn
```

## 💰 Оцінка вартості

### Pay-per-request (поточна конфігурація)

- **DynamoDB**: $1.25 за 1M write requests, $0.25 за 1M read requests
- **Lambda**: $0.20 за 1M requests + $0.0000166667 за GB-second
- **Step Functions**: $25 за 1M state transitions
- **Secrets Manager**: $0.40 за секрет/місяць

**Приклад**: 10,000 відео/місяць = ~$5-10/місяць

### Provisioned (для високого навантаження)

Змініть `billing_mode` в `dynamodb.tf`:

```hcl
billing_mode = "PROVISIONED"
read_capacity  = 5
write_capacity = 5
```

## 🔄 CI/CD Integration

### GitHub Actions

Додайте в `.github/workflows/terraform.yml`:

```yaml
name: Terraform

on:
  push:
    branches:
      - master
    paths:
      - 'terraform/**'
      - 'aws/lambda/**'

jobs:
  terraform:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3

      - name: Terraform Init
        run: terraform init
        working-directory: ./terraform

      - name: Terraform Plan
        run: terraform plan
        working-directory: ./terraform
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          TF_VAR_openai_api_key: ${{ secrets.OPENAI_API_KEY }}

      - name: Terraform Apply
        if: github.ref == 'refs/heads/master'
        run: terraform apply -auto-approve
        working-directory: ./terraform
```

## 🐛 Troubleshooting

### Error: Failed to create Lambda function

```
Error: error creating Lambda Function: InvalidParameterValueException:
The role defined for the function cannot be assumed by Lambda.
```

**Fix**: Почекайте 10 секунд після створення IAM role і спробуйте знову:

```bash
terraform apply
```

### Error: DynamoDB table already exists

```
Error: error creating DynamoDB Table: ResourceInUseException:
Table already exists: AIPromptConfigs
```

**Fix**: Імпортуйте існуючу таблицю:

```bash
terraform import aws_dynamodb_table.ai_prompt_configs AIPromptConfigs
```

### Lambda архів не оновлюється

```bash
# Видалити кеш
rm -rf .terraform/archives/

# Re-apply
terraform apply
```

## 📚 Додаткові ресурси

- [Terraform AWS Provider Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)
- [Step Functions Best Practices](https://docs.aws.amazon.com/step-functions/latest/dg/sfn-best-practices.html)

## 📝 TODO

- [ ] Додати S3 bucket для зберігання згенерованих відео
- [ ] Додати CloudFront distribution для website
- [ ] Додати API Gateway замість Lambda Function URL для кращого контролю
- [ ] Додати WAF rules для захисту API
- [ ] Налаштувати Remote State в S3 + DynamoDB lock table
- [ ] Додати Terraform workspaces для dev/staging/prod
- [ ] Додати automated backups для DynamoDB
- [ ] Додати CloudWatch Alarms для моніторингу

## 🤝 Contributing

Якщо ви хочете внести зміни в Terraform конфігурацію:

1. Створіть нову гілку
2. Внесіть зміни
3. Запустіть `terraform fmt` для форматування
4. Запустіть `terraform validate` для валідації
5. Створіть Pull Request

---

**Generated with ❤️ by Terraform**
