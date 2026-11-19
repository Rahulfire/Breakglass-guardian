#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Setup AWS credentials for BreakGlass Guardian

.DESCRIPTION
    Helps configure AWS CLI credentials interactively
#>

Write-Host ""
Write-Host "========================================" -ForegroundColor Blue
Write-Host " AWS Credentials Setup" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

# Check if AWS CLI is installed
try {
    $version = aws --version
    Write-Host "✅ AWS CLI installed: $version" -ForegroundColor Green
} catch {
    Write-Host "❌ AWS CLI not found!" -ForegroundColor Red
    Write-Host "Please install from: https://awscli.amazonaws.com/AWSCLIV2.msi" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "To configure AWS CLI, you need:" -ForegroundColor Cyan
Write-Host "1. AWS Access Key ID" -ForegroundColor White
Write-Host "2. AWS Secret Access Key" -ForegroundColor White
Write-Host ""

Write-Host "========================================" -ForegroundColor Yellow
Write-Host " How to Get AWS Access Keys" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "Method 1: AWS Console (Manual - 2 minutes)" -ForegroundColor Cyan
Write-Host "1. Go to: https://console.aws.amazon.com/iam/" -ForegroundColor White
Write-Host "2. Click: Users → Your username" -ForegroundColor White
Write-Host "3. Click: Security credentials tab" -ForegroundColor White
Write-Host "4. Click: Create access key" -ForegroundColor White
Write-Host "5. Choose: Command Line Interface (CLI)" -ForegroundColor White
Write-Host "6. Click: Next → Create access key" -ForegroundColor White
Write-Host "7. Copy both: Access Key ID and Secret Access Key" -ForegroundColor White
Write-Host ""

Write-Host "Method 2: Using AWS CLI (if you have temporary credentials)" -ForegroundColor Cyan
Write-Host "If you're logged in via SSO or temporary credentials:" -ForegroundColor White
Write-Host "  aws iam create-access-key --user-name YOUR_USERNAME" -ForegroundColor Gray
Write-Host ""

Write-Host "========================================" -ForegroundColor Green
Write-Host " Ready to Configure?" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

$response = Read-Host "Do you have your Access Key ID and Secret Access Key? (yes/no)"

if ($response -eq "yes" -or $response -eq "y") {
    Write-Host ""
    Write-Host "Great! Let's configure AWS CLI..." -ForegroundColor Green
    Write-Host ""
    Write-Host "Please enter the following when prompted:" -ForegroundColor Yellow
    Write-Host "  - AWS Access Key ID: [paste your access key]" -ForegroundColor White
    Write-Host "  - AWS Secret Access Key: [paste your secret key]" -ForegroundColor White
    Write-Host "  - Default region name: us-east-1" -ForegroundColor White
    Write-Host "  - Default output format: json" -ForegroundColor White
    Write-Host ""
    
    # Run aws configure
    aws configure
    
    Write-Host ""
    Write-Host "Testing configuration..." -ForegroundColor Cyan
    
    try {
        $identity = aws sts get-caller-identity | ConvertFrom-Json
        Write-Host ""
        Write-Host "✅ Success! AWS configured correctly" -ForegroundColor Green
        Write-Host "   Account ID: $($identity.Account)" -ForegroundColor White
        Write-Host "   User ARN: $($identity.Arn)" -ForegroundColor White
        Write-Host ""
        Write-Host "You're ready to deploy! Run: .\deploy-aws.ps1" -ForegroundColor Green
    } catch {
        Write-Host ""
        Write-Host "❌ Configuration failed. Please check your credentials." -ForegroundColor Red
        Write-Host "   Error: $($_.Exception.Message)" -ForegroundColor Red
    }
    
} else {
    Write-Host ""
    Write-Host "No problem! Follow these steps:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "1. Open AWS Console: https://console.aws.amazon.com/iam/" -ForegroundColor White
    Write-Host "2. Create access key (see instructions above)" -ForegroundColor White
    Write-Host "3. Run this script again: .\setup-aws-credentials.ps1" -ForegroundColor White
    Write-Host ""
}
