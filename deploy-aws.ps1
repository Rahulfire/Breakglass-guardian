#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Deploy BreakGlass Guardian AWS Infrastructure

.DESCRIPTION
    Automated deployment script for DynamoDB tables and IAM roles

.PARAMETER Environment
    Environment name (dev, staging, prod). Default: dev

.PARAMETER Region
    AWS region. Default: us-east-1

.PARAMETER SkipDynamoDB
    Skip DynamoDB deployment

.PARAMETER SkipIAM
    Skip IAM deployment

.EXAMPLE
    .\deploy-aws.ps1
    Deploy everything with defaults

.EXAMPLE
    .\deploy-aws.ps1 -Environment prod -Region us-west-2
    Deploy to production in us-west-2
#>

param(
    [string]$Environment = "dev",
    [string]$Region = "us-east-1",
    [switch]$SkipDynamoDB,
    [switch]$SkipIAM
)

# Colors for output
function Write-Success { Write-Host "[OK] $args" -ForegroundColor Green }
function Write-Info { Write-Host "[INFO] $args" -ForegroundColor Cyan }
function Write-Warning { Write-Host "[WARN] $args" -ForegroundColor Yellow }
function Write-Error { Write-Host "[ERROR] $args" -ForegroundColor Red }

Write-Host ""
Write-Host "================================" -ForegroundColor Blue
Write-Host " BreakGlass Guardian Deployment" -ForegroundColor Blue
Write-Host "================================" -ForegroundColor Blue
Write-Host ""

# Check AWS CLI
Write-Info "Checking AWS CLI installation..."
try {
    $awsVersion = aws --version
    Write-Success "AWS CLI installed: $awsVersion"
} catch {
    Write-Error "AWS CLI not found. Please install it first."
    Write-Info "Download from: https://awscli.amazonaws.com/AWSCLIV2.msi"
    exit 1
}

# Check AWS credentials
Write-Info "Checking AWS credentials..."
try {
    $identity = aws sts get-caller-identity | ConvertFrom-Json
    $accountId = $identity.Account
    $userArn = $identity.Arn
    Write-Success "AWS Account ID: $accountId"
    Write-Success "User ARN: $userArn"
} catch {
    Write-Error "AWS credentials not configured."
    Write-Info "Run: aws configure"
    exit 1
}

Write-Host ""

# Deploy DynamoDB
if (-not $SkipDynamoDB) {
    Write-Host "[DYNAMODB] Deploying DynamoDB Tables..." -ForegroundColor Yellow
    Write-Info "Stack: breakglass-dynamodb"
    Write-Info "Environment: $Environment"
    Write-Info "Region: $Region"
    Write-Host ""
    
    try {
        aws cloudformation deploy `
            --template-file infrastructure/dynamodb/tables.yaml `
            --stack-name breakglass-dynamodb `
            --parameter-overrides Environment=$Environment `
            --region $Region
        
        Write-Success "DynamoDB tables deployed successfully!"
        
        # Get table names
        $outputs = aws cloudformation describe-stacks `
            --stack-name breakglass-dynamodb `
            --query 'Stacks[0].Outputs' `
            --region $Region | ConvertFrom-Json
        
        Write-Host ""
        Write-Info "Created Tables:"
        foreach ($output in $outputs) {
            Write-Host "  - $($output.OutputValue)" -ForegroundColor Cyan
        }
    } catch {
        Write-Error "Failed to deploy DynamoDB tables"
        Write-Host $_.Exception.Message -ForegroundColor Red
        exit 1
    }
} else {
    Write-Warning "Skipping DynamoDB deployment"
}

Write-Host ""

# Deploy IAM Roles
if (-not $SkipIAM) {
    Write-Host "[IAM] Deploying IAM Roles..." -ForegroundColor Yellow
    Write-Info "Stack: breakglass-iam"
    Write-Info "Environment: $Environment"
    Write-Info "Backend Role ARN: $userArn"
    Write-Host ""
    
    try {
        aws cloudformation deploy `
            --template-file infrastructure/iam/roles.yaml `
            --stack-name breakglass-iam `
            --parameter-overrides Environment=$Environment BackendRoleArn=$userArn `
            --capabilities CAPABILITY_NAMED_IAM `
            --region $Region
        
        Write-Success "IAM roles deployed successfully!"
        
        # Get role ARNs
        $outputs = aws cloudformation describe-stacks `
            --stack-name breakglass-iam `
            --query 'Stacks[0].Outputs' `
            --region $Region | ConvertFrom-Json
        
        Write-Host ""
        Write-Info "Created Roles:"
        foreach ($output in $outputs) {
            Write-Host "  - $($output.OutputKey): $($output.OutputValue)" -ForegroundColor Cyan
        }
    } catch {
        Write-Error "Failed to deploy IAM roles"
        Write-Host $_.Exception.Message -ForegroundColor Red
        exit 1
    }
} else {
    Write-Warning "Skipping IAM deployment"
}

Write-Host ""
Write-Host "================================" -ForegroundColor Green
Write-Host " Deployment Complete!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Green
Write-Host ""

Write-Info "Next Steps:"
Write-Host "1. Update .env file with AWS Account ID: $accountId" -ForegroundColor White
Write-Host "2. Update DynamoDB table names in .env" -ForegroundColor White
Write-Host "3. Enable Bedrock model access in AWS Console" -ForegroundColor White
Write-Host "4. Run: python -m backend.main" -ForegroundColor White
Write-Host ""

Write-Info "To view stack details:"
Write-Host "  aws cloudformation describe-stacks --stack-name breakglass-dynamodb --region $Region" -ForegroundColor White
Write-Host "  aws cloudformation describe-stacks --stack-name breakglass-iam --region $Region" -ForegroundColor White
Write-Host ""

Write-Success "Deployment successful!"
