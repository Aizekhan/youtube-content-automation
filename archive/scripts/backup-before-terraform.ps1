# ПОВНИЙ БЕКАП СИСТЕМИ - Перед Terraform Migration
# Дата: 2025-12-02
# Мета: Snapshot всієї поточної інфраструктури

$BACKUP_DATE = Get-Date -Format "yyyyMMdd-HHmmss"
$BACKUP_DIR = "E:/youtube-automation-backups/pre-terraform-$BACKUP_DATE"

Write-Host "🔵 Starting full system backup..." -ForegroundColor Cyan
Write-Host "📁 Backup directory: $BACKUP_DIR" -ForegroundColor Yellow

# Створити структуру директорій
New-Item -ItemType Directory -Force -Path "$BACKUP_DIR/dynamodb"
New-Item -ItemType Directory -Force -Path "$BACKUP_DIR/lambda"
New-Item -ItemType Directory -Force -Path "$BACKUP_DIR/stepfunctions"
New-Item -ItemType Directory -Force -Path "$BACKUP_DIR/s3-configs"
New-Item -ItemType Directory -Force -Path "$BACKUP_DIR/iam"
New-Item -ItemType Directory -Force -Path "$BACKUP_DIR/cloudwatch"

Write-Host "`n=== 1. BACKING UP DYNAMODB TABLES ===" -ForegroundColor Green

$tables = @(
    "GeneratedContent",
    "ChannelConfigs",
    "CostTracking",
    "EC2InstanceLocks",
    "ThemeTemplates",
    "NarrativeTemplates",
    "TTSTemplates",
    "ImageGenerationTemplates",
    "CTATemplates",
    "DescriptionTemplates"
)

foreach ($table in $tables) {
    Write-Host "  📊 Backing up table: $table" -ForegroundColor Cyan

    # Table schema
    aws dynamodb describe-table `
        --table-name $table `
        --region eu-central-1 `
        --output json > "$BACKUP_DIR/dynamodb/$table-schema.json"

    # Table data (first 1000 items as sample)
    aws dynamodb scan `
        --table-name $table `
        --region eu-central-1 `
        --max-items 1000 `
        --output json > "$BACKUP_DIR/dynamodb/$table-data-sample.json"

    # Backup status
    aws dynamodb describe-continuous-backups `
        --table-name $table `
        --region eu-central-1 `
        --output json > "$BACKUP_DIR/dynamodb/$table-backup-status.json"

    Write-Host "    ✅ $table backed up" -ForegroundColor Green
}

Write-Host "`n=== 2. BACKING UP LAMBDA FUNCTIONS ===" -ForegroundColor Green

# Список всіх Lambda functions
$functions = aws lambda list-functions `
    --region eu-central-1 `
    --query 'Functions[*].FunctionName' `
    --output json | ConvertFrom-Json

Write-Host "  Found $($functions.Count) Lambda functions" -ForegroundColor Yellow

foreach ($func in $functions) {
    Write-Host "  ⚡ Backing up Lambda: $func" -ForegroundColor Cyan

    # Function configuration
    aws lambda get-function-configuration `
        --function-name $func `
        --region eu-central-1 `
        --output json > "$BACKUP_DIR/lambda/$func-config.json"

    # Function code URL (для завантаження якщо потрібно)
    aws lambda get-function `
        --function-name $func `
        --region eu-central-1 `
        --output json > "$BACKUP_DIR/lambda/$func-info.json"

    # Environment variables
    aws lambda get-function-configuration `
        --function-name $func `
        --region eu-central-1 `
        --query 'Environment' `
        --output json > "$BACKUP_DIR/lambda/$func-env.json"

    # IAM Role
    aws lambda get-function-configuration `
        --function-name $func `
        --region eu-central-1 `
        --query 'Role' `
        --output text > "$BACKUP_DIR/lambda/$func-role.txt"

    Write-Host "    ✅ $func backed up" -ForegroundColor Green
}

Write-Host "`n=== 3. BACKING UP STEP FUNCTIONS ===" -ForegroundColor Green

