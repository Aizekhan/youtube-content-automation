# Terraform Outputs

# =====================================
# DynamoDB Tables
# =====================================
output "dynamodb_tables" {
  description = "DynamoDB таблиці"
  value = {
    ai_prompt_configs = aws_dynamodb_table.ai_prompt_configs.name
    channel_configs   = aws_dynamodb_table.channel_configs.name
    generated_videos  = aws_dynamodb_table.generated_videos.name
    content_queue     = aws_dynamodb_table.content_queue.name
  }
}

# =====================================
# Lambda Functions
# =====================================
output "lambda_functions" {
  description = "Lambda функції"
  value = {
    content_get_channels = aws_lambda_function.content_get_channels.function_name
    content_theme_agent  = aws_lambda_function.content_theme_agent.function_name
    content_narrative    = aws_lambda_function.content_narrative.function_name
    content_select_topic = aws_lambda_function.content_select_topic.function_name
    content_query_titles = aws_lambda_function.content_query_titles.function_name
    content_save_result  = aws_lambda_function.content_save_result.function_name
    prompts_api          = aws_lambda_function.prompts_api.function_name
  }
}

# =====================================
# Lambda Function URLs
# =====================================
output "prompts_api_url" {
  description = "URL для Prompts API"
  value       = aws_lambda_function_url.prompts_api.function_url
}

# =====================================
# Step Functions
# =====================================
output "step_functions_arn" {
  description = "ARN Step Functions State Machine"
  value       = aws_sfn_state_machine.content_generator.arn
}

output "step_functions_console_url" {
  description = "URL для Step Functions в AWS Console"
  value       = "https://${var.aws_region}.console.aws.amazon.com/states/home?region=${var.aws_region}#/statemachines/view/${aws_sfn_state_machine.content_generator.arn}"
}

# =====================================
# IAM Roles
# =====================================
output "lambda_execution_role_arn" {
  description = "ARN Lambda Execution Role"
  value       = aws_iam_role.lambda_execution_role.arn
}

output "stepfunctions_execution_role_arn" {
  description = "ARN Step Functions Execution Role"
  value       = aws_iam_role.stepfunctions_execution_role.arn
}

# =====================================
# Secrets Manager
# =====================================
output "openai_api_key_secret_arn" {
  description = "ARN секрету з OpenAI API Key"
  value       = aws_secretsmanager_secret.openai_api_key.arn
  sensitive   = true
}

# =====================================
# EventBridge Rule
# =====================================
output "eventbridge_rule_name" {
  description = "EventBridge Rule для автоматичного запуску"
  value       = aws_cloudwatch_event_rule.daily_content_generation.name
}

# =====================================
# Quick Commands
# =====================================
output "quick_commands" {
  description = "Корисні команди для роботи з інфраструктурою"
  value = {
    test_prompts_api      = "curl ${aws_lambda_function_url.prompts_api.function_url}/prompts"
    invoke_stepfunctions  = "aws stepfunctions start-execution --state-machine-arn ${aws_sfn_state_machine.content_generator.arn} --region ${var.aws_region}"
    view_stepfunctions    = "aws stepfunctions list-executions --state-machine-arn ${aws_sfn_state_machine.content_generator.arn} --region ${var.aws_region}"
    tail_lambda_logs      = "aws logs tail /aws/lambda/${aws_lambda_function.content_theme_agent.function_name} --follow --region ${var.aws_region}"
  }
}
