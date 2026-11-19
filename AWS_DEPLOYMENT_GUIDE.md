# BreakGlass Guardian - AWS Deployment Guide

Complete step-by-step guide to deploy AWS infrastructure.

---

## 📋 Prerequisites

### 1. AWS Account Setup
- ✅ Active AWS account
- ✅ AWS CLI installed
- ✅ Administrator access (or appropriate permissions)

### 2. Install AWS CLI (if not installed)

**Windows:**
```powershell
# Download and install AWS CLI v2
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi

# Verify installation
aws --version
```

**Alternative (PowerShell):**
```powershell
winget install Amazon.AWSCLI
```

### 3. Configure AWS Credentials

```powershell
# Run AWS configure
aws configure

# Enter your credentials:
# AWS Access Key ID: YOUR_ACCESS_KEY
# AWS Secret Access Key: YOUR_SECRET_KEY
# Default region name: us-east-1
# Default output format: json
```

**Verify configuration:**
```powershell
aws sts get-caller-identity
```

You should see your AWS account ID and user ARN.

---

## 🚀 Deployment Steps

### **Step 1: Deploy DynamoDB Tables** (5-10 minutes)

#### 1.1 Review the Template
```powershell
# View the DynamoDB template
code infrastructure\dynamodb\tables.yaml
```

#### 1.2 Deploy DynamoDB Stack
```powershell
aws cloudformation deploy `
  --template-file infrastructure/dynamodb/tables.yaml `
  --stack-name breakglass-dynamodb `
  --parameter-overrides Environment=dev `
  --region us-east-1
```

**Expected output:**
```
Waiting for changeset to be created..
Waiting for stack create/update to complete
Successfully created/updated stack - breakglass-dynamodb
```

#### 1.3 Verify Tables Created
```powershell
# List DynamoDB tables
aws dynamodb list-tables --region us-east-1

# Should see:
# - breakglass-requests-dev
# - breakglass-approvals-dev
# - breakglass-sessions-dev
# - breakglass-audit-dev
```

#### 1.4 Get Table Details
```powershell
# Get table ARN and details
aws cloudformation describe-stacks `
  --stack-name breakglass-dynamodb `
  --query 'Stacks[0].Outputs' `
  --region us-east-1
```

---

### **Step 2: Deploy IAM Roles** (5-10 minutes)

#### 2.1 Get Your AWS Account ID
```powershell
$AWS_ACCOUNT_ID = (aws sts get-caller-identity --query 'Account' --output text)
Write-Host "AWS Account ID: $AWS_ACCOUNT_ID"
```

#### 2.2 Get Your User/Role ARN
```powershell
$USER_ARN = (aws sts get-caller-identity --query 'Arn' --output text)
Write-Host "Your ARN: $USER_ARN"
```

#### 2.3 Deploy IAM Stack
```powershell
aws cloudformation deploy `
  --template-file infrastructure/iam/roles.yaml `
  --stack-name breakglass-iam `
  --parameter-overrides Environment=dev BackendRoleArn=$USER_ARN `
  --capabilities CAPABILITY_NAMED_IAM `
  --region us-east-1
```

**Note:** `CAPABILITY_NAMED_IAM` is required because we're creating IAM roles.

**Expected output:**
```
Successfully created/updated stack - breakglass-iam
```

#### 2.4 Verify Roles Created
```powershell
# List IAM roles
aws iam list-roles --query 'Roles[?contains(RoleName, `BreakGlass`)].RoleName'

# Should see:
# - BreakGlassRestrictedEC2-dev
# - BreakGlassRestrictedLambda-dev
# - BreakGlassRestrictedS3Read-dev
# - BreakGlassRestrictedDynamoDBRead-dev
# - BreakGlassRestrictedRDS-dev
# - BreakGlassBackendApp-dev
```

#### 2.5 Get Role ARNs
```powershell
aws cloudformation describe-stacks `
  --stack-name breakglass-iam `
  --query 'Stacks[0].Outputs' `
  --region us-east-1