# Step Functions state machines
$stateMachines = aws stepfunctions list-state-machines `
    --region eu-central-1 `
    --query 'stateMachines[*].stateMachineArn' `
    --output json | ConvertFrom-Json

foreach ($sm in $stateMachines) {
    $smName = ($sm -split ':')[-1]
    Write-Host "  🔄 Backing up Step Function: $smName" -ForegroundColor Cyan

    # State machine definition
    aws stepfunctions describe-state-machine `
        --state-machine-arn $sm `
        --region eu-central-1 `
        --output json > "$BACKUP_DIR/stepfunctions/$smName-definition.json"

    # Execution history (last 10)
    aws stepfunctions list-executions `
        --state-machine-arn $sm `
        --region eu-central-1 `
        --max-results 10 `
        --output json > "$BACKUP_DIR/stepfunctions/$smName-recent-executions.json"

    Write-Host "    ✅ $smName backed up" -ForegroundColor Green
}

Write-Host "`n=== 4. BACKING UP S3 BUCKETS CONFIGURATION ===" -ForegroundColor Green

$buckets = @(
    "youtube-automation-audio-files",
    "youtube-automation-images",
    "youtube-automation-final-videos",
    "youtube-automation-data-grucia"
)

foreach ($bucket in $buckets) {
    Write-Host "  🪣 Backing up S3 config: $bucket" -ForegroundColor Cyan

    # Bucket policy
    aws s3api get-bucket-policy `
        --bucket $bucket `
        --output json 2>$null > "$BACKUP_DIR/s3-configs/$bucket-policy.json"

    # Lifecycle configuration
    aws s3api get-bucket-lifecycle-configuration `
        --bucket $bucket `
        --output json 2>$null > "$BACKUP_DIR/s3-configs/$bucket-lifecycle.json"

    # CORS configuration
    aws s3api get-bucket-cors `
        --bucket $bucket `
        --output json 2>$null > "$BACKUP_DIR/s3-configs/$bucket-cors.json"

    # Versioning
    aws s3api get-bucket-versioning `
        --bucket $bucket `
        --output json > "$BACKUP_DIR/s3-configs/$bucket-versioning.json"

    # Encryption
    aws s3api get-bucket-encryption `
        --bucket $bucket `
        --output json 2>$null > "$BACKUP_DIR/s3-configs/$bucket-encryption.json"

    Write-Host "    ✅ $bucket config backed up" -ForegroundColor Green
}

Write-Host "`n=== 5. BACKING UP IAM ROLES & POLICIES ===" -ForegroundColor Green

# IAM Roles для Lambda
foreach ($func in $functions) {
    $roleArn = Get-Content "$BACKUP_DIR/lambda/$func-role.txt"
    $roleName = ($roleArn -split '/')[-1]

    if ($roleName -and $roleName -ne "") {
        Write-Host "  🔐 Backing up IAM role: $roleName" -ForegroundColor Cyan

        # Role details
        aws iam get-role `
            --role-name $roleName `
            --output json 2>$null > "$BACKUP_DIR/iam/role-$roleName.json"

        # Attached policies
        aws iam list-attached-role-policies `
            --role-name $roleName `
            --output json 2>$null > "$BACKUP_DIR/iam/role-$roleName-attached-policies.json"

        # Inline policies
        aws iam list-role-policies `
            --role-name $roleName `
            --output json 2>$null > "$BACKUP_DIR/iam/role-$roleName-inline-policies.json"
    }
}

Write-Host "`n=== 6. BACKING UP CLOUDWATCH ALARMS ===" -ForegroundColor Green

# CloudWatch Alarms
aws cloudwatch describe-alarms `
    --region eu-central-1 `
    --output json > "$BACKUP_DIR/cloudwatch/alarms.json"

Write-Host "`n=== 7. BACKING UP SQS QUEUES ===" -ForegroundColor Green

# SQS Queues
$queues = aws sqs list-queues `
    --region eu-central-1 `
    --output json | ConvertFrom-Json

