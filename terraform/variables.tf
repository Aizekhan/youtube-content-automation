variable "aws_region" {
  description = "AWS region для розгортання ресурсів"
  type        = string
  default     = "eu-central-1"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "project_name" {
  description = "Назва проекту"
  type        = string
  default     = "youtube-content-automation"
}

variable "openai_api_key" {
  description = "OpenAI API Key (зберігається в AWS Secrets Manager)"
  type        = string
  sensitive   = true
}

variable "notion_api_key" {
  description = "Notion API Key (опціонально)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "lambda_runtime" {
  description = "Python runtime для Lambda"
  type        = string
  default     = "python3.11"
}

variable "lambda_timeout" {
  description = "Lambda timeout в секундах"
  type        = number
  default     = 300
}

variable "lambda_memory" {
  description = "Lambda memory в MB"
  type        = number
  default     = 512
}
