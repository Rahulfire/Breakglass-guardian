# 🚀 Deploy to AWS - Quick Start

## ONE COMMAND DEPLOYMENT

```powershell
.\deploy-aws.ps1
```

That's it! The script will:
1. ✅ Check your AWS setup
2. ✅ Deploy DynamoDB tables
3. ✅ Create IAM roles
4. ✅ Show you what was created

---

## ⚡ Super Quick Steps

### 1. Make sure AWS CLI is configured
```powershell
aws --version
aws sts get-caller-identity
```

If not configured:
```powershell
aws configure
# Enter your AWS credentials
```

### 2. Run deployment
```powershell
.\deploy-aws.ps1
```

### 3. Enable Bedrock (Manual - 2 minutes)
1. Go to: https://console.aws.amazon.com/bedrock
2. Click "Model access"
3. Click "Manage model access"
4. Enable "Claude 3 Sonnet"
5. Save

### 4. Update .env
The script will tell you what to update in your `.env` file.

### 5. Test it!
```powershell
python -m backend.main
```

---

## 📝 What Gets Created

- ✅ 4 DynamoDB tables (requests, approvals, sessions, audit)
- ✅ 6 IAM roles (restricted access roles + backend role)
- ✅ All with proper security settings

**Cost:** ~$6-27/month for development

---

## 🎯 If You Want Manual Control

See detailed guide: `AWS_DEPLOYMENT_GUIDE.md`

---

## 🆘 Problems?

### AWS CLI not found?
```powershell
winget install Amazon.AWSCLI
```

### Not configured?
```powershell
aws configure
```

### Permission errors?
You need Administrator access or CloudFormation + DynamoDB + IAM permissions.

---

## ✅ After Deployment

1. Check what was created:
```powershell
aws dynamodb list-tables
aws iam list-roles --query 'Roles[?contains(RoleName, `BreakGlass`)].RoleName'
```

2. Update your `.env` file with the table names

3. Start the application:
```powershell
python -m backend.main
```

---

**Ready? Just run:**
```powershell
.\deploy-aws.ps1
```

🚀 **DEPLOY NOW!**
