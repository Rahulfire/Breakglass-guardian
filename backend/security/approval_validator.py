"""
Approval validation and verification
"""
import hashlib
import json
from datetime import datetime, timedelta
from typing import Tuple, Optional
from backend.models.approval import ApprovalRequest, ApprovalStatus
from backend.models.access_request import AccessRequest
from backend.security.identity_validator import IdentityValidator
from backend.config import settings


class ApprovalValidator:
    """
    Validates approval authenticity and prevents tampering.
    """
    
    @staticmethod
    def compute_request_hash(request: AccessRequest) -> str:
        """
        Compute hash of request parameters to prevent tampering.
        
        Returns:
            SHA-256 hash of critical request fields
        """
        # Include all fields that must match between request and approval
        hash_data = {
            "requester_email": request.requester_email,
            "resource_type": request.resource_type,
            "resource_id": request.resource_id,
            "requested_action": request.requested_action,
            "duration_minutes": request.duration_minutes
        }
        
        # Sort keys for consistent hashing
        hash_string = json.dumps(hash_data, sort_keys=True)
        
        return hashlib.sha256(hash_string.encode()).hexdigest()
    
    @staticmethod
    def verify_approval_authenticity(
        approval: ApprovalRequest,
        current_request: AccessRequest
    ) -> Tuple[bool, str]:
        """
        Verify approval matches the current request exactly.
        
        Returns:
            Tuple of (is_authentic, message)
        """
        # Compute current request hash
        current_hash = ApprovalValidator.compute_request_hash(current_request)
        
        # Compare with stored hash
        if approval.request_hash != current_hash:
            return False, "Approval does not match current request parameters"
        
        # Verify critical fields match exactly
        mismatches = []
        
        if approval.requester_email != current_request.requester_email:
            mismatches.append("requester_email")
        
        if approval.resource_type != current_request.resource_type:
            mismatches.append("resource_type")
        
        if approval.resource_id != current_request.resource_id:
            mismatches.append("resource_id")
        
        if approval.requested_action != current_request.requested_action:
            mismatches.append("requested_action")
        
        if approval.duration_minutes != current_request.duration_minutes:
            mismatches.append("duration_minutes")
        
        if mismatches:
            return False, f"Request parameters modified after approval: {', '.join(mismatches)}"
        
        return True, "Approval authentically matches request"
    
    @staticmethod
    def check_approval_expiration(approval: ApprovalRequest) -> Tuple[bool, str]:
        """
        Check if approval has expired.
        
        Returns:
            Tuple of (is_valid, message)
        """
        now = datetime.utcnow()
        
        if now > approval.expires_at:
            expired_minutes = int((now - approval.expires_at).total_seconds() / 60)
            return False, f"Approval expired {expired_minutes} minutes ago"
        
        remaining_minutes = int((approval.expires_at - now).total_seconds() / 60)
        return True, f"Approval valid for {remaining_minutes} more minutes"
    
    @staticmethod
    def check_approval_used(approval: ApprovalRequest) -> Tuple[bool, str]:
        """
        Check if approval has already been used (prevent replay).
        
        Returns:
            Tuple of (is_unused, message)
        """
        if approval.used:
            if approval.used_at:
                used_minutes = int((datetime.utcnow() - approval.used_at).total_seconds() / 60)
                return False, f"Approval already used {used_minutes} minutes ago"
            return False, "Approval has already been used"
        
        return True, "Approval has not been used"
    
    @staticmethod
    def verify_approver_authorization(approver_email: str, approver_name: str) -> Tuple[bool, str]:
        """
        Verify approver is authorized.
        
        Returns:
            Tuple of (is_authorized, message)
        """
        return IdentityValidator.validate_approver(approver_email, approver_name)
    
    @staticmethod
    def prevent_self_approval(
        requester_email: str,
        approver_email: str
    ) -> Tuple[bool, str]:
        """
        Prevent self-approval attempts.
        
        Returns:
            Tuple of (is_different, message)
        """
        return IdentityValidator.check_self_approval(requester_email, approver_email)
    
    @staticmethod
    def validate_complete_approval(
        approval: ApprovalRequest,
        current_request: AccessRequest,
        approver_email: str,
        approver_name: str
    ) -> Tuple[bool, list[str]]:
        """
        Perform complete approval validation.
        
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        
        # Check approval status
        if approval.status != ApprovalStatus.APPROVED:
            errors.append(f"Approval status is {approval.status}, not APPROVED")
        
        # Check expiration
        expiration_valid, expiration_msg = ApprovalValidator.check_approval_expiration(approval)
        if not expiration_valid:
            errors.append(expiration_msg)
        
        # Check if already used
        unused_valid, unused_msg = ApprovalValidator.check_approval_used(approval)
        if not unused_valid:
            errors.append(unused_msg)
        
        # Verify authenticity
        authentic_valid, authentic_msg = ApprovalValidator.verify_approval_authenticity(
            approval, current_request
        )
        if not authentic_valid:
            errors.append(authentic_msg)
        
        # Verify approver authorization
        approver_valid, approver_msg = ApprovalValidator.verify_approver_authorization(
            approver_email, approver_name
        )
        if not approver_valid:
            errors.append(approver_msg)
        
        # Prevent self-approval
        self_approval_valid, self_approval_msg = ApprovalValidator.prevent_self_approval(
            current_request.requester_email, approver_email
        )
        if not self_approval_valid:
            errors.append(self_approval_msg)
        
        return len(errors) == 0, errors
    
    @staticmethod
    def calculate_approval_expiration() -> datetime:
        """Calculate expiration time for new approval"""
        return datetime.utcnow() + timedelta(minutes=settings.approval_expiration_minutes)
