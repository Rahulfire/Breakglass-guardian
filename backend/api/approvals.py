"""
API endpoints for approval management
"""
from fastapi import APIRouter, HTTPException, status
from typing import List
import uuid
from datetime import datetime

from backend.models.approval import (
    ApprovalRequest, ApprovalDecision, ApprovalStatus, PendingApprovalsList
)
from backend.security.approval_validator import ApprovalValidator
from backend.security.identity_validator import IdentityValidator
from backend.services.audit_service import audit_service

router = APIRouter()

# In-memory storage for demo
_approvals_store: dict[str, ApprovalRequest] = {}


@router.post("/", response_model=ApprovalRequest, status_code=status.HTTP_201_CREATED)
async def create_approval_request(approval: ApprovalRequest):
    """Create a new approval request (called by system, not users)"""
    _approvals_store[approval.approval_id] = approval
    
    audit_service.log_approval_created(
        approval_id=approval.approval_id,
        request_id=approval.request_id,
        risk_level=approval.risk_classification
    )
    
    return approval


@router.post("/{approval_id}/decide", response_model=ApprovalRequest)
async def make_approval_decision(approval_id: str, decision: ApprovalDecision):
    """
    Approve or reject a request.
    This endpoint enforces all security rules.
    """
    # Get approval
    if approval_id not in _approvals_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval {approval_id} not found"
        )
    
    approval = _approvals_store[approval_id]
    
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
    approval.approver_email = decision.approver_email
    approval.approver_name = decision.approver_name
    approval.approval_decision = decision.decision
    approval.approval_reason = decision.reason
    approval.approved_at = datetime.utcnow()
    approval.status = ApprovalStatus.APPROVED if decision.decision == "APPROVED" else ApprovalStatus.REJECTED
    
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
    pending = [a for a in _approvals_store.values() if a.status == ApprovalStatus.PENDING]
    pending.sort(key=lambda a: a.created_at, reverse=True)
    
    return PendingApprovalsList(
        approvals=pending,
        total=len(pending)
    )


@router.get("/{approval_id}", response_model=ApprovalRequest)
async def get_approval(approval_id: str):
    """Get approval details"""
    if approval_id not in _approvals_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Approval {approval_id} not found"
        )
    
    return _approvals_store[approval_id]
