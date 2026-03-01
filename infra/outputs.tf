# ── Outputs ────────────────────────────────────────────────────────────────────

output "api_gateway_url" {
  description = "Base URL of the JobSys API"
  value       = "${aws_api_gateway_stage.prod.invoke_url}"
}

output "s3_bucket_name" {
  description = "S3 bucket for document storage"
  value       = aws_s3_bucket.storage.id
}

output "frontend_bucket_name" {
  description = "S3 bucket for frontend hosting"
  value       = aws_s3_bucket.frontend.id
}

output "frontend_website_url" {
  description = "Frontend website URL"
  value       = aws_s3_bucket_website_configuration.frontend.website_endpoint
}

output "jobs_table_name" {
  description = "DynamoDB jobs table name"
  value       = aws_dynamodb_table.jobs.name
}

output "config_table_name" {
  description = "DynamoDB config table name"
  value       = aws_dynamodb_table.config.name
}

output "token_usage_table_name" {
  description = "DynamoDB token usage table name"
  value       = aws_dynamodb_table.token_usage.name
}

output "job_scanner_function" {
  description = "Job Scanner Lambda function name"
  value       = aws_lambda_function.job_scanner.function_name
}

output "resume_matcher_function" {
  description = "Resume Matcher Lambda function name"
  value       = aws_lambda_function.resume_matcher.function_name
}

output "document_generator_function" {
  description = "Document Generator Lambda function name"
  value       = aws_lambda_function.document_generator.function_name
}

# ── LLM Config Outputs ────────────────────────────────────────────────────────

output "llm_provider_ssm_path" {
  description = "SSM path to update to switch LLM provider"
  value       = aws_ssm_parameter.llm_provider.name
}

output "llm_gemini_model_ssm_path" {
  description = "SSM path for Gemini model name"
  value       = aws_ssm_parameter.llm_gemini_model.name
}

output "llm_openai_model_ssm_path" {
  description = "SSM path for OpenAI model name"
  value       = aws_ssm_parameter.llm_openai_model.name
}

output "llm_hf_model_ssm_path" {
  description = "SSM path for HuggingFace model name"
  value       = aws_ssm_parameter.llm_hf_model.name
}

output "openai_secret_name" {
  description = "Secrets Manager secret name for OpenAI API key"
  value       = aws_secretsmanager_secret.openai_api_key.name
}

output "hf_secret_name" {
  description = "Secrets Manager secret name for HuggingFace API key"
  value       = aws_secretsmanager_secret.hf_api_key.name
}
