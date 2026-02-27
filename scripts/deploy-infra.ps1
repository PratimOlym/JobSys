# JobSys — Infrastructure Deployment Script
# Deploys core infrastructure using Terraform

param(
    [string]$AwsRegion = "ap-south-1"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path $PSScriptRoot -Parent
$InfraDir = Join-Path $ProjectRoot "infra"

Write-Host "`n===== JobSys Infrastructure Deployment =====" -ForegroundColor Cyan

# ── Step 1: Check Prerequisites ───────────────────────────────────────────────
Write-Host "`n[1/2] Checking prerequisites..." -ForegroundColor Yellow

if (-not (Get-Command terraform -ErrorAction SilentlyContinue)) {
    Write-Error "Terraform is not installed or not in PATH."
}
if (-not (Get-Command aws -ErrorAction SilentlyContinue)) {
    Write-Error "AWS CLI is not installed or not in PATH."
}

# ── Step 2: Deploy Infrastructure (Terraform) ─────────────────────────────────
Write-Host "`n[2/2] Deploying AWS infrastructure..." -ForegroundColor Yellow
Push-Location $InfraDir

# Create dummy zip files for first run if they don't exist
# Terraform needs them to exist even if they are empty for the initial plan
$BackendDir = Join-Path $ProjectRoot "backend"
$Zips = @("layer.zip", "job_scanner.zip", "resume_matcher.zip", "document_generator.zip", "api_handler.zip")
foreach ($zip in $Zips) {
    $zipPath = Join-Path $BackendDir $zip
    if (-not (Test-Path $zipPath)) {
        Write-Host "  Creating dummy $zip for initial Terraform run..." -ForegroundColor Gray
        "dummy" | Out-File (Join-Path $BackendDir "dummy.txt")
        Compress-Archive -Path (Join-Path $BackendDir "dummy.txt") -DestinationPath $zipPath
        Remove-Item (Join-Path $BackendDir "dummy.txt")
    }
}

# Initialize Terraform
Write-Host "  Initializing Terraform..." -ForegroundColor Gray
terraform init -reconfigure

# Apply Terraform
# We use a placeholder for gemini_api_key as the user will update it in Secrets Manager
Write-Host "  Applying Terraform configuration..." -ForegroundColor Gray
terraform apply -var="aws_region=$AwsRegion" -auto-approve

# Get Outputs
$ApiUrl = terraform output -raw api_gateway_url
$StorageBucket = terraform output -raw s3_bucket_name
$FrontendBucket = terraform output -raw frontend_bucket_name

Pop-Location

Write-Host "`n===== Infrastructure Deployment Complete! =====" -ForegroundColor Green
Write-Host "API Gateway URL: $ApiUrl" -ForegroundColor Cyan
Write-Host "Storage Bucket:  $StorageBucket" -ForegroundColor Cyan
Write-Host "Frontend Bucket: $FrontendBucket" -ForegroundColor Cyan

Write-Host "`nNext Step: Update Gemini API key in Secrets Manager (jobsys/gemini-api-key)" -ForegroundColor Yellow
Write-Host "Then run: .\scripts\deploy-lambdas.ps1" -ForegroundColor Yellow
