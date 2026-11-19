#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Enable Bedrock Model Access

.DESCRIPTION
    Enables Claude model access in AWS Bedrock
#>

Write-Host ""
Write-Host "========================================" -ForegroundColor Blue
Write-Host " Enable AWS Bedrock Model Access" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

$region = "us-east-1"

Write-Host "[INFO] Checking Bedrock model access..." -ForegroundColor Cyan
Write-Host ""

# Note: AWS CLI doesn't have direct command to enable model access
# This must be done through AWS Console

Write-Host "[ACTION REQUIRED] Enable model access in AWS Console:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Open this URL:" -ForegroundColor White
Write-Host "   https://console.aws.amazon.com/bedrock/home?region=$region#/modelaccess" -ForegroundColor Cyan
Write-Host ""
Write-Host "2. Click the orange button: 'Manage model access'" -ForegroundColor White
Write-Host ""
Write-Host "3. Find 'Anthropic' section and check:" -ForegroundColor White
Write-Host "   ☑ Claude 3 Sonnet" -ForegroundColor Gray
Write-Host "   ☑ Claude 3.5 Sonnet" -ForegroundColor Gray
Write-Host "   ☑ Claude 3 Haiku" -ForegroundColor Gray
Write-Host "   (or any Claude model)" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Click 'Request model access' or 'Save changes'" -ForegroundColor White
Write-Host ""
Write-Host "5. Wait 1-2 minutes for status to change to 'Access granted'" -ForegroundColor White
Write-Host ""

# Open browser automatically
Write-Host "[INFO] Opening browser..." -ForegroundColor Cyan
Start-Process "https://console.aws.amazon.com/bedrock/home?region=$region#/modelaccess"

Write-Host ""
$response = Read-Host "Have you enabled model access? (yes/no)"

if ($response -eq "yes" -or $response -eq "y") {
    Write-Host ""
    Write-Host "[INFO] Testing Bedrock access..." -ForegroundColor Cyan
    
    python test_bedrock_access.py
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "[OK] Bedrock is ready! Proceeding to create Bedrock Agent..." -ForegroundColor Green
        exit 0
    } else {
        Write-Host ""
        Write-Host "[WARN] Bedrock access still not working. Please wait a minute and try again." -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host ""
    Write-Host "[INFO] Please enable model access and run this script again." -ForegroundColor Yellow
    exit 1
}
