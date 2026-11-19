"""
Session management service
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, List

from backend.models.access_session import (
    AccessSession, SessionStatus, TemporaryCredentials
)
from backend.models.access_request import AccessRequest
from backend.models.approval import ApprovalRequest
from backend.services.sts_service import sts_service
from backend.services.iam_service import iam_service
from backend.config import settings


class SessionService:
    """
    Service for managing temporary access sessions.
    Creates, tracks, and expires sessions.
    """
    
    def __init__(self):
        """Initialize session service"""
        # In production: Initialize DynamoDB client
        self._sessions: dict[str, AccessSession] = {}  # In-memory for demo
    
    def create_session(
        self,
        request: AccessRequest,
        approval: ApprovalRequest,
        granted_permissions: List[str]
    ) -> tuple[AccessSession, TemporaryCredentials]:
        """
        Create a new access session and generate temporary credentials.
        
        Args:
            request: Original access request
            approval: Approved approval request
            granted_permissions: List of granted IAM permissions
            
        Returns:
            Tuple of (AccessSession, TemporaryCredentials)
        """
        session_id = f"sess_{uuid.uuid4().hex[:12]}"
        
        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(minutes=request.duration_minutes)
        
        # Get appropriate IAM role
        role_arn = iam_service.get_restricted_role_for_template(
            approval.recommended_permissions[0] if approval.recommended_permissions else "default"
        )
        
        # Build resource ARN
        resource_arn = iam_service.build_resource_arn(
            request.resource_type,
            request.resource_id,
            request.resource_region
        )
        
        # Create session record
        session = AccessSession(
            session_id=session_id,
            request_id=request.request_id,
            approval_id=approval.approval_id,
            requester_email=request.requester_email,
            requester_name=request.requester_name,
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            resource_region=request.resource_region,
            aws_account_id=settings.aws_account_id,
            granted_permissions=granted_permissions,
            permission_template=getattr(approval, 'recommended_template', None),
            iam_role_arn=role_arn,
            status=SessionStatus.CREATING,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            duration_minutes=request.duration_minutes,
            sts_session_name=f"breakglass-{request.requester_email.split('@')[0]}-{session_id}"
        )
        
        try:
            # Generate temporary credentials
            credentials = sts_service.generate_temporary_credentials(
                session_id=session_id,
                role_arn=role_arn,
                session_name=session.sts_session_name,
                duration_minutes=request.duration_minutes,
                permissions=granted_permissions,
                resource_arn=resource_arn
            )
            
            # Update session status
            session.status = SessionStatus.ACTIVE
            session.assumed_role_id = credentials.access_key_id  # For tracking
            
        except Exception as e:
            session.status = SessionStatus.FAILED
            raise RuntimeError(f"Failed to create session: {str(e)}")
        
        # Store session
        self._sessions[session_id] = session
        
        return session, credentials
    
    def get_session(self, session_id: str) -> Optional[AccessSession]:
        """Get session by ID"""
        # In production: Query DynamoDB
        return self._sessions.get(session_id)
    
    def get_active_sessions(self) -> List[AccessSession]:
        """Get all active sessions"""
        # In production: Query DynamoDB with GSI on status
        return [
            session for session in self._sessions.values()
            if session.status == SessionStatus.ACTIVE
        ]
    
    def get_sessions_by_requester(self, requester_email: str) -> List[AccessSession]:
        """Get all sessions for a specific requester"""
        # In production: Query DynamoDB with GSI on requester_email
        return [
            session for session in self._sessions.values()
            if session.requester_email == requester_email
        ]
    
    def revoke_session(
        self,
        session_id: str,
        revoked_by: str,
        reason: str
    ) -> AccessSession:
        """
        Manually revoke an active session.
        
        Args:
            session_id: Session to revoke
            revoked_by: Email of person revoking
            reason: Reason for revocation
            
        Returns:
            Updated AccessSession
        """
        session = self.get_session(session_id)
        
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if session.status != SessionStatus.ACTIVE:
            raise ValueError(f"Cannot revoke session with status {session.status}")
        
        # Update session
        session.status = SessionStatus.REVOKED
        session.revoked_at = datetime.utcnow()
        session.revoked_by = revoked_by
        session.revocation_reason = reason
        
        # In production: Update DynamoDB
        self._sessions[session_id] = session
        
        # Note: STS credentials will expire automatically
        # No need to explicitly revoke them
        
        return session
    
    def expire_sessions(self) -> int:
        """
        Expire sessions that have passed their expiration time.
        Should be run periodically (e.g., via scheduled Lambda).
        
        Returns:
            Number of sessions expired
        """
        now = datetime.utcnow()
        expired_count = 0
        
        for session in self._sessions.values():
            if session.status == SessionStatus.ACTIVE and now > session.expires_at:
                session.status = SessionStatus.EXPIRED
                expired_count += 1
        
        return expired_count
    
    def get_expiring_soon(self, minutes: int = 15) -> List[AccessSession]:
        """
        Get sessions expiring within specified minutes.
        Useful for alerting users.
        """
        threshold = datetime.utcnow() + timedelta(minutes=minutes)
        
        return [
            session for session in self._sessions.values()
            if session.status == SessionStatus.ACTIVE
            and session.expires_at <= threshold
        ]
    
    def get_session_statistics(self) -> dict:
        """Get statistics about sessions"""
        total = len(self._sessions)
        active = sum(1 for s in self._sessions.values() if s.status == SessionStatus.ACTIVE)
        expired = sum(1 for s in self._sessions.values() if s.status == SessionStatus.EXPIRED)
        revoked = sum(1 for s in self._sessions.values() if s.status == SessionStatus.REVOKED)
        failed = sum(1 for s in self._sessions.values() if s.status == SessionStatus.FAILED)
        
        # Calculate average duration
        if self._sessions:
            avg_duration = sum(s.duration_minutes for s in self._sessions.values()) / len(self._sessions)
        else:
            avg_duration = 0
        
        # Most common resource type
        resource_counts = {}
        for session in self._sessions.values():
            resource_counts[session.resource_type] = resource_counts.get(session.resource_type, 0) + 1
        
        most_common = max(resource_counts.items(), key=lambda x: x[1])[0] if resource_counts else "none"
        
        return {
            "total": total,
            "active": active,
            "expired": expired,
            "revoked": revoked,
            "failed": failed,
            "average_duration_minutes": round(avg_duration, 1),
            "most_common_resource_type": most_common
        }
    
    def validate_session_active(self, session_id: str) -> tuple[bool, str]:
        """
        Validate that a session is still active and usable.
        
        Returns:
            Tuple of (is_active, message)
        """
        session = self.get_session(session_id)
        
        if not session:
            return False, "Session not found"
        
        if session.status != SessionStatus.ACTIVE:
            return False, f"Session status is {session.status}"
        
        if datetime.utcnow() > session.expires_at:
            return False, "Session has expired"
        
        return True, "Session is active"


# Global session service instance
session_service = SessionService()
