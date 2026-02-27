terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = "production"
      ManagedBy   = "terraform"
      CostCenter  = "Engineering"
      Service     = "Job-Automation-System"
    }
  }
}

# Store the Gemini API key in Secrets Manager
resource "aws_secretsmanager_secret" "gemini_api_key" {
  name                    = "${var.project_name}/gemini-api-key"
  description             = "Google Gemini API key for JobSys"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "gemini_api_key" {
  secret_id     = aws_secretsmanager_secret.gemini_api_key.id
  secret_string = jsonencode({ api_key = var.gemini_api_key })

  lifecycle {
    ignore_changes = [secret_string]
  }
}
