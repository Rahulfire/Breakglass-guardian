# BreakGlass Guardian

## AI-Powered Emergency AWS Access Management Agent

BreakGlass Guardian is an intelligent emergency access management system designed to help cloud administrators and DevOps engineers handle urgent AWS infrastructure access requests safely and securely.

### 🎯 Overview

In real-world cloud environments, engineers sometimes need temporary elevated permissions to resolve production incidents. However, granting unrestricted administrative access during emergencies creates serious security risks. BreakGlass Guardian addresses this by introducing an AI agent that:

- Evaluates emergency access requests intelligently
- Understands incident context and urgency
- Recommends minimum required permissions
- Coordinates human approval workflows
- Manages time-limited access sessions
- Maintains comprehensive audit trails
- Detects and blocks malicious requests

### 🏗️ Architecture

```
User → React Frontend → FastAPI Backend → Amazon Bedrock AgentCore
                                              ↓
                                    Security Layers:
                                    1. Agent Instructions
                                    2. Bedrock Guardrails
                                    3. AgentCore Gateway & Policy
                                    4. AWS IAM Restrictions
                                    5. Backend Authorization
                                    6. Human Approval
                                    7. Audit & Monitoring
                                              ↓
                                    Restricted Lambda Tools
                                              ↓
                                    IAM / STS / DynamoDB
```

### 🔒 Security Principles

**The agent CAN:**
- Analyze access requests and recommend permissions
- Create approval requests for human review
- Initiate approved sandbox access workflows
- Monitor session status and generate audit reports

**The agent CANNOT:**
- Grant permanent administrative access
- Bypass human approval requirements
- Modify IAM policies or security controls
- Approve its own requests
- Execute arbitrary commands
- Access unauthorized AWS accounts

### 🚀 Technology Stack

**Backend:**
- Python 3.12
- FastAPI
- Amazon Bedrock AgentCore Runtime
- AWS SDK (Boto3)
- Pydantic for validation

**Frontend:**
- React + TypeScript
- Tailwind CSS
- Modern responsive dashboard

**AWS Services:**
- AWS IAM & STS
- Amazon DynamoDB
- AWS Lambda
- AWS CloudTrail
- Amazon CloudWatch
- Amazon Bedrock Guardrails

### 📦 Installation

#### Prerequisites

- Python 3.12+
- Node.js 18+
- AWS Account with appropriate permissions
- AWS CLI configured
- Amazon Bedrock access enabled

#### Backend Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your AWS configuration

# Run database migrations (if applicable)
python -m backend.services.init_db

# Start the backend server
uvicorn backend.main:app --reload --port 8000
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Edit .env.local with your API endpoint

# Start development server
npm run dev
```

### 🧪 Testing

#### Run Unit Tests

```bash
pytest backend/tests/ -v
```

#### Run Adversarial Security Tests

```bash
pytest backend/tests/test_prompt_injection.py -v
pytest backend/tests/test_unauthorized_access.py -v
pytest backend/tests/test_approval_validation.py -v
```

#### Test Coverage

```bash
pytest --cov=backend --cov-report=html
```

### 🔐 AWS Setup

#### 1. Create IAM Roles

```bash
# Deploy IAM roles for Lambda functions
aws cloudformation deploy \
  --template-file infrastructure/iam/roles.yaml \
  --stack-name breakglass-iam-roles \
  --capabilities CAPABILITY_NAMED_IAM
```

#### 2. Create DynamoDB Tables

```bash
# Deploy DynamoDB tables
aws cloudformation deploy \
  --template-file infrastructure/dynamodb/tables.yaml \
  --stack-name breakglass-dynamodb
