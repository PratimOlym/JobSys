variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Project name prefix for all resources"
  type        = string
  default     = "jobsys"
}

variable "s3_bucket_name" {
  description = "Name of the S3 bucket for document storage"
  type        = string
  default     = "jobsys-storage"
}

variable "gemini_api_key" {
  description = "Google Gemini API key (stored in Secrets Manager)"
  type        = string
  sensitive   = true
  default     = "PLACEHOLDER"
}

variable "lambda_timeout" {
  description = "Default Lambda timeout in seconds"
  type        = number
  default     = 300
}

variable "lambda_memory" {
  description = "Default Lambda memory in MB"
  type        = number
  default     = 512
}

variable "schedule_expression" {
  description = "EventBridge schedule for the daily job scan"
  type        = string
  default     = "cron(0 19 * * ? *)"  # 1 AM IST = 7:30 PM UTC (previous day)
}

variable "frontend_domain" {
  description = "Custom domain for the frontend (optional)"
  type        = string
  default     = ""
}
