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

# ── Secrets Manager — API Keys ─────────────────────────────────────────────────
# Terraform creates the secret containers only.
# Set the actual values manually in the AWS Console (or via AWS CLI).
# All secret versions use lifecycle { ignore_changes = [secret_string] }
# so Terraform will never overwrite a value you have already set.

resource "aws_secretsmanager_secret" "gemini_api_key" {
  name                    = "${var.project_name}/gemini-api-key"
  description             = "Google Gemini API key for JobSys"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "gemini_api_key" {
  secret_id     = aws_secretsmanager_secret.gemini_api_key.id
  secret_string = jsonencode({ api_key = "PLACEHOLDER_SET_IN_CONSOLE" })

  lifecycle {
    ignore_changes = [secret_string]
  }
}

resource "aws_secretsmanager_secret" "openai_api_key" {
  name                    = "${var.project_name}/openai-api-key"
  description             = "OpenAI API key for JobSys"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "openai_api_key" {
  secret_id     = aws_secretsmanager_secret.openai_api_key.id
  secret_string = jsonencode({ api_key = "PLACEHOLDER_SET_IN_CONSOLE" })

  lifecycle {
    ignore_changes = [secret_string]
  }
}

resource "aws_secretsmanager_secret" "hf_api_key" {
  name                    = "${var.project_name}/hf-api-key"
  description             = "HuggingFace API key for JobSys"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "hf_api_key" {
  secret_id     = aws_secretsmanager_secret.hf_api_key.id
  secret_string = jsonencode({ api_key = "PLACEHOLDER_SET_IN_CONSOLE" })

  lifecycle {
    ignore_changes = [secret_string]
  }
}

# ── SSM Parameter Store — LLM Config ──────────────────────────────────────────
# Non-secret configuration: provider selection and model names.
# Set the values you want in the AWS Console — Terraform creates the parameters
# with defaults; lifecycle { ignore_changes = [value] } prevents overwriting.

resource "aws_ssm_parameter" "llm_provider" {
  name        = "/${var.project_name}/llm/provider"
  type        = "String"
  value       = "gemini"   # default; override in Console to switch providers
  description = "Active LLM provider: gemini | openai | huggingface"

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "llm_gemini_model" {
  name        = "/${var.project_name}/llm/gemini_model"
  type        = "String"
  value       = "gemini-2.0-flash"
  description = "Gemini model name used by JobSys"

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "llm_openai_model" {
  name        = "/${var.project_name}/llm/openai_model"
  type        = "String"
  value       = "gpt-4o-mini"
  description = "OpenAI model name used by JobSys"

  lifecycle {
    ignore_changes = [value]
  }
}

resource "aws_ssm_parameter" "llm_hf_model" {
  name        = "/${var.project_name}/llm/hf_model"
  type        = "String"
  value       = "mistralai/Mistral-7B-Instruct-v0.3"
  description = "HuggingFace model name used by JobSys"

  lifecycle {
    ignore_changes = [value]
  }
}
