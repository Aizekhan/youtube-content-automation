# Lambda Functions для YouTube Content Automation

# =====================================
# Lambda Layer для спільних залежностей (опціонально)
# =====================================
# resource "aws_lambda_layer_version" "dependencies" {
#   filename            = "../layers/dependencies.zip"
#   layer_name          = "${var.project_name}-dependencies"
#   compatible_runtimes = [var.lambda_runtime]
# }

# =====================================
# Lambda: content-get-channels
# =====================================
data "archive_file" "content_get_channels" {
  type        = "zip"
  source_dir  = "../aws/lambda/content-get-channels"
  output_path = "${path.module}/.terraform/archives/content-get-channels.zip"
}

resource "aws_lambda_function" "content_get_channels" {
  filename         = data.archive_file.content_get_channels.output_path
  function_name    = "${var.project_name}-get-channels"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory
  source_code_hash = data.archive_file.content_get_channels.output_base64sha256

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.channel_configs.name
      AWS_REGION     = var.aws_region
    }
  }

  tags = {
    Name = "content-get-channels"
  }
}

# =====================================
# Lambda: content-theme-agent
# =====================================
data "archive_file" "content_theme_agent" {
  type        = "zip"
  source_dir  = "../aws/lambda/content-theme-agent"
  output_path = "${path.module}/.terraform/archives/content-theme-agent.zip"
}

resource "aws_lambda_function" "content_theme_agent" {
  filename         = data.archive_file.content_theme_agent.output_path
  function_name    = "${var.project_name}-theme-agent"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory
  source_code_hash = data.archive_file.content_theme_agent.output_base64sha256

  environment {
    variables = {
      OPENAI_API_KEY_SECRET = aws_secretsmanager_secret.openai_api_key.name
      DYNAMODB_TABLE        = aws_dynamodb_table.ai_prompt_configs.name
      AWS_REGION            = var.aws_region
    }
  }

  tags = {
    Name = "content-theme-agent"
  }
}

# =====================================
# Lambda: content-narrative
# =====================================
data "archive_file" "content_narrative" {
  type        = "zip"
  source_dir  = "../aws/lambda/content-narrative"
  output_path = "${path.module}/.terraform/archives/content-narrative.zip"
}

resource "aws_lambda_function" "content_narrative" {
  filename         = data.archive_file.content_narrative.output_path
  function_name    = "${var.project_name}-narrative"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = 1024 # Більше пам'яті для Narrative Architect
  source_code_hash = data.archive_file.content_narrative.output_base64sha256

  environment {
    variables = {
      OPENAI_API_KEY_SECRET = aws_secretsmanager_secret.openai_api_key.name
      DYNAMODB_TABLE        = aws_dynamodb_table.ai_prompt_configs.name
      AWS_REGION            = var.aws_region
    }
  }

  tags = {
    Name = "content-narrative"
  }
}

# =====================================
# Lambda: content-select-topic
# =====================================
data "archive_file" "content_select_topic" {
  type        = "zip"
  source_dir  = "../aws/lambda/content-select-topic"
  output_path = "${path.module}/.terraform/archives/content-select-topic.zip"
}

resource "aws_lambda_function" "content_select_topic" {
  filename         = data.archive_file.content_select_topic.output_path
  function_name    = "${var.project_name}-select-topic"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = var.lambda_runtime
  timeout          = 60
  memory_size      = 256
  source_code_hash = data.archive_file.content_select_topic.output_base64sha256

  environment {
    variables = {
      AWS_REGION = var.aws_region
    }
  }

  tags = {
    Name = "content-select-topic"
  }
}

# =====================================
# Lambda: content-query-titles
# =====================================
data "archive_file" "content_query_titles" {
  type        = "zip"
  source_dir  = "../aws/lambda/content-query-titles"
  output_path = "${path.module}/.terraform/archives/content-query-titles.zip"
}

resource "aws_lambda_function" "content_query_titles" {
  filename         = data.archive_file.content_query_titles.output_path
  function_name    = "${var.project_name}-query-titles"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory
  source_code_hash = data.archive_file.content_query_titles.output_base64sha256

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.generated_videos.name
      AWS_REGION     = var.aws_region
    }
  }

  tags = {
    Name = "content-query-titles"
  }
}

# =====================================
# Lambda: content-save-result
# =====================================
data "archive_file" "content_save_result" {
  type        = "zip"
  source_dir  = "../aws/lambda/content-save-result"
  output_path = "${path.module}/.terraform/archives/content-save-result.zip"
}

resource "aws_lambda_function" "content_save_result" {
  filename         = data.archive_file.content_save_result.output_path
  function_name    = "${var.project_name}-save-result"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = var.lambda_runtime
  timeout          = 60
  memory_size      = 256
  source_code_hash = data.archive_file.content_save_result.output_base64sha256

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.generated_videos.name
      AWS_REGION     = var.aws_region
    }
  }

  tags = {
    Name = "content-save-result"
  }
}

# =====================================
# Lambda: prompts-api (з Function URL)
# =====================================
data "archive_file" "prompts_api" {
  type        = "zip"
  source_dir  = "../aws/lambda/prompts-api"
  output_path = "${path.module}/.terraform/archives/prompts-api.zip"
}

resource "aws_lambda_function" "prompts_api" {
  filename         = data.archive_file.prompts_api.output_path
  function_name    = "${var.project_name}-prompts-api"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = var.lambda_runtime
  timeout          = 30
  memory_size      = 256
  source_code_hash = data.archive_file.prompts_api.output_base64sha256

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.ai_prompt_configs.name
      AWS_REGION     = var.aws_region
    }
  }

  tags = {
    Name = "prompts-api"
  }
}

# Lambda Function URL для prompts-api
resource "aws_lambda_function_url" "prompts_api" {
  function_name      = aws_lambda_function.prompts_api.function_name
  authorization_type = "NONE" # Public access

  cors {
    allow_origins     = ["*"]
    allow_methods     = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    allow_headers     = ["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
    expose_headers    = ["Content-Type"]
    max_age           = 86400
  }
}

# =====================================
# CloudWatch Log Groups (автоматичне видалення старих логів)
# =====================================
resource "aws_cloudwatch_log_group" "lambda_logs" {
  for_each = {
    content_get_channels = aws_lambda_function.content_get_channels.function_name
    content_theme_agent  = aws_lambda_function.content_theme_agent.function_name
    content_narrative    = aws_lambda_function.content_narrative.function_name
    content_select_topic = aws_lambda_function.content_select_topic.function_name
    content_query_titles = aws_lambda_function.content_query_titles.function_name
    content_save_result  = aws_lambda_function.content_save_result.function_name
    prompts_api          = aws_lambda_function.prompts_api.function_name
  }

  name              = "/aws/lambda/${each.value}"
  retention_in_days = 7 # Зберігати логи 7 днів

  tags = {
    Name = "${each.value}-logs"
  }
}
