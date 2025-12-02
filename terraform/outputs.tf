output "sns_topic_arn" {
  description = "ARN of SNS topic for alerts"
  value       = var.sns_alerts_arn
}

output "dynamodb_tables" {
  description = "DynamoDB table names"
  value = {
    generated_content = aws_dynamodb_table.generated_content.name
    channel_configs   = aws_dynamodb_table.channel_configs.name
    cost_tracking     = aws_dynamodb_table.cost_tracking.name
    ec2_locks         = aws_dynamodb_table.ec2_instance_locks.name
  }
}