if ($queues.QueueUrls) {
    foreach ($queueUrl in $queues.QueueUrls) {
        $queueName = ($queueUrl -split '/')[-1]
        Write-Host "  📨 Backing up SQS: $queueName" -ForegroundColor Cyan

        # Queue attributes
        aws sqs get-queue-attributes `
            --queue-url $queueUrl `
            --attribute-names All `
            --region eu-central-1 `
            --output json > "$BACKUP_DIR/cloudwatch/sqs-$queueName.json"
    }
}

Write-Host "`n=== 8. BACKING UP EVENTBRIDGE RULES ===" -ForegroundColor Green

# EventBridge Rules
aws events list-rules `
    --region eu-central-1 `
    --output json > "$BACKUP_DIR/cloudwatch/eventbridge-rules.json"

Write-Host "`n=== 9. CREATING BACKUP MANIFEST ===" -ForegroundColor Green

# Створити manifest файл
$manifest = @{
    backup_date = $BACKUP_DATE
    backup_type = "pre-terraform-migration"
    region = "eu-central-1"
    tables_backed_up = $tables.Count
    lambdas_backed_up = $functions.Count
    s3_buckets = $buckets.Count
    backup_location = $BACKUP_DIR
    restore_instructions = "See RESTORE-INSTRUCTIONS.md"
}

$manifest | ConvertTo-Json | Out-File "$BACKUP_DIR/MANIFEST.json"

# Створити restore instructions
@"
# RESTORE INSTRUCTIONS
**Backup Date:** $BACKUP_DATE
**Backup Type:** Pre-Terraform Migration

## Як відновити систему з цього бекапу

### 1. DynamoDB Tables
``````powershell
# Відновити table з backup
aws dynamodb restore-table-from-backup \
    --target-table-name GeneratedContent \
    --backup-arn <arn-from-backup-status.json>

# АБО створити нову table зі schema
aws dynamodb create-table \
    --cli-input-json file://dynamodb/GeneratedContent-schema.json
``````

### 2. Lambda Functions
``````powershell
# Відновити Lambda code з URL
`$codeUrl = (Get-Content lambda/content-narrative-info.json | ConvertFrom-Json).Code.Location
Invoke-WebRequest -Uri `$codeUrl -OutFile content-narrative.zip

aws lambda update-function-code \
    --function-name content-narrative \
    --zip-file fileb://content-narrative.zip
``````

### 3. Step Functions
``````powershell
# Відновити state machine
`$definition = (Get-Content stepfunctions/ContentGenerator-definition.json | ConvertFrom-Json).definition

aws stepfunctions update-state-machine \
    --state-machine-arn <arn> \
    --definition `$definition
``````

### 4. S3 Buckets
``````powershell
# Відновити lifecycle policy
aws s3api put-bucket-lifecycle-configuration \
    --bucket youtube-automation-audio-files \
    --lifecycle-configuration file://s3-configs/youtube-automation-audio-files-lifecycle.json
``````

## Emergency Contact
- Backup location: $BACKUP_DIR
- Original system region: eu-central-1
- Backup includes: Full infrastructure snapshot
"@ | Out-File "$BACKUP_DIR/RESTORE-INSTRUCTIONS.md"

Write-Host "`n=== 10. COMPRESSING BACKUP ===" -ForegroundColor Green

# Compress backup (optional)
# Compress-Archive -Path $BACKUP_DIR -DestinationPath "$BACKUP_DIR.zip"

Write-Host "`n" -NoNewline
Write-Host "✅ BACKUP COMPLETED SUCCESSFULLY!" -ForegroundColor Green
Write-Host "`n📊 Backup Summary:" -ForegroundColor Yellow
Write-Host "  • DynamoDB tables: $($tables.Count)" -ForegroundColor White
Write-Host "  • Lambda functions: $($functions.Count)" -ForegroundColor White
Write-Host "  • S3 buckets: $($buckets.Count)" -ForegroundColor White
Write-Host "  • Location: $BACKUP_DIR" -ForegroundColor White
Write-Host "`n📝 See RESTORE-INSTRUCTIONS.md for recovery procedures" -ForegroundColor Cyan
Write-Host "`n🔒 This backup can restore your ENTIRE system if needed" -ForegroundColor Green
