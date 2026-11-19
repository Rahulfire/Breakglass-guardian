"""
Identity and authorization validation
"""
from typing import Tuple
from backend.config import settings


class IdentityValidator:
    """
    Validates user identities and authorizations.
    In production, integrate with your identity provider (AWS Cognito, Okta, etc.)
    """
    
    @staticmethod
    def validate_requester(email: str, name: str) -> Tuple[bool, str]:
        """
        Validate requester identity.
        
        Returns:
            Tuple of (is_valid, message)
        """
        # Basic email validation
        if not email or "@" not in email:
            return False, "Invalid email format"
        
        # Check for suspicious email patterns
        suspicious_domains = ["test.com", "example.com", "localhost"]
        domain = email.split("@")[1].lower() if "@" in email else ""
        
        if domain in suspicious_domains:
            return False, f"Suspicious email domain: {domain}"
        
        # In production: Verify against identity provider
        # For now: Basic validation
        if not name or len(name) < 2:
            return False, "Invalid requester name"
        
        return True, f"Requester identity validated: {email}"
    
    @staticmethod
    def validate_approver(email: str, name: str) -> Tuple[bool, str]:
        """
        Validate approver is authorized to approve requests.
        
        Returns:
            Tuple of (is_authorized, message)
        """
        # Normalize email for comparison
        email_normalized = email.lower().strip()
        
        # Check against authorized approvers list
        authorized_emails = [e.lower().strip() for e in settings.authorized_approvers]
        
        if email_normalized not in authorized_emails:
            return False, f"User {email} is not an authorized approver"
        
        # Basic name validation
        if not name or len(name) < 2:
            return False, "Invalid approver name"
        
        return True, f"Approver authorized: {email}"
    
    @staticmethod
    def check_self_approval(requester_email: str, approver_email: str) -> Tuple[bool, str]:
        """
        Check if requester and approver are the same person.
        
        Returns:
            Tuple of (is_different, message)
        """
        # Normalize emails
        requester = requester_email.lower().strip()
        approver = approver_email.lower().strip()
        
        if requester == approver:
            return False, "Self-approval is prohibited"
        
        # Check for alias attempts (simple check)
        requester_local, requester_domain = requester.split("@", 1)
        approver_local, approver_domain = approver.split("@", 1)
        requester_base = requester_local.split("+", 1)[0] + "@" + requester_domain
        approver_base = approver_local.split("+", 1)[0] + "@" + approver_domain
        
        if requester_base == approver_base:
            return False, "Self-approval via email alias is prohibited"
        
        return True, "Requester and approver are different users"
    
    @staticmethod
    def validate_mfa(user_email: str, mfa_code: str = None) -> Tuple[bool, str]:
        """
        Validate MFA if required for approvals.
        
        Returns:
            Tuple of (is_valid, message)
        """
        if not settings.require_mfa_for_approval:
            return True, "MFA not required"
        
        # In production: Integrate with MFA provider
        # For demo: Simple validation
        if not mfa_code:
            return False, "MFA code required for approval"
        
        # In production: Verify MFA code against user's MFA device
        # For now: Accept any 6-digit code as placeholder
        if len(mfa_code) == 6 and mfa_code.isdigit():
            return True, "MFA validated"
        
        return False, "Invalid MFA code"
