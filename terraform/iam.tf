# IAM Roles & Policies для Lambda Functions

# =====================================
# Lambda Execution Role
# =====================================
resource "aws_iam_role" "lambda_execution_role" {
  name = "${var.project_name}-lambda-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-lambda-execution-role"
  }
}

# =====================================
# CloudWatch Logs Policy
# =====================================
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# =====================================
# DynamoDB Access Policy
# =====================================
resource "aws_iam_role_policy" "lambda_dynamodb_policy" {
  name = "${var.project_name}-lambda-dynamodb-policy"
  role = aws_iam_role.lambda_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan",
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem"
        ]
        Resource = [
          aws_dynamodb_table.ai_prompt_configs.arn,
          aws_dynamodb_table.channel_configs.arn,
          aws_dynamodb_table.generated_videos.arn,
          aws_dynamodb_table.content_queue.arn,
          "${aws_dynamodb_table.channel_configs.arn}/index/*",
          "${aws_dynamodb_table.generated_videos.arn}/index/*",
          "${aws_dynamodb_table.content_queue.arn}/index/*"
        ]
      }
    ]
  })
}

# =====================================
# Secrets Manager Policy (для всіх secrets)
# =====================================
resource "aws_iam_role_policy" "lambda_secrets_policy" {
  name = "${var.project_name}-lambda-secrets-policy"
  role = aws_iam_role.lambda_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = concat(
          [aws_secretsmanager_secret.openai_api_key.arn],
          var.notion_api_key != "" ? [aws_secretsmanager_secret.notion_integration[0].arn] : [],
          var.youtube_api_key != "" ? [aws_secretsmanager_secret.youtube_credentials[0].arn] : []
        )
      }
    ]
  })
}

# =====================================
# Step Functions Execution Role
# =====================================
resource "aws_iam_role" "stepfunctions_execution_role" {
  name = "${var.project_name}-stepfunctions-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-stepfunctions-execution-role"
  }
}

# =====================================
# Step Functions Lambda Invoke Policy
# =====================================
resource "aws_iam_role_policy" "stepfunctions_lambda_policy" {
  name = "${var.project_name}-stepfunctions-lambda-policy"
  role = aws_iam_role.stepfunctions_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          aws_lambda_function.content_get_channels.arn,
          aws_lambda_function.content_theme_agent.arn,
          aws_lambda_function.content_select_topic.arn,
          aws_lambda_function.content_narrative.arn,
          aws_lambda_function.content_query_titles.arn,
          aws_lambda_function.content_save_result.arn
        ]
      }
    ]
  })
}

# =====================================
# Step Functions CloudWatch Logs Policy
# =====================================
resource "aws_iam_role_policy" "stepfunctions_logs_policy" {
  name = "${var.project_name}-stepfunctions-logs-policy"
  role = aws_iam_role.stepfunctions_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:*"
      }
    ]
  })
}

# =====================================
# Secrets Manager - OpenAI API Key
# =====================================
resource "aws_secretsmanager_secret" "openai_api_key" {
  name        = "${var.project_name}/openai-api-key"
  description = "OpenAI API Key для AI агентів"

  tags = {
    Name = "${var.project_name}-openai-api-key"
  }
}

resource "aws_secretsmanager_secret_version" "openai_api_key" {
  secret_id     = aws_secretsmanager_secret.openai_api_key.id
  secret_string = var.openai_api_key
}

# =====================================
# Secrets Manager - Notion Integration (опціонально)
# =====================================
resource "aws_secretsmanager_secret" "notion_integration" {
  count       = var.notion_api_key != "" ? 1 : 0
  name        = "${var.project_name}/notion-integration"
  description = "Notion API credentials і database IDs"

  tags = {
    Name = "${var.project_name}-notion-integration"
  }
}

resource "aws_secretsmanager_secret_version" "notion_integration" {
  count     = var.notion_api_key != "" ? 1 : 0
  secret_id = aws_secretsmanager_secret.notion_integration[0].id
  secret_string = jsonencode({
    api_key           = var.notion_api_key
    tasks_database_id = var.notion_tasks_database_id
  })
}

# =====================================
# Secrets Manager - YouTube API (опціонально)
# =====================================
resource "aws_secretsmanager_secret" "youtube_credentials" {
  count       = var.youtube_api_key != "" ? 1 : 0
  name        = "${var.project_name}/youtube-credentials"
  description = "YouTube Data API credentials"

  tags = {
    Name = "${var.project_name}-youtube-credentials"
  }
}

resource "aws_secretsmanager_secret_version" "youtube_credentials" {
  count         = var.youtube_api_key != "" ? 1 : 0
  secret_id     = aws_secretsmanager_secret.youtube_credentials[0].id
  secret_string = var.youtube_api_key
}
