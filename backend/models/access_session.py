"""
Data models for temporary access sessions
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from enum import Enum


class SessionStatus(str, Enum):
    """Session lifecycle status"""
    CREATING = "creating"
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    FAILED = "failed"


class AccessSession(BaseModel):
    """Temporary AWS access session"""
    session_id: str
    request_id: str
    approval_id: str
    
    # User information
    requester_email: EmailStr
    requester_name: str
    
    # AWS resource details
    resource_type: str
    resource_id: str
    resource_region: str
    aws_account_id: str
    
    # Permissions granted
    granted_permissions: list[str]
    permission_template: Optional[str] = None
    iam_role_arn: Optional[str] = None
    
    # Session lifecycle
    status: SessionStatus = SessionStatus.CREATING
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime
    duration_minutes: int
    
    # AWS STS details (credentials not stored, only metadata)
    sts_session_name: Optional[str] = None
    assumed_role_id: Optional[str] = None
    
    # Session revocation
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[str] = None
    revocation_reason: Optional[str] = None
    
    # Audit trail reference
    audit_event_ids: list[str] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_def456",
                "request_id": "req_abc123",
                "approval_id": "appr_xyz789",
                "requester_email": "engineer@company.com",
                "requester_name": "John Engineer",
                "resource_type": "ec2",
                "resource_id": "i-1234567890abcdef0",
                "resource_region": "us-east-1",
                "aws_account_id": "123456789012",
                "granted_permissions": ["ec2:RebootInstances", "ec2:DescribeInstances"],
                "permission_template": "ec2_restart",
                "status": "active",
                "created_at": "2024-01-15T11:00:00Z",
                "expires_at": "2024-01-15T11:30:00Z",
                "duration_minutes": 30
            }
        }


class TemporaryCredentials(BaseModel):
    """AWS STS temporary credentials (returned once, never stored)"""
    session_id: str
    access_key_id: str
    secret_access_key: str
    session_token: str
    expiration: datetime
    region: str
    
    # Usage instructions
    granted_permissions: list[str]
    resource_scope: str
    
    # Security reminder
    security_notice: str = (
        "These credentials are temporary and will expire automatically. "
        "They are scoped to specific resources and actions. "
        "All operations are audited. Do not share these credentials."
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_def456",
                "access_key_id": "ASIA...",
                "secret_access_key": "***",
                "session_token": "***",
                "expiration": "2024-01-15T11:30:00Z",
                "region": "us-east-1",
                "granted_permissions": ["ec2:RebootInstances"],
                "resource_scope": "i-1234567890abcdef0"
            }
        }


class SessionRevocation(BaseModel):
    """Request to revoke an active session"""
    session_id: str
    revoked_by_email: EmailStr
    revoked_by_name: str
    revocation_reason: str = Field(..., min_length=10, max_length=500)
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_def456",
                "revoked_by_email": "admin@company.com",
                "revoked_by_name": "Admin User",
                "revocation_reason": "Emergency resolved, access no longer needed"
            }
        }


class ActiveSessionsList(BaseModel):
    """List of active sessions for monitoring"""
    sessions: list[AccessSession]
    total: int
    active_count: int
    expiring_soon_count: int  # Sessions expiring in next 15 minutes
    
    class Config:
        json_schema_extra = {
            "example": {
                "sessions": [
                    {
                        "session_id": "sess_def456",
                        "requester_email": "engineer@company.com",
                        "resource_id": "i-1234567890abcdef0",
                        "status": "active",
                        "expires_at": "2024-01-15T11:30:00Z"
                    }
                ],
                "total": 10,
                "active_count": 5,
                "expiring_soon_count": 2
            }
        }


class SessionStatistics(BaseModel):
    """Session analytics"""
    total_sessions: int
    active_sessions: int
    expired_sessions: int
    revoked_sessions: int
    average_duration_minutes: float
    most_common_resource_type: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_sessions": 150,
                "active_sessions": 5,
                "expired_sessions": 140,
                "revoked_sessions": 5,
                "average_duration_minutes": 45.5,
                "most_common_resource_type": "ec2"
            }
        }
