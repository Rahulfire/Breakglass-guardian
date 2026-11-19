"""
API endpoints for audit log access
"""
from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from datetime import datetime

from backend.models.audit_event import (
    AuditEvent, AuditQuery, AuditLogResponse, AuditStatistics, SecurityAlert
)
from backend.services.audit_service import audit_service

router = APIRouter()


@router.get("/events", response_model=AuditLogResponse)
async def query_audit_events(
    event_type: Optional[str] = None,
    severity: Optional[str] = None,
    actor_email: Optional[str] = None,
    request_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Query audit events with filters.
    Provides complete forensic trail for security investigations.
    """
    query = AuditQuery(
        event_types=[event_type] if event_type else None,
        severity=severity,
        actor_email=actor_email,
        request_id=request_id,
        limit=limit,
        offset=offset
    )
    
    events = audit_service.query_events(query)
    total = len(audit_service._events)
    
    return AuditLogResponse(
        events=events,
        total=total,
        page=offset // limit + 1,
        page_size=limit,
        has_more=(offset + limit) < total
    )


@router.get("/alerts", response_model=List[SecurityAlert])
async def get_security_alerts(resolved: Optional[bool] = None):
    """
    Get security alerts.
    High-priority security events requiring review.
    """
    return audit_service.get_security_alerts(resolved=resolved)


@router.get("/statistics", response_model=AuditStatistics)
async def get_audit_statistics():
    """Get audit trail statistics for dashboard"""
    events = audit_service._events
    
    events_by_type = {}
    events_by_severity = {}
    
    for event in events:
        event_type = event.event_type.value
        severity = event.severity.value
        
        events_by_type[event_type] = events_by_type.get(event_type, 0) + 1
        events_by_severity[severity] = events_by_severity.get(severity, 0) + 1
    
    # Count security alerts
    security_alerts = len(audit_service.get_security_alerts())
    blocked_attempts = len([e for e in events if e.outcome == "BLOCKED"])
    
    # Time-based metrics
    now = datetime.utcnow()
    events_last_24h = len([e for e in events if (now - e.timestamp).total_seconds() < 86400])
    events_last_7d = len([e for e in events if (now - e.timestamp).days < 7])
    events_last_30d = len([e for e in events if (now - e.timestamp).days < 30])
    
    # Most active users
    user_counts = {}
    for event in events:
        if event.actor_email:
            user_counts[event.actor_email] = user_counts.get(event.actor_email, 0) + 1
    
    most_active_users = [
        {"email": email, "event_count": count}
        for email, count in sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    ]
    
    return AuditStatistics(
        total_events=len(events),
        events_by_type=events_by_type,
        events_by_severity=events_by_severity,
        security_alerts=security_alerts,
        blocked_attempts=blocked_attempts,
        events_last_24h=events_last_24h,
        events_last_7d=events_last_7d,
        events_last_30d=events_last_30d,
        most_active_users=most_active_users
    )
