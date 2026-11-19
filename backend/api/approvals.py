"""
API endpoints for approval management
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
import uuid
from datetime import datetime

from backend.models.approval import (
    ApprovalRequest, ApprovalDecision, ApprovalStatus, PendingApprovalsList
)
from backend.security.approval_validator import ApprovalValidator
from backend.security.identity_validator import IdentityValidator
from backend.services.audit_service import audit_service
from backend.services.approval_service import approval_service
from backend.security.auth import require_role, Principal
from backend.config import settings

router = APIRouter()

# In-memory storage for demo
_approvals_store: dict[str, ApprovalRequest] = {}


@router.post("/", response_model=ApprovalRequest, status_code=status.HTTP_201_CREATED)
async def create_approval_request(
    approval: ApprovalRequest,
    _principal=Depends(require_role("internal")),
):
    """Reject direct creation; requests create approvals through the service layer."""
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Approval requests are created by request submission",
    )


@router.post("/{approval_id}/decide", response_model=ApprovalRequest)
async def make_approval_decision(
    approval_id: str,
    decision: ApprovalDecision,
    principal: Principal = Depends(require_role("approver", "admin")),
):
    """
    Approve or reject a request.
    This endpoint enforces all security rules.
    """
    # Get approval
    approval = approval_service.get_approval(approval_id)
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval {approval_id} not found"
        )
    
    if decision.approval_id != approval_id:
        raise HTTPException(status_code=400, detail="Approval ID does not match path")
    if (settings.auth_enabled or not settings.use_local_mode) and decision.approver_email.lower() != principal.email:
        raise HTTPException(status_code=403, detail="Approver identity does not match token")
    
    # Verify approver is authorized
    approver_valid, approver_msg = IdentityValidator.validate_approver(
        decision.approver_email,
        decision.approver_name
    )
    
    if not approver_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=approver_msg
        )

    if settings.require_mfa_for_approval and not decision.mfa_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="MFA verification is required for approval decisions",
        )
    
    # Prevent self-approval
    self_approval_valid, self_approval_msg = IdentityValidator.check_self_approval(
        approval.requester_email,
        decision.approver_email
    )
    
    if not self_approval_valid:
        audit_service.log_approval_bypass_attempt(
            request_id=approval.request_id,
            actor_email=decision.approver_email,
            reason=self_approval_msg
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=self_approval_msg
        )
    
    # Update approval
    try:
        approval = approval_service.process_approval_decision(approval_id, decision)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    
    # Log decision
    audit_service.log_approval_decision(
        approval_id=approval_id,
        request_id=approval.request_id,
        approver_email=decision.approver_email,
        approver_name=decision.approver_name,
        decision=decision.decision,
        reason=decision.reason
    )
    
    return approval


@router.get("/pending", response_model=PendingApprovalsList)
async def get_pending_approvals():
    """Get all pending approval requests"""
    pending = approval_service.get_pending_approvals()
    pending.sort(key=lambda a: a.created_at, reverse=True)
    
    return PendingApprovalsList(
        approvals=pending,
        total=len(pending)
    )


@router.get("/{approval_id}", response_model=ApprovalRequest)
async def get_approval(approval_id: str):
    """Get approval details"""
    approval = approval_service.get_approval(approval_id)
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval {approval_id} not found"
        )
    
    return approval