```

---

### **Step 3: Set Up Amazon Bedrock** (10-15 minutes)

#### 3.1 Enable Bedrock Model Access

1. **Open AWS Console:** https://console.aws.amazon.com/bedrock
2. **Navigate to:** Model access (left sidebar)
3. **Click:** "Manage model access"
4. **Enable models:**
   - ✅ Claude 3 Sonnet
   - ✅ Claude 3.5 Sonnet (recommended)
5. **Click:** "Save changes"
6. **Wait:** 2-3 minutes for activation

#### 3.2 Create Bedrock Agent (Manual - via Console)

**For now, we'll use Bedrock Models directly instead of Agents:**

The Bedrock Agent setup is complex. For initial testing, we'll use the Bedrock Runtime API directly.

**Skip agent creation for now** - we'll implement direct model invocation.

---

### **Step 4: Update Environment Configuration** (2 minutes)

#### 4.1 Get Stack Outputs
```powershell
# Get DynamoDB table names
$REQUESTS_TABLE = (aws cloudformation describe-stacks --stack-name breakglass-dynamodb --query 'Stacks[0].Outputs[?OutputKey==`RequestsTableName`].OutputValue' --output text)
$APPROVALS_TABLE = (aws cloudformation describe-stacks --stack-name breakglass-dynamodb --query 'Stacks[0].Outputs[?OutputKey==`ApprovalsTableName`].OutputValue' --output text)
$SESSIONS_TABLE = (aws cloudformation describe-stacks --stack-name breakglass-dynamodb --query 'Stacks[0].Outputs[?OutputKey==`SessionsTableName`].OutputValue' --output text)
$AUDIT_TABLE = (aws cloudformation describe-stacks --stack-name breakglass-dynamodb --query 'Stacks[0].Outputs[?OutputKey==`AuditTableName`].OutputValue' --output text)

# Display values
Write-Host "Requests Table: $REQUESTS_TABLE"
Write-Host "Approvals Table: $APPROVALS_TABLE"
Write-Host "Sessions Table: $SESSIONS_TABLE"
Write-Host "Audit Table: $AUDIT_TABLE"
```

#### 4.2 Update .env File
```powershell
# Open .env file
code .env
```

**Update these values:**
```ini
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=YOUR_ACCOUNT_ID  # From step 2.1

# DynamoDB Tables
DYNAMODB_REQUESTS_TABLE=breakglass-requests-dev
DYNAMODB_APPROVALS_TABLE=breakglass-approvals-dev
DYNAMODB_SESSIONS_TABLE=breakglass-sessions-dev
DYNAMODB_AUDIT_TABLE=breakglass-audit-dev

# Bedrock Configuration (we'll use direct model invocation)
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
```

---

### **Step 5: Test AWS Integration** (5 minutes)

#### 5.1 Test DynamoDB Access
```powershell
# Test connection to DynamoDB
aws dynamodb describe-table `
  --table-name breakglass-requests-dev `
  --region us-east-1
```

#### 5.2 Test IAM Role Assumption
```powershell
# Test assuming a restricted role
aws sts assume-role `
  --role-arn "arn:aws:iam::YOUR_ACCOUNT_ID:role/BreakGlassRestrictedEC2-dev" `
  --role-session-name test-session `
  --external-id breakglass-guardian `
  --duration-seconds 900
```

**Expected:** You should receive temporary credentials.

#### 5.3 Test Bedrock Access
```powershell
# List available models
aws bedrock list-foundation-models --region us-east-1

# Test model invocation
aws bedrock-runtime invoke-model `
  --model-id anthropic.claude-3-sonnet-20240229-v1:0 `
  --body '{"prompt":"Human: Hello\nAssistant:","max_tokens_to_sample":100}' `
  --region us-east-1 `
  output.json
