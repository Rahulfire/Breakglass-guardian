"""
Data models for audit events
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from enum import Enum


class EventType(str, Enum):
    """Types of auditable events"""
    REQUEST_SUBMITTED = "request_submitted"
    REQUEST_ANALYZED = "request_analyzed"
    APPROVAL_CREATED = "approval_created"
    APPROVAL_DECISION = "approval_decision"
    SESSION_CREATED = "session_created"
    SESSION_EXPIRED = "session_expired"
    SESSION_REVOKED = "session_revoked"
    PROMPT_INJECTION_DETECTED = "prompt_injection_detected"
    UNAUTHORIZED_ACCESS_ATTEMPT = "unauthorized_access_attempt"
    POLICY_VIOLATION = "policy_violation"
    PRIVILEGE_ESCALATION_ATTEMPT = "privilege_escalation_attempt"
    APPROVAL_BYPASS_ATTEMPT = "approval_bypass_attempt"
    SECURITY_ALERT = "security_alert"


class EventSeverity(str, Enum):
    """Event severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditEvent(BaseModel):
    """Comprehensive audit event record"""
    event_id: str
    event_type: EventType
    severity: EventSeverity
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Actor information
    actor_email: Optional[EmailStr] = None
    actor_name: Optional[str] = None
    actor_ip: Optional[str] = None
    
    # Related entities
    request_id: Optional[str] = None
    approval_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Resource information
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    
    # Event details
    event_description: str
    event_data: Optional[Dict[str, Any]] = None
    
    # Security information
    risk_level: Optional[str] = None
    security_flags: list[str] = Field(default_factory=list)
    
    # Agent interaction
    agent_involved: bool = False
    agent_decision: Optional[str] = None
    agent_reasoning: Optional[str] = None
    
    # Outcome
    outcome: str  # "SUCCESS", "FAILURE", "BLOCKED", "PENDING"
    outcome_reason: Optional[str] = None
    
    # Compliance
    policy_references: list[str] = Field(default_factory=list)
    compliance_tags: list[str] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "evt_123abc",
                "event_type": "request_submitted",
                "severity": "info",
                "timestamp": "2024-01-15T10:30:00Z",
                "actor_email": "engineer@company.com",
                "actor_name": "John Engineer",
                "request_id": "req_abc123",
                "resource_type": "ec2",
                "resource_id": "i-1234567890abcdef0",
                "event_description": "Emergency access request submitted",
                "risk_level": "MEDIUM",
                "agent_involved": True,
                "outcome": "SUCCESS"
            }
        }


class SecurityAlert(BaseModel):
    """High-priority security event"""
    alert_id: str
    alert_type: str
    severity: EventSeverity
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    title: str
    description: str
    
    # Related audit events
    related_event_ids: list[str]
    
    # Actor information
    suspected_actor_email: Optional[str] = None
    suspected_actor_ip: Optional[str] = None
    
    # Attack details
    attack_vector: Optional[str] = None
    attack_indicators: list[str] = Field(default_factory=list)
    
    # Response
    auto_blocked: bool
    manual_review_required: bool
    notified_security_team: bool
    
    # Resolution
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "alert_id": "alert_sec001",
                "alert_type": "prompt_injection",
                "severity": "critical",
                "timestamp": "2024-01-15T10:35:00Z",
                "title": "Prompt Injection Attempt Detected",
                "description": "User attempted to override system instructions",
                "related_event_ids": ["evt_123abc"],
                "suspected_actor_email": "attacker@example.com",
                "attack_vector": "malicious_prompt",
                "attack_indicators": [
                    "Contains 'ignore previous instructions'",
                    "Requests administrator access"
                ],
                "auto_blocked": True,
                "manual_review_required": True,
                "notified_security_team": True,
                "resolved": False
            }
        }


class AuditQuery(BaseModel):
    """Query parameters for audit log search"""
    event_types: Optional[list[EventType]] = None
    severity: Optional[EventSeverity] = None
    actor_email: Optional[str] = None
    request_id: Optional[str] = None
    resource_type: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    outcome: Optional[str] = None
    security_flags: Optional[list[str]] = None
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0, ge=0)


class AuditLogResponse(BaseModel):
    """Paginated audit log results"""
    events: list[AuditEvent]
    total: int
    page: int
    page_size: int
    has_more: bool
    
    class Config:
        json_schema_extra = {
            "example": {
                "events": [
                    {
                        "event_id": "evt_123abc",
                        "event_type": "request_submitted",
                        "severity": "info",
                        "actor_email": "engineer@company.com",
                        "outcome": "SUCCESS"
                    }
                ],
                "total": 150,
                "page": 1,
                "page_size": 50,
                "has_more": True
            }
        }


class AuditStatistics(BaseModel):
    """Audit trail statistics for dashboard"""
    total_events: int
    events_by_type: Dict[str, int]
    events_by_severity: Dict[str, int]
    security_alerts: int
    blocked_attempts: int
    
    # Time-based metrics
    events_last_24h: int
    events_last_7d: int
    events_last_30d: int
    
    # Top actors
    most_active_users: list[Dict[str, Any]]
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_events": 1500,
                "events_by_type": {
                    "request_submitted": 150,
                    "approval_created": 120,
                    "session_created": 100
                },
                "events_by_severity": {
                    "info": 1200,
                    "warning": 250,
                    "error": 40,
                    "critical": 10
                },
                "security_alerts": 15,
                "blocked_attempts": 8,
                "events_last_24h": 45,
                "events_last_7d": 320,
                "events_last_30d": 1500,
                "most_active_users": [
                    {"email": "engineer@company.com", "event_count": 25}
                ]
            }
        }
