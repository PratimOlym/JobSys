# JobSys — Lambda Deployment Script
# Packages and deploys code using Terraform/cli

param(
    [string]$AwsRegion = "ap-south-1",
    [switch]$DeployFrontend
)

$ErrorActionPreference = "Stop"

# Set AWS Credentials/Region
$env:AWS_DEFAULT_REGION = "ap-south-1"
$env:AWS_PROFILE = "superclub-dev"

$ProjectRoot = Split-Path $PSScriptRoot -Parent
$ScriptsDir = Join-Path $ProjectRoot "scripts"
$InfraDir = Join-Path $ProjectRoot "infra"
$FrontendDir = Join-Path $ProjectRoot "frontend"

Write-Host "`n===== JobSys Lambda & Code Deployment =====" -ForegroundColor Cyan

# ── Step 1: Package Lambdas ───────────────────────────────────────────────────
Write-Host "`n[1/3] Packaging Lambda functions..." -ForegroundColor Yellow
& "$ScriptsDir\package-lambdas.ps1"

# ── Step 2: Update Infrastructure (Code only) ─────────────────────────────────
Write-Host "`n[2/3] Updating Lambda code via Terraform..." -ForegroundColor Yellow
Push-Location $InfraDir

# Apply code changes (Terraform will detect ZIP changes)
$TerraformArgs = @(
    "apply",
    "-var=aws_region=$AwsRegion",
    "-target", "aws_lambda_function.job_scanner",
    "-target", "aws_lambda_function.resume_matcher",
    "-target", "aws_lambda_function.document_generator",
    "-target", "aws_lambda_function.api_handler",
    "-target", "aws_lambda_layer_version.dependencies",
    "-auto-approve"
)
terraform @TerraformArgs

# Get API URL for frontend
$ApiUrl = terraform output -raw api_gateway_url
$FrontendBucket = terraform output -raw frontend_bucket_name

Pop-Location

# ── Step 3: Optional Frontend Deployment ──────────────────────────────────────
if ($DeployFrontend) {
    Write-Host "`n[3/3] Deploying Frontend..." -ForegroundColor Yellow
    
    # Update API URL in frontend source
    $ApiServicePath = Join-Path $FrontendDir "src/services/api.js"
    $ApiContent = Get-Content $ApiServicePath
    # Replace the base URL line. Pattern matches the const definition.
    $ApiContent = $ApiContent -replace "const API_BASE_URL = .*;", "const API_BASE_URL = '$ApiUrl';"
    Set-Content $ApiServicePath $ApiContent
    
    # Build
    Push-Location $FrontendDir
    Write-Host "  Installing frontend dependencies..." -ForegroundColor Gray
    npm install
    Write-Host "  Building frontend..." -ForegroundColor Gray
    npm run build
    
    # Sync to S3
    Write-Host "  Uploading to S3 ($FrontendBucket)..." -ForegroundColor Gray
    aws s3 sync dist/ "s3://$FrontendBucket/" --delete
    Pop-Location
} else {
    Write-Host "`n[3/3] Skipping Frontend deployment (use -DeployFrontend to deploy)." -ForegroundColor Gray
}

Write-Host "`n===== Lambda Code Deployment Complete! =====" -ForegroundColor Green
Write-Host "API Gateway URL: $ApiUrl" -ForegroundColor Cyan
if ($DeployFrontend) {
    Push-Location $InfraDir
    $FrontendUrl = terraform output -raw frontend_website_url
    Pop-Location
    Write-Host "Frontend URL:    http://$FrontendUrl" -ForegroundColor Cyan
}
