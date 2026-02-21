# QUICK SYSTEM BACKUP
$BACKUP_DATE = Get-Date -Format "yyyyMMdd-HHmmss"
$BACKUP_DIR = "E:/youtube-automation-backups/backup-$BACKUP_DATE"

Write-Host "Starting backup to: $BACKUP_DIR"
New-Item -ItemType Directory -Force -Path "$BACKUP_DIR/dynamodb" | Out-Null
New-Item -ItemType Directory -Force -Path "$BACKUP_DIR/lambda" | Out-Null
New-Item -ItemType Directory -Force -Path "$BACKUP_DIR/stepfunctions" | Out-Null
New-Item -ItemType Directory -Force -Path "$BACKUP_DIR/s3" | Out-Null

# 1. DynamoDB Tables
Write-Host "`n1. Backing up DynamoDB tables..."
$tables = @("GeneratedContent", "ChannelConfigs", "CostTracking", "EC2InstanceLocks")
foreach ($table in $tables) {
    Write-Host "  - $table"
    aws dynamodb describe-table --table-name $table --region eu-central-1 > "$BACKUP_DIR/dynamodb/$table.json"
}

# 2. Lambda Functions
Write-Host "`n2. Backing up Lambda functions..."
aws lambda list-functions --region eu-central-1 > "$BACKUP_DIR/lambda/all-functions.json"

# 3. Step Functions
Write-Host "`n3. Backing up Step Functions..."
aws stepfunctions describe-state-machine `
    --state-machine-arn "arn:aws:states:eu-central-1:599297130956:stateMachine:ContentGenerator" `
    --region eu-central-1 > "$BACKUP_DIR/stepfunctions/ContentGenerator.json"

# 4. S3 Configs
Write-Host "`n4. Backing up S3 configurations..."
$buckets = @("youtube-automation-audio-files", "youtube-automation-images",
             "youtube-automation-final-videos", "youtube-automation-data-grucia")
foreach ($bucket in $buckets) {
    Write-Host "  - $bucket"
    aws s3api get-bucket-lifecycle-configuration --bucket $bucket 2>$null > "$BACKUP_DIR/s3/$bucket-lifecycle.json"
    aws s3api get-bucket-cors --bucket $bucket 2>$null > "$BACKUP_DIR/s3/$bucket-cors.json"
}

# 5. Save manifest
@"
Backup Date: $BACKUP_DATE
Region: eu-central-1
Tables: $($tables.Count)
Buckets: $($buckets.Count)
Location: $BACKUP_DIR
"@ > "$BACKUP_DIR/MANIFEST.txt"

Write-Host "`nBackup completed: $BACKUP_DIR" -ForegroundColor Green
