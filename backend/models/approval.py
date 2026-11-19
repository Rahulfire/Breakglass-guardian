"""
Data models for approval workflow
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr, validator
from enum import Enum


class ApprovalStatus(str, Enum):
    """Approval decision status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalRequest(BaseModel):
    """Approval request awaiting human decision"""
    approval_id: str
    request_id: str
    
    # Request context for approver
    requester_email: EmailStr
    requester_name: str
    emergency_description: str
    resource_type: str
    resource_id: str
    requested_action: str
    duration_minutes: int
    business_justification: str
    
    # AI analysis for approver review
    risk_classification: str
    risk_score: int
    recommended_permissions: list[str]
    agent_recommendation: str
    risk_explanation: str
    
    # Approval status
    status: ApprovalStatus = ApprovalStatus.PENDING
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    
    # Approval decision (filled when approved/rejected)
    approver_email: Optional[EmailStr] = None
    approver_name: Optional[str] = None
    approval_decision: Optional[str] = None  # "APPROVED" or "REJECTED"
    approval_reason: Optional[str] = None
    approved_at: Optional[datetime] = None
    
    # Security tracking
    used: bool = False  # Prevent replay attacks
    used_at: Optional[datetime] = None
    request_hash: str  # Hash of request parameters to prevent tampering
    
    class Config:
        json_schema_extra = {
            "example": {
                "approval_id": "appr_xyz789",
                "request_id": "req_abc123",
                "requester_email": "engineer@company.com",
                "requester_name": "John Engineer",
                "emergency_description": "Production EC2 instance unresponsive",
                "resource_type": "ec2",
                "resource_id": "i-1234567890abcdef0",
                "requested_action": "restart_instance",
                "duration_minutes": 30,
                "business_justification": "Customer-facing application down",
                "risk_classification": "MEDIUM",
                "risk_score": 45,
                "recommended_permissions": ["ec2:RebootInstances"],
                "agent_recommendation": "RECOMMEND_APPROVAL",
                "risk_explanation": "Narrowly scoped operational action",
                "status": "pending",
                "created_at": "2024-01-15T10:30:00Z",
                "expires_at": "2024-01-15T11:30:00Z"
            }
        }


class ApprovalDecision(BaseModel):
    """Approver's decision on a request"""
    approval_id: str
    approver_email: EmailStr
    approver_name: str
    decision: str  # "APPROVED" or "REJECTED"
    reason: str = Field(..., min_length=10, max_length=500)
    mfa_verified: bool = False
    
    @validator("decision")
    def validate_decision(cls, v):
        """Ensure decision is valid"""
        if v not in ["APPROVED", "REJECTED"]:
            raise ValueError("Decision must be APPROVED or REJECTED")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "approval_id": "appr_xyz789",
                "approver_email": "admin@company.com",
                "approver_name": "Admin User",
                "decision": "APPROVED",
                "reason": "Emergency justified, permissions appropriate",
                "mfa_verified": True
            }
        }


class ApprovalValidationResult(BaseModel):
    """Result of approval validation"""
    valid: bool
    approval_id: str
    
    approval_exists: bool
    approval_status: Optional[str] = None
    approval_expired: bool
    approval_used: bool
    approver_authorized: bool
    request_matches: bool
    
    validation_message: str
    errors: list[str] = Field(default_factory=list)
    
    validated_at: datetime = Field(default_factory=datetime.utcnow)


class PendingApprovalsList(BaseModel):
    """List of pending approvals for dashboard"""
    approvals: list[ApprovalRequest]
    total: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "approvals": [
                    {
                        "approval_id": "appr_xyz789",
                        "request_id": "req_abc123",
                        "requester_email": "engineer@company.com",
                        "risk_classification": "MEDIUM",
                        "status": "pending"
                    }
                ],
                "total": 5
            }
        }
