# ── API Gateway (REST API) ─────────────────────────────────────────────────────

resource "aws_api_gateway_rest_api" "api" {
  name        = "${var.project_name}-api"
  description = "JobSys Dashboard REST API"

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

# ── /jobs resource ─────────────────────────────────────────────────────────────

resource "aws_api_gateway_resource" "jobs" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "jobs"
}

# GET /jobs
resource "aws_api_gateway_method" "get_jobs" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.jobs.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "get_jobs" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.jobs.id
  http_method             = aws_api_gateway_method.get_jobs.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api_handler.invoke_arn
}

# ── /jobs/scan resource ────────────────────────────────────────────────────────

resource "aws_api_gateway_resource" "jobs_scan" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.jobs.id
  path_part   = "scan"
}

# POST /jobs/scan
resource "aws_api_gateway_method" "post_jobs_scan" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.jobs_scan.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "post_jobs_scan" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.jobs_scan.id
  http_method             = aws_api_gateway_method.post_jobs_scan.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api_handler.invoke_arn
}

# ── /jobs/{id} resource ────────────────────────────────────────────────────────

resource "aws_api_gateway_resource" "job_by_id" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.jobs.id
  path_part   = "{id}"
}

# GET /jobs/{id}
resource "aws_api_gateway_method" "get_job_by_id" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.job_by_id.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "get_job_by_id" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.job_by_id.id
  http_method             = aws_api_gateway_method.get_job_by_id.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api_handler.invoke_arn
}

# ── /jobs/{id}/regenerate resource ─────────────────────────────────────────────

resource "aws_api_gateway_resource" "job_regenerate" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.job_by_id.id
  path_part   = "regenerate"
}

# POST /jobs/{id}/regenerate
resource "aws_api_gateway_method" "post_job_regenerate" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.job_regenerate.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "post_job_regenerate" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.job_regenerate.id
  http_method             = aws_api_gateway_method.post_job_regenerate.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api_handler.invoke_arn
}

# ── /config resource ──────────────────────────────────────────────────────────

resource "aws_api_gateway_resource" "config" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "config"
}

# GET /config
resource "aws_api_gateway_method" "get_config" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.config.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "get_config" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.config.id
  http_method             = aws_api_gateway_method.get_config.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api_handler.invoke_arn
}

# PUT /config
resource "aws_api_gateway_method" "put_config" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.config.id
  http_method   = "PUT"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "put_config" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.config.id
  http_method             = aws_api_gateway_method.put_config.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api_handler.invoke_arn
}

# ── /dashboard/stats resource ─────────────────────────────────────────────────

resource "aws_api_gateway_resource" "dashboard" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "dashboard"
}

resource "aws_api_gateway_resource" "dashboard_stats" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.dashboard.id
  path_part   = "stats"
}

# GET /dashboard/stats
resource "aws_api_gateway_method" "get_dashboard_stats" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.dashboard_stats.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "get_dashboard_stats" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.dashboard_stats.id
  http_method             = aws_api_gateway_method.get_dashboard_stats.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api_handler.invoke_arn
}

# ── /resumes resource ─────────────────────────────────────────────────────────

resource "aws_api_gateway_resource" "resumes" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "resumes"
}

# GET /resumes
resource "aws_api_gateway_method" "get_resumes" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.resumes.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "get_resumes" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.resumes.id
  http_method             = aws_api_gateway_method.get_resumes.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api_handler.invoke_arn
}

# POST /resumes
resource "aws_api_gateway_method" "post_resumes" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.resumes.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "post_resumes" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.resumes.id
  http_method             = aws_api_gateway_method.post_resumes.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api_handler.invoke_arn
}

# DELETE /resumes
resource "aws_api_gateway_method" "delete_resumes" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.resumes.id
  http_method   = "DELETE"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "delete_resumes" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.resumes.id
  http_method             = aws_api_gateway_method.delete_resumes.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api_handler.invoke_arn
}

# ── /resumes/summarize ──
resource "aws_api_gateway_resource" "resumes_summarize" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.resumes.id
  path_part   = "summarize"
}

resource "aws_api_gateway_method" "post_resumes_summarize" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.resumes_summarize.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "post_resumes_summarize" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.resumes_summarize.id
  http_method             = aws_api_gateway_method.post_resumes_summarize.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api_handler.invoke_arn
}

# ── /resumes/summaries ──
resource "aws_api_gateway_resource" "resumes_summaries" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.resumes.id
  path_part   = "summaries"
}

resource "aws_api_gateway_method" "get_resumes_summaries" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.resumes_summaries.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "get_resumes_summaries" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.resumes_summaries.id
  http_method             = aws_api_gateway_method.get_resumes_summaries.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api_handler.invoke_arn
}

# ── /resumes/match ──
resource "aws_api_gateway_resource" "resumes_match" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.resumes.id
  path_part   = "match"
}

resource "aws_api_gateway_method" "post_resumes_match" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.resumes_match.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "post_resumes_match" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.resumes_match.id
  http_method             = aws_api_gateway_method.post_resumes_match.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api_handler.invoke_arn
}

