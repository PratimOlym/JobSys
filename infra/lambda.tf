# ── Lambda Functions ───────────────────────────────────────────────────────────

# Shared environment variables for all Lambdas
locals {
  lambda_env_vars = {
    JOBS_TABLE_NAME          = aws_dynamodb_table.jobs.name
    CONFIG_TABLE_NAME        = aws_dynamodb_table.config.name
    TOKEN_USAGE_TABLE_NAME   = aws_dynamodb_table.token_usage.name
    S3_BUCKET_NAME           = aws_s3_bucket.storage.id
    GEMINI_API_KEY_SECRET    = aws_secretsmanager_secret.gemini_api_key.name
    OPENAI_API_KEY_SECRET    = aws_secretsmanager_secret.openai_api_key.name
    HF_API_KEY_SECRET        = aws_secretsmanager_secret.hf_api_key.name
    SSM_LLM_PROVIDER         = aws_ssm_parameter.llm_provider.name
    SSM_GEMINI_MODEL         = aws_ssm_parameter.llm_gemini_model.name
    SSM_OPENAI_MODEL         = aws_ssm_parameter.llm_openai_model.name
    SSM_HF_MODEL             = aws_ssm_parameter.llm_hf_model.name
    RESUME_MATCHER_FUNCTION  = "${var.project_name}-resume-matcher"
    DOC_GENERATOR_FUNCTION   = "${var.project_name}-document-generator"
    JOB_SCANNER_FUNCTION     = "${var.project_name}-job-scanner"
    AWS_REGION_NAME          = var.aws_region
  }
}

# ── Lambda Layer (shared dependencies) ─────────────────────────────────────────

resource "aws_lambda_layer_version" "dependencies" {
  s3_bucket           = aws_s3_bucket.storage.id
  s3_key              = aws_s3_object.layer_zip.key
  layer_name          = "${var.project_name}-dependencies"
  compatible_runtimes = ["python3.10", "python3.11", "python3.12"]
  description         = "Shared Python dependencies for JobSys Lambdas"
  source_code_hash    = filebase64sha256("${path.module}/../backend/layer.zip")
}

# ── Job Scanner Lambda ─────────────────────────────────────────────────────────

resource "aws_lambda_function" "job_scanner" {
  filename         = "${path.module}/../backend/job_scanner.zip"
  function_name    = "${var.project_name}-job-scanner"
  role             = aws_iam_role.lambda_role.arn
  handler          = "job_scanner.handler.handler"
  runtime          = "python3.11"
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory
  source_code_hash = filebase64sha256("${path.module}/../backend/job_scanner.zip")

  layers = [aws_lambda_layer_version.dependencies.arn]

  environment {
    variables = local.lambda_env_vars
  }

  tags = {
    Name = "${var.project_name}-job-scanner"
  }
}

# ── Resume Matcher Lambda ──────────────────────────────────────────────────────

resource "aws_lambda_function" "resume_matcher" {
  filename         = "${path.module}/../backend/resume_matcher.zip"
  function_name    = "${var.project_name}-resume-matcher"
  role             = aws_iam_role.lambda_role.arn
  handler          = "resume_matcher.handler.handler"
  runtime          = "python3.11"
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory
  source_code_hash = filebase64sha256("${path.module}/../backend/resume_matcher.zip")

  layers = [aws_lambda_layer_version.dependencies.arn]

  environment {
    variables = local.lambda_env_vars
  }

  tags = {
    Name = "${var.project_name}-resume-matcher"
  }
}

# ── Document Generator Lambda ──────────────────────────────────────────────────

resource "aws_lambda_function" "document_generator" {
  filename         = "${path.module}/../backend/document_generator.zip"
  function_name    = "${var.project_name}-document-generator"
  role             = aws_iam_role.lambda_role.arn
  handler          = "document_generator.handler.handler"
  runtime          = "python3.11"
  timeout          = var.lambda_timeout
  memory_size      = 1024  # More memory for DOCX generation
  source_code_hash = filebase64sha256("${path.module}/../backend/document_generator.zip")

  layers = [aws_lambda_layer_version.dependencies.arn]

  environment {
    variables = local.lambda_env_vars
  }

  tags = {
    Name = "${var.project_name}-document-generator"
  }
}

# ── API Handler Lambda ─────────────────────────────────────────────────────────

resource "aws_lambda_function" "api_handler" {
  filename         = "${path.module}/../backend/api_handler.zip"
  function_name    = "${var.project_name}-api-handler"
  role             = aws_iam_role.lambda_role.arn
  handler          = "api_handler.handler.handler"
  runtime          = "python3.11"
  timeout          = 30
  memory_size      = 256
  source_code_hash = filebase64sha256("${path.module}/../backend/api_handler.zip")

  layers = [aws_lambda_layer_version.dependencies.arn]

  environment {
    variables = local.lambda_env_vars
  }

  tags = {
    Name = "${var.project_name}-api-handler"
  }
}
