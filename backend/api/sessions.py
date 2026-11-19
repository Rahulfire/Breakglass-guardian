"""
API endpoints for session management
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
import uuid
from datetime import datetime, timedelta

from backend.models.access_session import (
    AccessSession, SessionStatus, ActiveSessionsList, SessionRevocation
)
from backend.services.audit_service import audit_service
from backend.models.audit_event import EventType, EventSeverity
from backend.security.auth import require_role, Principal
from backend.services.approval_service import approval_service
from backend.security.approval_validator import ApprovalValidator
from backend.api.requests import get_request_record
from backend.config import settings
from backend.storage import DynamoRepository
from backend.services.session_service import session_service

router = APIRouter()

# In-memory storage for demo
_sessions_store: dict[str, AccessSession] = {}
_sessions_repository = DynamoRepository(settings.dynamodb_sessions_table, "session_id")


@router.post("/", response_model=AccessSession, status_code=status.HTTP_201_CREATED)
async def create_session(
    session: AccessSession,
    _principal=Depends(require_role("internal", "admin")),
):
    """
    Create a new access session (called by system after approval).
    In production: This would call AWS STS to generate temporary credentials.
    """
    request_full = get_request_record(session.request_id)
    approval = approval_service.get_approval(session.approval_id)
    if request_full is None or approval is None:
        raise HTTPException(status_code=404, detail="Request or approval not found")
    valid, errors = ApprovalValidator.validate_complete_approval(
        approval,
        request_full.request,
        approval.approver_email or "",
        approval.approver_name or "",
    )
    if not valid:
        raise HTTPException(status_code=409, detail={"errors": errors})
    if session.requester_email != request_full.request.requester_email:
        raise HTTPException(status_code=400, detail="Session requester does not match request")
    if session.granted_permissions != approval.recommended_permissions:
        raise HTTPException(status_code=400, detail="Session permissions do not match approval")
    if settings.use_local_mode:
        session.status = SessionStatus.ACTIVE
    else:
        try:
            aws_session, _credentials = session_service.create_session(
                request_full.request,
                approval,
                session.granted_permissions,
            )
            aws_session.session_id = session.session_id
            session = aws_session
        except RuntimeError as exc:
            session.status = SessionStatus.FAILED
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Temporary AWS session could not be created safely: {exc}",
            ) from exc
    _sessions_store[session.session_id] = session
    _sessions_repository.put(session, session.session_id)
    approval_service.mark_approval_used(session.approval_id)
    
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
        stored_session = _sessions_repository.get(session_id, AccessSession)
        if stored_session is not None:
            _sessions_store[session_id] = stored_session
    if session_id not in _sessions_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    return _sessions_store[session_id]


@router.post("/{session_id}/revoke", response_model=AccessSession)
async def revoke_session(
    session_id: str,
    revocation: SessionRevocation,
    principal: Principal = Depends(require_role("approver", "admin")),
):
    """Manually revoke an active session"""
    if session_id not in _sessions_store:
        stored_session = _sessions_repository.get(session_id, AccessSession)
        if stored_session is not None:
            _sessions_store[session_id] = stored_session
    if session_id not in _sessions_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found"
        )
    
    session = _sessions_store[session_id]
    if (settings.auth_enabled or not settings.use_local_mode) and revocation.revoked_by_email.lower() != principal.email:
        raise HTTPException(status_code=403, detail="Revoker identity does not match token")
    
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
    _sessions_repository.put(session, session.session_id)
    
    # Log revocation
    audit_service.log_event(
        event_type=EventType.SESSION_REVOKED,
        severity=EventSeverity.INFO,
        event_description=f"Session {session_id} revoked by {revocation.revoked_by_name}",
        actor_email=revocation.revoked_by_email,
        session_id=session_id,
        outcome="SUCCESS"
    )
    
    return session
