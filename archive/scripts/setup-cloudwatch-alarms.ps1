$SNS_ARN = "arn:aws:sns:eu-central-1:599297130956:youtube-automation-alerts"

Write-Host "Setting up CloudWatch Alarms..." -ForegroundColor Cyan
Write-Host "SNS Topic: $SNS_ARN`n" -ForegroundColor Yellow

# ALARM 1: DLQ Messages
Write-Host "1. Creating DLQ Messages Alarm..." -ForegroundColor Cyan
aws cloudwatch put-metric-alarm `
    --alarm-name "DLQ-Messages-Alert" `
    --alarm-description "Alert when DLQ has messages (failed Lambda executions)" `
    --metric-name ApproximateNumberOfMessagesVisible `
    --namespace AWS/SQS `
    --statistic Sum `
    --period 300 `
    --threshold 0 `
    --comparison-operator GreaterThanThreshold `
    --evaluation-periods 1 `
    --alarm-actions $SNS_ARN `
    --dimensions Name=QueueName,Value=PendingImageGeneration-DLQ `
    --region eu-central-1

Write-Host "  SUCCESS: DLQ alarm created`n" -ForegroundColor Green

# ALARM 2: Daily Cost
Write-Host "2. Creating Daily Cost Alarm..." -ForegroundColor Cyan
aws cloudwatch put-metric-alarm `
    --alarm-name "Daily-Cost-High-Alert" `
    --alarm-description "Alert when daily AWS cost exceeds USD 50" `
    --metric-name EstimatedCharges `
    --namespace AWS/Billing `
    --statistic Maximum `
    --period 86400 `
    --threshold 50 `
    --comparison-operator GreaterThanThreshold `
    --evaluation-periods 1 `
    --alarm-actions $SNS_ARN `
    --dimensions Name=Currency,Value=USD `
    --region us-east-1

Write-Host "  SUCCESS: Daily cost alarm created`n" -ForegroundColor Green

# ALARM 3: Lambda Errors
Write-Host "3. Creating Lambda Errors Alarm..." -ForegroundColor Cyan
aws cloudwatch put-metric-alarm `
    --alarm-name "Lambda-Errors-High-Alert" `
    --alarm-description "Alert when Lambda error rate exceeds 5 percent" `
    --metric-name Errors `
    --namespace AWS/Lambda `
    --statistic Sum `
    --period 300 `
    --threshold 5 `
    --comparison-operator GreaterThanThreshold `
    --evaluation-periods 2 `
    --alarm-actions $SNS_ARN `
    --treat-missing-data notBreaching `
    --region eu-central-1

Write-Host "  SUCCESS: Lambda errors alarm created`n" -ForegroundColor Green

# ALARM 4: Step Functions Failures
Write-Host "4. Creating Step Functions Failures Alarm..." -ForegroundColor Cyan
aws cloudwatch put-metric-alarm `
    --alarm-name "StepFunctions-Failures-Alert" `
    --alarm-description "Alert when Step Functions executions fail" `
    --metric-name ExecutionsFailed `
    --namespace AWS/States `
    --statistic Sum `
    --period 300 `
    --threshold 1 `
    --comparison-operator GreaterThanOrEqualToThreshold `
    --evaluation-periods 1 `
    --alarm-actions $SNS_ARN `
    --dimensions Name=StateMachineArn,Value=arn:aws:states:eu-central-1:599297130956:stateMachine:ContentGenerator `
    --region eu-central-1

Write-Host "  SUCCESS: Step Functions failures alarm created`n" -ForegroundColor Green

Write-Host "All CloudWatch Alarms created successfully!" -ForegroundColor Green
Write-Host "`nAlarms will trigger SNS notifications to:" -ForegroundColor Yellow
Write-Host "  $SNS_ARN" -ForegroundColor White
Write-Host "`nTo receive notifications, subscribe to the SNS topic with email or other endpoints." -ForegroundColor Cyan