# ── /documents/{path+} resource ───────────────────────────────────────────────

resource "aws_api_gateway_resource" "documents" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_rest_api.api.root_resource_id
  path_part   = "documents"
}

resource "aws_api_gateway_resource" "documents_proxy" {
  rest_api_id = aws_api_gateway_rest_api.api.id
  parent_id   = aws_api_gateway_resource.documents.id
  path_part   = "{path+}"
}

# GET /documents/{path+}
resource "aws_api_gateway_method" "get_document" {
  rest_api_id   = aws_api_gateway_rest_api.api.id
  resource_id   = aws_api_gateway_resource.documents_proxy.id
  http_method   = "GET"
  authorization = "NONE"

  request_parameters = {
    "method.request.path.path" = true
  }
}

resource "aws_api_gateway_integration" "get_document" {
  rest_api_id             = aws_api_gateway_rest_api.api.id
  resource_id             = aws_api_gateway_resource.documents_proxy.id
  http_method             = aws_api_gateway_method.get_document.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.api_handler.invoke_arn
}

# ── CORS (OPTIONS) for all resources ──────────────────────────────────────────

module "cors_jobs" {
  source      = "./modules/cors"
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.jobs.id
}

module "cors_job_by_id" {
  source      = "./modules/cors"
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.job_by_id.id
}

module "cors_config" {
  source      = "./modules/cors"
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.config.id
}

module "cors_dashboard_stats" {
  source      = "./modules/cors"
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.dashboard_stats.id
}

module "cors_jobs_scan" {
  source      = "./modules/cors"
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.jobs_scan.id
}

module "cors_job_regenerate" {
  source      = "./modules/cors"
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.job_regenerate.id
}

module "cors_resumes" {
  source      = "./modules/cors"
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.resumes.id
}

module "cors_resumes_summarize" {
  source      = "./modules/cors"
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.resumes_summarize.id
}

module "cors_resumes_summaries" {
  source      = "./modules/cors"
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.resumes_summaries.id
}

module "cors_resumes_match" {
  source      = "./modules/cors"
  rest_api_id = aws_api_gateway_rest_api.api.id
  resource_id = aws_api_gateway_resource.resumes_match.id
}

# ── Deployment ─────────────────────────────────────────────────────────────────

resource "aws_api_gateway_deployment" "api" {
  depends_on = [
    aws_api_gateway_integration.get_jobs,
    aws_api_gateway_integration.get_job_by_id,
    aws_api_gateway_integration.post_jobs_scan,
    aws_api_gateway_integration.post_job_regenerate,
    aws_api_gateway_integration.get_config,
    aws_api_gateway_integration.put_config,
    aws_api_gateway_integration.get_dashboard_stats,
    aws_api_gateway_integration.get_document,
    aws_api_gateway_integration.get_resumes,
    aws_api_gateway_integration.post_resumes,
    aws_api_gateway_integration.delete_resumes,
    aws_api_gateway_integration.post_resumes_summarize,
    aws_api_gateway_integration.get_resumes_summaries,
    aws_api_gateway_integration.post_resumes_match,
  ]

  rest_api_id = aws_api_gateway_rest_api.api.id

  triggers = {
    redeployment = sha1(join(",", [
      jsonencode(aws_api_gateway_integration.get_jobs),
      jsonencode(aws_api_gateway_integration.get_job_by_id),
      jsonencode(aws_api_gateway_integration.post_jobs_scan),
      jsonencode(aws_api_gateway_integration.post_job_regenerate),
      jsonencode(aws_api_gateway_integration.get_config),
      jsonencode(aws_api_gateway_integration.put_config),
      jsonencode(aws_api_gateway_integration.get_dashboard_stats),
      jsonencode(aws_api_gateway_integration.get_document),
      jsonencode(aws_api_gateway_integration.get_resumes),
      jsonencode(aws_api_gateway_integration.post_resumes),
      jsonencode(aws_api_gateway_integration.delete_resumes),
      jsonencode(aws_api_gateway_integration.post_resumes_summarize),
      jsonencode(aws_api_gateway_integration.get_resumes_summaries),
      jsonencode(aws_api_gateway_integration.post_resumes_match),
      # CORS
      jsonencode(module.cors_jobs),
      jsonencode(module.cors_job_by_id),
      jsonencode(module.cors_config),
      jsonencode(module.cors_dashboard_stats),
      jsonencode(module.cors_jobs_scan),
      jsonencode(module.cors_job_regenerate),
      jsonencode(module.cors_resumes),
      jsonencode(module.cors_resumes_summarize),
      jsonencode(module.cors_resumes_summaries),
      jsonencode(module.cors_resumes_match),
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "prod" {
  deployment_id = aws_api_gateway_deployment.api.id
  rest_api_id   = aws_api_gateway_rest_api.api.id
  stage_name    = "prod"
}

# ── Lambda Permission for API Gateway ──────────────────────────────────────────

resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.api.execution_arn}/*/*"
}