```

#### 3. Configure Bedrock Agent

```bash
# Deploy Bedrock Agent configuration
python infrastructure/bedrock/deploy_agent.py
```

### 📊 Dashboard Features

**Emergency Request Submission**
- Submit urgent access requests with full context
- Specify resources, actions, and business justification

**AI Analysis View**
- Real-time agent analysis and risk classification
- Permission recommendations and security explanations

**Approval Management**
- Review pending requests
- Approve or reject with human oversight

**Active Sessions**
- Monitor temporary access sessions
- Track expiration and session status

**Security Audit**
- Complete audit trail of all operations
- Detect prompt injection attempts
- Review agent decisions and refusals

### 🎯 Usage Example

#### 1. Submit Emergency Request

```bash
POST /api/requests
{
  "requester": "engineer@company.com",
  "emergency_description": "Production EC2 instance unresponsive",
  "resource_type": "ec2",
  "resource_id": "i-1234567890abcdef0",
  "requested_action": "restart_instance",
  "duration_minutes": 30,
  "business_justification": "Critical customer-facing application down"
}
```

#### 2. Agent Analysis

The AI agent analyzes the request and returns:
- Risk classification: MEDIUM
- Recommended permissions: ec2:RebootInstances (specific instance only)
- Approval required: Yes

#### 3. Human Approval

Authorized approver reviews and approves via dashboard.

#### 4. Temporary Access

System generates time-limited AWS STS credentials with narrowly scoped permissions.

#### 5. Automatic Expiration

Session expires after approved duration. All actions audited.

### 🛡️ Security Testing Results

The system has been tested against common attack vectors:

| Test Scenario | Status | Description |
|--------------|--------|-------------|
| Privilege Escalation | ✅ BLOCKED | Refuses AdministratorAccess requests |
| Prompt Injection | ✅ BLOCKED | Ignores malicious instructions |
| Approval Bypass | ✅ BLOCKED | Requires independent human approval |
| Unauthorized Resource | ✅ BLOCKED | Backend allowlist enforcement |
| Excessive Permissions | ✅ BLOCKED | Recommends narrow alternatives |
| Expired Approval | ✅ BLOCKED | Validates approval freshness |
| Malicious Log Data | ✅ BLOCKED | Treats logs as untrusted data |
| Legitimate Emergency | ✅ PASSED | Proper workflow execution |

See `docs/stress_test_results.md` for detailed test reports.

### 📁 Project Structure

```
BreakGlass Guardian/
├── backend/
│   ├── api/              # FastAPI endpoints
│   ├── agent/            # Bedrock Agent integration
│   ├── security/         # Policy validation & enforcement
│   ├── services/         # Business logic layer
│   ├── models/           # Pydantic models
│   └── tests/            # Comprehensive test suite
├── frontend/
│   └── src/
│       ├── components/   # React components
│       ├── pages/        # Dashboard pages
│       ├── services/     # API clients
│       └── types/        # TypeScript definitions
├── infrastructure/
│   ├── iam/              # IAM roles and policies
│   ├── lambda/           # Lambda function code
│   ├── dynamodb/         # DynamoDB schemas
│   └── bedrock/          # Bedrock Agent configuration
└── docs/
    ├── architecture.md
    ├── security_rules.md
    ├── threat_model.md
    └── stress_test_results.md
```

### 🔧 Configuration

#### Environment Variables

```env
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=your-account-id

# Bedrock Configuration
BEDROCK_AGENT_ID=your-agent-id
BEDROCK_AGENT_ALIAS_ID=your-alias-id
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# DynamoDB Tables
DYNAMODB_REQUESTS_TABLE=breakglass-requests
DYNAMODB_APPROVALS_TABLE=breakglass-approvals
DYNAMODB_SESSIONS_TABLE=breakglass-sessions
DYNAMODB_AUDIT_TABLE=breakglass-audit

# Security Configuration
MAX_SESSION_DURATION_MINUTES=120
REQUIRE_APPROVAL_FOR_RISK_LEVEL=MEDIUM
ALLOWED_RESOURCE_TYPES=ec2,s3,lambda,dynamodb

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:5173
```

### 🤝 Contributing

This is a demonstration project showcasing AI-powered security controls. Contributions for improving security, testing, or architecture are welcome.

### 📄 License

MIT License - see LICENSE file for details.

### ⚠️ Security Notice

This is a demonstration application. Before deploying to production:

1. Complete security review by qualified professionals
2. Penetration testing and vulnerability assessment
3. Compliance validation for your industry
4. Regular security audits and updates
5. Proper AWS account isolation
6. Enhanced monitoring and alerting

### 📞 Support

For questions or issues, please open a GitHub issue or contact the development team.

---

**Built with security-first principles to demonstrate that AI agents can be powerful yet safely constrained.**
#   B r e a k g l a s s - g u a r d i a n  
 