```

---

### **Step 6: Update Application to Use DynamoDB** (10 minutes)

I'll create a DynamoDB integration helper:

```powershell
# This will be created in the next step
code backend/services/dynamodb_service.py
```

---

## 📊 Deployment Checklist

### ✅ Prerequisites
- [ ] AWS CLI installed
- [ ] AWS credentials configured
- [ ] Administrator access

### ✅ DynamoDB
- [ ] Tables deployed
- [ ] Tables verified
- [ ] ARNs collected

### ✅ IAM Roles
- [ ] Roles deployed
- [ ] Roles verified
- [ ] ARNs collected

### ✅ Bedrock
- [ ] Model access enabled
- [ ] Model tested
- [ ] Configuration updated

### ✅ Application
- [ ] .env file updated
- [ ] AWS integration tested
- [ ] Application running

---

## 🎯 Quick Deployment (All at Once)

If you want to deploy everything quickly:

```powershell
# Set variables
$AWS_ACCOUNT_ID = (aws sts get-caller-identity --query 'Account' --output text)
$USER_ARN = (aws sts get-caller-identity --query 'Arn' --output text)

# Deploy DynamoDB
aws cloudformation deploy `
  --template-file infrastructure/dynamodb/tables.yaml `
  --stack-name breakglass-dynamodb `
  --parameter-overrides Environment=dev `
  --region us-east-1

# Deploy IAM
aws cloudformation deploy `
  --template-file infrastructure/iam/roles.yaml `
  --stack-name breakglass-iam `
  --parameter-overrides Environment=dev BackendRoleArn=$USER_ARN `
  --capabilities CAPABILITY_NAMED_IAM `
  --region us-east-1

# Verify
aws cloudformation describe-stacks --stack-name breakglass-dynamodb
aws cloudformation describe-stacks --stack-name breakglass-iam
```

---

## 🔧 Troubleshooting

### Issue: "Insufficient permissions"
**Solution:** Ensure your AWS user has Administrator or appropriate CloudFormation permissions.

### Issue: "Stack already exists"
**Solution:** Delete existing stack or update it:
```powershell
aws cloudformation delete-stack --stack-name breakglass-dynamodb
```

### Issue: "Model access not enabled"
**Solution:** Go to Bedrock console and enable model access manually.

### Issue: "Cannot assume role"
**Solution:** Check the BackendRoleArn parameter matches your user ARN.

---

## 💰 Cost Estimate

### DynamoDB (Pay-per-request)
- **Development:** ~$0-5/month
- **Production:** Varies by usage

### IAM Roles
- **Free** - No charge for IAM

### Bedrock
- **Claude 3 Sonnet:** ~$3 per 1M input tokens
- **Estimated:** $5-20/month for development

**Total Estimated Cost: $5-25/month for development**

---

## 🗑️ Clean Up (Delete Resources)

When you're done testing:

```powershell
# Delete IAM stack first (dependencies)
aws cloudformation delete-stack --stack-name breakglass-iam --region us-east-1

# Wait for completion
aws cloudformation wait stack-delete-complete --stack-name breakglass-iam

# Delete DynamoDB stack
aws cloudformation delete-stack --stack-name breakglass-dynamodb --region us-east-1

# Verify deletion
aws cloudformation list-stacks --query 'StackSummaries[?contains(StackName, `breakglass`)].StackStatus'
```

---

## ✅ Next Steps After Deployment

1. **Test Application with AWS:**
   ```powershell
   python -m backend.main
   ```

2. **Submit Test Request:**
   Use the API to create a request that will use real AWS resources

3. **Monitor CloudWatch Logs:**
   Check for any errors in AWS console

4. **Update Services:**
   Integration DynamoDB with the backend services

---

## 📞 Support

If you encounter issues:
1. Check AWS CloudFormation console for stack events
2. Review CloudWatch Logs
3. Verify IAM permissions
4. Check region configuration

---

**Ready to deploy? Start with Step 1!** 🚀
