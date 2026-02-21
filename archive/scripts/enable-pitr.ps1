$tables = @(
    "GeneratedContent",
    "ChannelConfigs",
    "CostTracking",
    "EC2InstanceLocks"
)

foreach ($table in $tables) {
    Write-Host "Enabling PITR for $table..." -ForegroundColor Cyan
    aws dynamodb update-continuous-backups `
        --table-name $table `
        --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true `
        --region eu-central-1

    if ($LASTEXITCODE -eq 0) {
        Write-Host "  SUCCESS: PITR enabled for $table" -ForegroundColor Green
    } else {
        Write-Host "  ERROR for $table" -ForegroundColor Red
    }
}

Write-Host "`nPITR enabled for all tables!" -ForegroundColor Green
