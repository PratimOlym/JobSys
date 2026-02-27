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
