#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Deploy Complete Bedrock Infrastructure

.DESCRIPTION
    Deploys Bedrock Agent infrastructure and creates the agent
#>

param(
    [string]$Environment = "dev",
    [string]$Region = "us-east-1"
)

Write-Host ""
Write-Host "========================================" -ForegroundColor Blue
Write-Host " BreakGlass Bedrock Deployment" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

# Step 1: Check model access
Write-Host "[1/4] Checking Bedrock model access..." -ForegroundColor Cyan
python test_bedrock_access.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] Bedrock model access not enabled!" -ForegroundColor Red
    Write-Host "[INFO] Run: .\enable-bedrock.ps1" -ForegroundColor Yellow
    Write-Host ""
    
    $enable = Read-Host "Do you want to enable it now? (yes/no)"
    if ($enable -eq "yes" -or $enable -eq "y") {
        .\enable-bedrock.ps1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] Failed to enable Bedrock access" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "[INFO] Please enable model access manually and run this script again" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host ""

# Step 2: Deploy CloudFormation stack
Write-Host "[2/4] Deploying Bedrock infrastructure..." -ForegroundColor Cyan
Write-Host "[INFO] Stack: breakglass-bedrock" -ForegroundColor Gray
Write-Host "[INFO] Environment: $Environment" -ForegroundColor Gray
Write-Host ""

try {
    aws cloudformation deploy `
        --template-file infrastructure/bedrock/agent.yaml `
        --stack-name breakglass-bedrock `
        --parameter-overrides Environment=$Environment `
        --capabilities CAPABILITY_NAMED_IAM `
        --region $Region
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Infrastructure deployed!" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Failed to deploy infrastructure" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[ERROR] CloudFormation deployment failed" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 3: Create Bedrock Agent
Write-Host "[3/4] Creating Bedrock Agent..." -ForegroundColor Cyan
Write-Host "[INFO] This may take 30-60 seconds..." -ForegroundColor Gray
Write-Host ""

python create_bedrock_agent.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] Failed to create Bedrock Agent" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 4: Update .env file
Write-Host "[4/4] Updating configuration..." -ForegroundColor Cyan

# Get stack outputs
$outputs = aws cloudformation describe-stacks `
    --stack-name breakglass-bedrock `
    --query 'Stacks[0].Outputs' `
    --region $Region | ConvertFrom-Json

Write-Host "[INFO] CloudFormation outputs retrieved" -ForegroundColor Gray
Write-Host ""

Write-Host "========================================" -ForegroundColor Green
Write-Host " Bedrock Deployment Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Host "[INFO] Next steps:" -ForegroundColor Cyan
Write-Host "1. Update .env with BEDROCK_AGENT_ID and BEDROCK_AGENT_ALIAS_ID" -ForegroundColor White
Write-Host "2. Start application: python -m backend.main" -ForegroundColor White
Write-Host "3. Test the complete workflow" -ForegroundColor White
Write-Host ""

Write-Host "[OK] Bedrock is ready to use!" -ForegroundColor Green
Write-Host ""
