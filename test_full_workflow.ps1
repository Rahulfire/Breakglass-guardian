#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Test BreakGlass Guardian Full Workflow
#>

Write-Host ""
Write-Host "========================================" -ForegroundColor Blue
Write-Host " BreakGlass Guardian - Full Workflow Test" -ForegroundColor Blue
Write-Host "========================================" -ForegroundColor Blue
Write-Host ""

$baseUrl = "http://localhost:8000"

# 1. Health Check
Write-Host "[1/5] Health Check..." -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod -Uri "$baseUrl/health" -Method Get -UseBasicParsing
    Write-Host "   Status: $($health.status)" -ForegroundColor Green
    Write-Host "   Timestamp: $($health.timestamp)" -ForegroundColor Gray
} catch {
    Write-Host "   ERROR: Server not running" -ForegroundColor Red
    Write-Host "   Start with: python -m backend.main" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# 2. Create Access Request
Write-Host "[2/5] Creating Access Request..." -ForegroundColor Cyan
$requestBody = @{
    requester_email = "john.doe@company.com"
    requester_name = "John Doe"
    emergency_description = "Production DynamoDB table experiencing performance issues - need to investigate query patterns"
    resource_type = "dynamodb"
    resource_id = "breakglass-requests-dev"
    resource_region = "us-east-1"
    requested_action = "read_query_investigate"
    requested_permissions = @("dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan")
    duration_minutes = 60
    business_justification = "Production incident #12345 - Table showing high latency. Need to query table to identify problematic access patterns and optimize application queries. Time-sensitive issue affecting customer experience."
} | ConvertTo-Json

try {
    $request = Invoke-RestMethod -Uri "$baseUrl/api/requests" -Method Post -Body $requestBody -ContentType "application/json" -UseBasicParsing
    $requestId = $request.request_id
    Write-Host "   Request ID: $requestId" -ForegroundColor Green
    Write-Host "   Status: $($request.status)" -ForegroundColor Gray
    Write-Host "   Risk Level: $($request.risk_assessment.risk_level)" -ForegroundColor Yellow
    Write-Host "   Risk Score: $($request.risk_assessment.risk_score)" -ForegroundColor Gray
} catch {
    Write-Host "   ERROR: Failed to create request" -ForegroundColor Red
    Write-Host "   $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""

# 3. List Pending Approvals
Write-Host "[3/5] Checking Pending Approvals..." -ForegroundColor Cyan
try {
    $pending = Invoke-RestMethod -Uri "$baseUrl/api/approvals/pending" -Method Get -UseBasicParsing
    Write-Host "   Pending approvals: $($pending.Count)" -ForegroundColor Green
    if ($pending.Count -gt 0) {
        Write-Host "   Latest: $($pending[0].request_id)" -ForegroundColor Gray
    }
} catch {
    Write-Host "   ERROR: Failed to list approvals" -ForegroundColor Red
}

Write-Host ""

# 4. Approve Request
Write-Host "[4/5] Approving Request..." -ForegroundColor Cyan
$approvalBody = @{
    approver_id = "admin@company.com"
    approval_notes = "Approved for database investigation - verified ticket #12345"
} | ConvertTo-Json

try {
    $approval = Invoke-RestMethod -Uri "$baseUrl/api/approvals/$requestId/approve" -Method Post -Body $approvalBody -ContentType "application/json" -UseBasicParsing
    Write-Host "   Approval ID: $($approval.approval_id)" -ForegroundColor Green
    Write-Host "   Status: $($approval.status)" -ForegroundColor Gray
    Write-Host "   Approved at: $($approval.approved_at)" -ForegroundColor Gray
} catch {
    Write-Host "   ERROR: Failed to approve request" -ForegroundColor Red
    Write-Host "   $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# 5. Get Temporary Credentials
Write-Host "[5/5] Generating Temporary Credentials..." -ForegroundColor Cyan
try {
    $creds = Invoke-RestMethod -Uri "$baseUrl/api/sessions/$requestId/credentials" -Method Get -UseBasicParsing
    Write-Host "   Session ID: $($creds.session_id)" -ForegroundColor Green
    Write-Host "   Access Key: $($creds.credentials.access_key_id.Substring(0, 20))..." -ForegroundColor Gray
    Write-Host "   Expires: $($creds.expires_at)" -ForegroundColor Yellow
    Write-Host "   Duration: $($creds.duration_minutes) minutes" -ForegroundColor Gray
} catch {
    Write-Host "   ERROR: Failed to generate credentials" -ForegroundColor Red
    Write-Host "   $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " ✅ Workflow Test Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

Write-Host "Next Steps:" -ForegroundColor Cyan
Write-Host "1. View audit logs: curl $baseUrl/api/audit/events" -ForegroundColor White
Write-Host "2. Check request status: curl $baseUrl/api/requests/$requestId" -ForegroundColor White
Write-Host "3. List active sessions: curl $baseUrl/api/sessions/active" -ForegroundColor White
Write-Host ""
