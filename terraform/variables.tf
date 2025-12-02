variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-central-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "sns_alerts_arn" {
  description = "SNS topic ARN for CloudWatch alerts"
  type        = string
  default     = "arn:aws:sns:eu-central-1:599297130956:youtube-automation-alerts"
}
