terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }

  # Опціонально: Remote state в S3
  # backend "s3" {
  #   bucket         = "youtube-automation-terraform-state"
  #   key            = "terraform.tfstate"
  #   region         = "eu-central-1"
  #   encrypt        = true
  #   dynamodb_table = "terraform-state-lock"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "youtube-content-automation"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
