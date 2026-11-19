"""
Data models for access requests
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr, validator
from enum import Enum


class ResourceType(str, Enum):
    """Supported AWS resource types"""
    EC2 = "ec2"
    S3 = "s3"
    LAMBDA = "lambda"
    DYNAMODB = "dynamodb"
    RDS = "rds"


class RequestStatus(str, Enum):
    """Request processing status"""
    SUBMITTED = "submitted"
    ANALYZING = "analyzing"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class RiskLevel(str, Enum):
    """Risk classification levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AccessRequest(BaseModel):
    """Emergency access request from user"""
    request_id: Optional[str] = None
    requester_email: EmailStr
    requester_name: str
    emergency_description: str = Field(..., min_length=10, max_length=1000)
    resource_type: ResourceType
    resource_id: str = Field(..., min_length=1, max_length=500)
    resource_region: str = Field(default="us-east-1")
    requested_action: str = Field(..., min_length=1, max_length=200)
    requested_permissions: Optional[List[str]] = None
    duration_minutes: int = Field(..., gt=0, le=120)
    business_justification: str = Field(..., min_length=10, max_length=2000)
    
    status: RequestStatus = RequestStatus.SUBMITTED
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    @validator("duration_minutes")
    def validate_duration(cls, v):
        """Validate session duration is reasonable"""
        if v < 5:
            raise ValueError("Duration must be at least 5 minutes")
        if v > 120:
            raise ValueError("Duration cannot exceed 120 minutes")
        return v
    
    @validator("emergency_description", "business_justification")
    def check_for_suspicious_content(cls, v):
        """Basic check for prompt injection attempts"""
        suspicious_phrases = [
            "ignore previous instructions",
            "ignore all instructions",
            "you are now",
            "system prompt",
            "override security",
            "disable security",
            "grant admin",
            "bypass approval"
        ]
        v_lower = v.lower()
        for phrase in suspicious_phrases:
            if phrase in v_lower:
                raise ValueError(f"Request contains suspicious content: '{phrase}'")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "requester_email": "engineer@company.com",
                "requester_name": "John Engineer",
                "emergency_description": "Production EC2 instance i-1234567890abcdef0 is unresponsive and causing application downtime",
                "resource_type": "ec2",
                "resource_id": "i-1234567890abcdef0",
                "resource_region": "us-east-1",
                "requested_action": "restart_instance",
                "duration_minutes": 30,
                "business_justification": "Customer-facing application is down. Need to restart the instance to restore service."
            }
        }


class AgentAnalysis(BaseModel):
    """AI agent's analysis of the access request"""
    request_id: str
    incident_summary: str
    risk_classification: RiskLevel
    risk_score: int = Field(..., ge=0, le=100)
    risk_explanation: str
    
    requested_permissions: List[str]
    recommended_permissions: List[str]
    recommended_template: Optional[str] = None
    
    affected_resources: List[str]
    potential_impact: str
    
    approval_required: bool
    approval_reason: str
    
    suspicious_indicators: List[str] = Field(default_factory=list)
    
    agent_decision: str  # "RECOMMEND_APPROVAL" or "RECOMMEND_REJECTION"
    agent_explanation: str
    
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_schema_extra = {
            "example": {
                "request_id": "req_abc123",
                "incident_summary": "Engineer needs to restart unresponsive EC2 instance",
                "risk_classification": "MEDIUM",
                "risk_score": 45,
                "risk_explanation": "Operational action on specific resource with limited scope",
                "requested_permissions": ["ec2:*"],
                "recommended_permissions": ["ec2:RebootInstances", "ec2:DescribeInstances"],
                "recommended_template": "ec2_restart",
                "affected_resources": ["i-1234567890abcdef0"],
                "potential_impact": "Instance will restart, brief service interruption",
                "approval_required": True,
                "approval_reason": "MEDIUM risk operations require human approval",
                "suspicious_indicators": [],
                "agent_decision": "RECOMMEND_APPROVAL",
                "agent_explanation": "Request is legitimate and narrowly scoped",
                "analyzed_at": "2024-01-15T10:30:00Z"
            }
        }


class BackendValidation(BaseModel):
    """Backend validation results"""
    request_id: str
    validation_passed: bool
    
    resource_allowed: bool
    resource_validation_message: str
    
    permissions_valid: bool
    permissions_validation_message: str
    
    duration_valid: bool
    duration_validation_message: str
    
    requester_authorized: bool
    requester_validation_message: str
    
    final_risk_level: RiskLevel
    backend_risk_score: int
    
    violations: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    validated_at: datetime = Field(default_factory=datetime.utcnow)


class AccessRequestFull(BaseModel):
    """Complete access request with analysis and validation"""
    request: AccessRequest
    agent_analysis: Optional[AgentAnalysis] = None
    backend_validation: Optional[BackendValidation] = None
    approval_id: Optional[str] = None
    session_id: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "request": {
                    "request_id": "req_abc123",
                    "requester_email": "engineer@company.com",
                    "requester_name": "John Engineer",
                    "emergency_description": "Production instance unresponsive",
                    "resource_type": "ec2",
                    "resource_id": "i-1234567890abcdef0",
                    "requested_action": "restart_instance",
                    "duration_minutes": 30,
                    "business_justification": "Application downtime affecting customers",
                    "status": "pending_approval"
                },
                "agent_analysis": {
                    "risk_classification": "MEDIUM",
                    "recommended_permissions": ["ec2:RebootInstances"],
                    "agent_decision": "RECOMMEND_APPROVAL"
                }
            }
        }


class RequestListResponse(BaseModel):
    """Paginated list of requests"""
    requests: List[AccessRequestFull]
    total: int
    page: int
    page_size: int
    has_more: bool


class RequestStatistics(BaseModel):
    """Dashboard statistics"""
    total_requests: int
    approved_requests: int
    rejected_requests: int
    pending_approvals: int
    active_sessions: int
    expired_sessions: int
    high_risk_requests: int
    critical_risk_requests: int
    prompt_injection_attempts: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_requests": 150,
                "approved_requests": 120,
                "rejected_requests": 20,
                "pending_approvals": 10,
                "active_sessions": 5,
                "expired_sessions": 115,
                "high_risk_requests": 15,
                "critical_risk_requests": 5,
                "prompt_injection_attempts": 3
            }
        }
