# Lambda Packaging Script for JobSys
# Creates ZIP files for each Lambda function and the shared dependency layer

param(
    [switch]$LayerOnly,
    [switch]$SkipLayer
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path $PSScriptRoot -Parent
$BackendDir = Join-Path $ProjectRoot "backend"

Write-Host "=== JobSys Lambda Packaging ===" -ForegroundColor Cyan

# ── Step 1: Build Lambda Layer (shared dependencies) ──────────────────────────
if (-not $SkipLayer) {
    Write-Host "`n[1/5] Checking Lambda layer dependencies..." -ForegroundColor Yellow
    $ReqFile = Join-Path $BackendDir "requirements.txt"
    $LayerZip = Join-Path $BackendDir "layer.zip"
    $HashFile = Join-Path $BackendDir "requirements.hash"
    
    $CurrentHash = (Get-FileHash $ReqFile).Hash
    $StoredHash = ""
    if (Test-Path $HashFile) { $StoredHash = Get-Content $HashFile }

    if ($CurrentHash -eq $StoredHash -and (Test-Path $LayerZip)) {
        Write-Host "  Requirements unchanged. Skipping layer build." -ForegroundColor Gray
    } else {
        Write-Host "  Requirements changed or layer missing. Building layer..." -ForegroundColor Yellow
        $LayerDir = Join-Path $BackendDir "layer_build"

        # Clean
        if (Test-Path $LayerDir) { Remove-Item -Recurse -Force $LayerDir }
        New-Item -ItemType Directory -Path "$LayerDir\python" -Force | Out-Null

        # Install dependencies into layer (Force Linux platform binaries)
        & pip install `
            --platform manylinux2014_x86_64 `
            --target "$LayerDir\python" `
            --implementation cp `
            --python-version 3.11 `
            --only-binary=:all: `
            --upgrade `
            -r $ReqFile `
            --quiet --no-cache-dir

        # Cleanup unnecessary files to reduce layer size
        Write-Host "  Cleaning up layer build..." -ForegroundColor Gray
        Get-ChildItem -Path "$LayerDir\python" -Include "*.dist-info", "*.egg-info", "tests", "__pycache__" -Recurse | Remove-Item -Recurse -Force
        # Remove bin directory if it exists
        if (Test-Path "$LayerDir\python\bin") { Remove-Item -Recurse -Force "$LayerDir\python\bin" }
        
        # Create ZIP with retry
        if (Test-Path $LayerZip) { Remove-Item -Force $LayerZip }
        Push-Location $LayerDir
        $retryCount = 0
        $maxRetries = 3
        while ($retryCount -lt $maxRetries) {
            try {
                Compress-Archive -Path "python" -DestinationPath $LayerZip -Force -ErrorAction Stop
                break
            } catch {
                $retryCount++
                if ($retryCount -eq $maxRetries) { throw $_ }
                Write-Host "  Retry $retryCount/3: File lock detected, waiting..." -ForegroundColor Gray
                Start-Sleep -Seconds 1
            }
        }
        Pop-Location

        # Save hash
        $CurrentHash | Out-File $HashFile -Encoding ascii

        # Cleanup
        Remove-Item -Recurse -Force $LayerDir
        Write-Host "  Layer created: $LayerZip ($([math]::Round((Get-Item $LayerZip).Length / 1MB, 1)) MB)" -ForegroundColor Green
    }
}

if ($LayerOnly) {
    Write-Host "`nDone (layer only)." -ForegroundColor Cyan
    exit 0
}

# ── Step 2: Package each Lambda function ──────────────────────────────────────

$Lambdas = @(
    @{ Name = "job_scanner";         Dir = "job_scanner" },
    @{ Name = "resume_matcher";      Dir = "resume_matcher" },
    @{ Name = "document_generator";  Dir = "document_generator" },
    @{ Name = "api_handler";         Dir = "api_handler" }
)

$SharedDir = Join-Path $BackendDir "shared"
$step = 2

foreach ($lambda in $Lambdas) {
    Write-Host "`n[$step/5] Packaging $($lambda.Name)..." -ForegroundColor Yellow
    $step++

    $SrcDir = Join-Path $BackendDir $lambda.Dir
    $ZipFile = Join-Path $BackendDir "$($lambda.Name).zip"
    $TempDir = Join-Path $BackendDir "pkg_$($lambda.Name)"

    # Clean
    if (Test-Path $TempDir) { Remove-Item -Recurse -Force $TempDir }
    New-Item -ItemType Directory -Path $TempDir -Force | Out-Null

    # Copy Lambda source
    Copy-Item -Recurse -Path $SrcDir -Destination (Join-Path $TempDir $lambda.Dir)

    # Copy shared module
    Copy-Item -Recurse -Path $SharedDir -Destination (Join-Path $TempDir "shared")

    # Create ZIP with retry
    if (Test-Path $ZipFile) { Remove-Item -Force $ZipFile }
    Push-Location $TempDir
    $retryCount = 0
    $maxRetries = 3
    while ($retryCount -lt $maxRetries) {
        try {
            Compress-Archive -Path "*" -DestinationPath $ZipFile -Force -ErrorAction Stop
            break
        } catch {
            $retryCount++
            if ($retryCount -eq $maxRetries) { throw $_ }
            Write-Host "  Retry $retryCount/3: File lock detected, waiting..." -ForegroundColor Gray
            Start-Sleep -Seconds 1
        }
    }
    Pop-Location

    # Cleanup
    Remove-Item -Recurse -Force $TempDir
    Write-Host "  Package created: $ZipFile ($([math]::Round((Get-Item $ZipFile).Length / 1KB, 1)) KB)" -ForegroundColor Green
}

Write-Host "`n=== Packaging Complete ===" -ForegroundColor Cyan
Write-Host "Lambda packages are ready in: $BackendDir" -ForegroundColor Green
Write-Host "Next: cd infra && terraform init && terraform apply" -ForegroundColor Yellow
