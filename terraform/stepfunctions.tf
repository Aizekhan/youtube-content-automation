# AWS Step Functions State Machine для генерації контенту

# =====================================
# Step Functions State Machine
# =====================================
resource "aws_sfn_state_machine" "content_generator" {
  name     = "${var.project_name}-content-generator"
  role_arn = aws_iam_role.stepfunctions_execution_role.arn

  definition = jsonencode({
    Comment = "YouTube Content Generation Workflow"
    StartAt = "GetActiveChannels"
    States = {
      # Step 1: Отримати активні канали
      GetActiveChannels = {
        Type     = "Task"
        Resource = aws_lambda_function.content_get_channels.arn
        Next     = "ProcessChannels"
        Catch = [
          {
            ErrorEquals = ["States.ALL"]
            Next        = "HandleError"
          }
        ]
      }

      # Step 2: Обробити кожен канал (Map state)
      ProcessChannels = {
        Type     = "Map"
        ItemsPath = "$"
        MaxConcurrency = 5
        Iterator = {
          StartAt = "QueryExistingTitles"
          States = {
            # Step 2.1: Перевірити існуючі назви відео
            QueryExistingTitles = {
              Type     = "Task"
              Resource = aws_lambda_function.content_query_titles.arn
              Next     = "GenerateTopics"
            }

            # Step 2.2: Згенерувати теми (Theme Agent)
            GenerateTopics = {
              Type     = "Task"
              Resource = aws_lambda_function.content_theme_agent.arn
              Next     = "SelectTopic"
              Retry = [
                {
                  ErrorEquals       = ["States.TaskFailed"]
                  IntervalSeconds   = 3
                  MaxAttempts       = 2
                  BackoffRate       = 2.0
                }
              ]
            }

            # Step 2.3: Вибрати тему
            SelectTopic = {
              Type     = "Task"
              Resource = aws_lambda_function.content_select_topic.arn
              Next     = "GenerateNarrative"
            }

            # Step 2.4: Згенерувати наратив (Narrative Architect)
            GenerateNarrative = {
              Type     = "Task"
              Resource = aws_lambda_function.content_narrative.arn
              Next     = "SaveResult"
              Retry = [
                {
                  ErrorEquals       = ["States.TaskFailed"]
                  IntervalSeconds   = 5
                  MaxAttempts       = 2
                  BackoffRate       = 2.0
                }
              ]
            }

            # Step 2.5: Зберегти результат
            SaveResult = {
              Type     = "Task"
              Resource = aws_lambda_function.content_save_result.arn
              End      = true
            }
          }
        }
        Next = "WorkflowComplete"
      }

      # Success state
      WorkflowComplete = {
        Type = "Succeed"
      }

      # Error handler
      HandleError = {
        Type = "Fail"
        Error = "WorkflowFailed"
        Cause = "An error occurred during content generation workflow"
      }
    }
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.stepfunctions_logs.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tags = {
    Name = "${var.project_name}-content-generator"
  }
}

# =====================================
# CloudWatch Log Group для Step Functions
# =====================================
resource "aws_cloudwatch_log_group" "stepfunctions_logs" {
  name              = "/aws/vendedlogs/states/${var.project_name}-content-generator"
  retention_in_days = 7

  tags = {
    Name = "${var.project_name}-stepfunctions-logs"
  }
}

# =====================================
# EventBridge Rule для автоматичного запуску (опціонально)
# =====================================
resource "aws_cloudwatch_event_rule" "daily_content_generation" {
  name                = "${var.project_name}-daily-content-generation"
  description         = "Trigger content generation daily at 10:00 AM UTC"
  schedule_expression = "cron(0 10 * * ? *)" # Щодня о 10:00 UTC

  tags = {
    Name = "${var.project_name}-daily-trigger"
  }
}

resource "aws_cloudwatch_event_target" "stepfunctions_target" {
  rule      = aws_cloudwatch_event_rule.daily_content_generation.name
  target_id = "StepFunctionsTarget"
  arn       = aws_sfn_state_machine.content_generator.arn
  role_arn  = aws_iam_role.eventbridge_stepfunctions_role.arn
}

# =====================================
# IAM Role для EventBridge → Step Functions
# =====================================
resource "aws_iam_role" "eventbridge_stepfunctions_role" {
  name = "${var.project_name}-eventbridge-stepfunctions-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-eventbridge-stepfunctions-role"
  }
}

resource "aws_iam_role_policy" "eventbridge_stepfunctions_policy" {
  name = "${var.project_name}-eventbridge-stepfunctions-policy"
  role = aws_iam_role.eventbridge_stepfunctions_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "states:StartExecution"
        ]
        Resource = aws_sfn_state_machine.content_generator.arn
      }
    ]
  })
}
