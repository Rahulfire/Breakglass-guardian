#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Run BreakGlass Guardian in Local Mode

.DESCRIPTION
    Starts the application without Bedrock - uses deterministic risk scoring
#>

Write-Host ""
Write-Host "========================================" -ForegroundColor Blue
Write-Host " BreakGlass Guardian - Local Mode" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

Write-Host "[INFO] Configuration:" -ForegroundColor Cyan
Write-Host "  - Mode: LOCAL (No Bedrock required)" -ForegroundColor Gray
Write-Host "  - Risk Scoring: Deterministic rules" -ForegroundColor Gray
Write-Host "  - Database: In-memory (no DynamoDB)" -ForegroundColor Gray
Write-Host "  - AWS Integration: STS credentials via boto3" -ForegroundColor Gray
Write-Host ""

# Check if server is already running
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        Write-Host "[WARN] Server already running on port 8000" -ForegroundColor Yellow
        Write-Host ""
        $restart = Read-Host "Stop and restart? (yes/no)"
        if ($restart -eq "yes" -or $restart -eq "y") {
            Write-Host "[INFO] Stopping existing server..." -ForegroundColor Cyan
            # Find and kill the process
            $processes = Get-Process python -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like "*uvicorn*" -or $_.CommandLine -like "*backend.main*" }
            foreach ($proc in $processes) {
                Stop-Process -Id $proc.Id -Force
                Write-Host "[OK] Stopped process $($proc.Id)" -ForegroundColor Green
            }
            Start-Sleep -Seconds 2
        } else {
            Write-Host "[INFO] Keeping existing server running" -ForegroundColor Yellow
            Write-Host "[INFO] Test with: curl http://localhost:8000/health" -ForegroundColor Cyan
            Write-Host ""
            exit 0
        }
    }
} catch {
    # Server not running, continue
}

Write-Host "[INFO] Starting BreakGlass Guardian..." -ForegroundColor Cyan
Write-Host ""

# Check Python dependencies
Write-Host "[1/3] Checking dependencies..." -ForegroundColor Cyan
$requirements = Get-Content requirements.txt
Write-Host "  - Found $($requirements.Count) packages" -ForegroundColor Gray

# Check AWS credentials
Write-Host ""
Write-Host "[2/3] Checking AWS credentials..." -ForegroundColor Cyan
try {
    $identity = aws sts get-caller-identity 2>$null | ConvertFrom-Json
    if ($identity) {
        Write-Host "  - Account: $($identity.Account)" -ForegroundColor Green
        Write-Host "  - User: $($identity.Arn.Split('/')[-1])" -ForegroundColor Gray
    }
} catch {
    Write-Host "  - [WARN] AWS credentials not configured" -ForegroundColor Yellow
    Write-Host "  - [INFO] STS credential generation will use mock mode" -ForegroundColor Gray
}

Write-Host ""
Write-Host "[3/3] Starting FastAPI server..." -ForegroundColor Cyan
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " Server Starting..." -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Start the server
python -m backend.main

