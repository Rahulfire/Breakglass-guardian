"""
API endpoints for session management
"""
from fastapi import APIRouter, HTTPException, status
from typing import List
import uuid
from datetime import datetime, timedelta

from backend.models.access_session import (
    AccessSession, SessionStatus, ActiveSessionsList, SessionRevocation
)
from backend.services.audit_service import audit_service

router = APIRouter()

# In-memory storage for demo
_sessions_store: dict[str, AccessSession] = {}


@router.post("/", response_model=AccessSession, status_code=status.HTTP_201_CREATED)
async def create_session(session: AccessSession):
    """
    Create a new access session (called by system after approval).
    In production: This would call AWS STS to generate temporary credentials.
    """
    _sessions_store[session.session_id] = session
    
    audit_service.log_session_created(
        session_id=session.session_id,
        request_id=session.request_id,
        approval_id=session.approval_id,
        requester_email=session.requester_email,
        resource_type=session.resource_type,
        resource_id=session.resource_id,
        granted_permissions=session.granted_permissions,
        duration_minutes=session.duration_minutes
    )
    
    return session


@router.get("/", response_model=ActiveSessionsList)
async def list_sessions(status_filter: str = None):
    """List all sessions with optional status filter"""
    sessions = list(_sessions_store.values())
    
    if status_filter:
        sessions = [s for s in sessions if s.status == status_filter]
    
    # Check for expiring sessions
    now = datetime.utcnow()
    expiring_soon = [s for s in sessions if s.status == SessionStatus.ACTIVE and (s.expires_at - now) < timedelta(minutes=15)]
    
    active = [s for s in sessions if s.status == SessionStatus.ACTIVE]
    
    return ActiveSessionsList(
        sessions=sessions,
        total=len(sessions),
        active_count=len(active),
        expiring_soon_count=len(expiring_soon)
    )


@router.get("/{session_id}", response_model=AccessSession)
async def get_session(session_id: str):
    """Get session details"""
    if session_id not in _sessions_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    return _sessions_store[session_id]


@router.post("/{session_id}/revoke", response_model=AccessSession)
async def revoke_session(session_id: str, revocation: SessionRevocation):
    """Manually revoke an active session"""
    if session_id not in _sessions_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    session = _sessions_store[session_id]
    
    if session.status != SessionStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot revoke session with status {session.status}"
        )
    
    # Update session
    session.status = SessionStatus.REVOKED
    session.revoked_at = datetime.utcnow()
    session.revoked_by = revocation.revoked_by_email
    session.revocation_reason = revocation.revocation_reason
    
    # Log revocation
    audit_service.log_event(
        event_type=audit_service.log_event.__self__.__class__.__module__,
        severity="INFO",
        event_description=f"Session {session_id} revoked by {revocation.revoked_by_name}",
        actor_email=revocation.revoked_by_email,
        session_id=session_id,
        outcome="SUCCESS"
    )
    
    return session
