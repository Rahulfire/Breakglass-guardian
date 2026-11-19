"""
Approval workflow service
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, List

from backend.models.approval import (
    ApprovalRequest, ApprovalDecision, ApprovalStatus
)
from backend.models.access_request import AccessRequest, AgentAnalysis
from backend.security.approval_validator import ApprovalValidator
from backend.config import settings
from backend.services.audit_service import audit_service
from backend.storage import DynamoRepository


class ApprovalService:
    """
    Service for managing the approval workflow.
    Creates, updates, and validates approval requests.
    """
    
    def __init__(self):
        """Initialize approval service"""
        # In production: Initialize DynamoDB client
        self._approvals: dict[str, ApprovalRequest] = {}  # In-memory for demo
        self._repository = DynamoRepository(settings.dynamodb_approvals_table, "approval_id")
    
    def create_approval_request(
        self,
        request: AccessRequest,
        analysis: AgentAnalysis
    ) -> ApprovalRequest:
        """
        Create a new approval request from an access request and AI analysis.
        
        Args:
            request: The original access request
            analysis: AI agent's analysis
            
        Returns:
            Created ApprovalRequest
        """
        approval_id = f"appr_{uuid.uuid4().hex[:12]}"
        
        # Compute request hash for integrity verification
        request_hash = ApprovalValidator.compute_request_hash(request)
        
        # Calculate expiration time
        expires_at = ApprovalValidator.calculate_approval_expiration()
        
        approval = ApprovalRequest(
            approval_id=approval_id,
            request_id=request.request_id,
            requester_email=request.requester_email,
            requester_name=request.requester_name,
            emergency_description=request.emergency_description,
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            requested_action=request.requested_action,
            duration_minutes=request.duration_minutes,
            business_justification=request.business_justification,
            risk_classification=analysis.risk_classification,
            risk_score=analysis.risk_score,
            recommended_permissions=analysis.recommended_permissions,
            agent_recommendation=analysis.agent_decision,
            risk_explanation=analysis.risk_explanation,
            status=ApprovalStatus.PENDING,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            request_hash=request_hash
        )
        
        # Store approval
        self._approvals[approval_id] = approval
        self._repository.put(approval, approval_id)
        audit_service.log_approval_created(
            approval_id=approval_id,
            request_id=request.request_id,
            risk_level=analysis.risk_classification,
        )
        
        return approval
    
    def get_approval(self, approval_id: str) -> Optional[ApprovalRequest]:
        """Get approval by ID"""
        # In production: Query DynamoDB
        approval = self._approvals.get(approval_id)
        if approval is None:
            approval = self._repository.get(approval_id, ApprovalRequest)
            if approval is not None:
                self._approvals[approval_id] = approval
        return approval
    
    def get_pending_approvals(self) -> List[ApprovalRequest]:
        """Get all pending approval requests"""
        # In production: Query DynamoDB with GSI on status
        pending = [
            approval for approval in self._approvals.values()
            if approval.status == ApprovalStatus.PENDING
        ]
        
        # Sort by creation time (oldest first)
        pending.sort(key=lambda a: a.created_at)
        
        return pending
    
    def process_approval_decision(
        self,
        approval_id: str,
        decision: ApprovalDecision
    ) -> ApprovalRequest:
        """
        Process an approval decision (approve or reject).
        
        Args:
            approval_id: ID of approval to decide on
            decision: The approval decision
            
        Returns:
            Updated ApprovalRequest
        """
        approval = self.get_approval(approval_id)
        
        if not approval:
            raise ValueError(f"Approval {approval_id} not found")
        
        # Validate approval is still pending
        if approval.status != ApprovalStatus.PENDING:
            raise ValueError(f"Approval is already {approval.status}")
        
        # Check expiration
        if datetime.utcnow() > approval.expires_at:
            approval.status = ApprovalStatus.EXPIRED
            raise ValueError("Approval has expired")
        
        # Update approval with decision
        approval.approver_email = decision.approver_email
        approval.approver_name = decision.approver_name
        approval.approval_decision = decision.decision
        approval.approval_reason = decision.reason
        approval.approved_at = datetime.utcnow()
        
        # Update status
        if decision.decision == "APPROVED":
            approval.status = ApprovalStatus.APPROVED
        else:
            approval.status = ApprovalStatus.REJECTED
        
        # In production: Update DynamoDB
        self._approvals[approval_id] = approval
        self._repository.put(approval, approval_id)
        audit_service.log_approval_decision(
            approval_id=approval_id,
            request_id=approval.request_id,
            approver_email=decision.approver_email,
            approver_name=decision.approver_name,
            decision=decision.decision,
            reason=decision.reason,
        )
        
        return approval
    
    def mark_approval_used(self, approval_id: str) -> bool:
        """
        Mark an approval as used (prevents replay attacks).
        
        Returns:
            True if successfully marked
        """
        approval = self.get_approval(approval_id)
        
        if not approval:
            return False
        
        if approval.used:
            raise ValueError("Approval has already been used")
        
        approval.used = True
        approval.used_at = datetime.utcnow()
        
        # In production: Update DynamoDB
        self._approvals[approval_id] = approval
        self._repository.update_fields(
            approval_id,
            {"used": True, "used_at": approval.used_at.isoformat()},
            "used = :unused",
        )
        
        return True
    
    def check_approval_valid(
        self,
        approval_id: str,
        current_request: AccessRequest
    ) -> tuple[bool, List[str]]:
        """
        Check if an approval is valid for use.
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        approval = self.get_approval(approval_id)
        
        if not approval:
            return False, ["Approval not found"]
        
        errors = []
        
        # Check status
        if approval.status != ApprovalStatus.APPROVED:
            errors.append(f"Approval status is {approval.status}, not APPROVED")
        
        # Check expiration
        if datetime.utcnow() > approval.expires_at:
            errors.append("Approval has expired")
        
        # Check if already used
        if approval.used:
            errors.append("Approval has already been used")
        
        # Verify request authenticity
        authentic, msg = ApprovalValidator.verify_approval_authenticity(
            approval, current_request
        )
        if not authentic:
            errors.append(msg)
        
        return len(errors) == 0, errors
    
    def expire_old_approvals(self) -> int:
        """
        Expire approvals that have passed their expiration time.
        Should be run periodically.
        
        Returns:
            Number of approvals expired
        """
        now = datetime.utcnow()
        expired_count = 0
        
        for approval in self._approvals.values():
            if approval.status == ApprovalStatus.PENDING and now > approval.expires_at:
                approval.status = ApprovalStatus.EXPIRED
                expired_count += 1
        
        return expired_count
    
    def get_approval_statistics(self) -> dict:
        """Get statistics about approvals"""
        total = len(self._approvals)
        pending = sum(1 for a in self._approvals.values() if a.status == ApprovalStatus.PENDING)
        approved = sum(1 for a in self._approvals.values() if a.status == ApprovalStatus.APPROVED)
        rejected = sum(1 for a in self._approvals.values() if a.status == ApprovalStatus.REJECTED)
        expired = sum(1 for a in self._approvals.values() if a.status == ApprovalStatus.EXPIRED)
        
        return {
            "total": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "expired": expired
        }


# Global approval service instance
approval_service = ApprovalService()
