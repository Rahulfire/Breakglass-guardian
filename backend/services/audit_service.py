"""
Audit logging service for complete forensic trail
"""
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from backend.models.audit_event import (
    AuditEvent, EventType, EventSeverity, SecurityAlert, AuditQuery
)
from backend.config import settings
from backend.storage import DynamoRepository


class AuditService:
    """
    Comprehensive audit logging service.
    In production, integrate with DynamoDB and CloudWatch.
    """
    
    def __init__(self):
        # In production: Initialize DynamoDB client
        self._events: List[AuditEvent] = []  # In-memory for demo
        self._alerts: List[SecurityAlert] = []
        self._repository = DynamoRepository(
            settings.dynamodb_audit_table,
            "event_id",
            sort_key="timestamp",
        )
    
    def log_event(
        self,
        event_type: EventType,
        severity: EventSeverity,
        event_description: str,
        actor_email: Optional[str] = None,
        actor_name: Optional[str] = None,
        request_id: Optional[str] = None,
        approval_id: Optional[str] = None,
        session_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None,
        risk_level: Optional[str] = None,
        security_flags: Optional[List[str]] = None,
        agent_involved: bool = False,
        agent_decision: Optional[str] = None,
        agent_reasoning: Optional[str] = None,
        outcome: str = "SUCCESS",
        outcome_reason: Optional[str] = None
    ) -> AuditEvent:
        """
        Log an audit event.
        
        Returns:
            Created AuditEvent
        """
        event = AuditEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            event_type=event_type,
            severity=severity,
            timestamp=datetime.utcnow(),
            actor_email=actor_email,
            actor_name=actor_name,
            request_id=request_id,
            approval_id=approval_id,
            session_id=session_id,
            resource_type=resource_type,
            resource_id=resource_id,
            event_description=event_description,
            event_data=event_data or {},
            risk_level=risk_level,
            security_flags=security_flags or [],
            agent_involved=agent_involved,
            agent_decision=agent_decision,
            agent_reasoning=agent_reasoning,
            outcome=outcome,
            outcome_reason=outcome_reason
        )
        
        # In production: Write to DynamoDB
        self._events.append(event)
        self._repository.put(event, event.event_id)
        
        # In production: Write to CloudWatch Logs
        print(f"[AUDIT] {event.severity.upper()}: {event.event_description}")
        
        # Trigger security alerts if needed
        if severity == EventSeverity.CRITICAL or len(security_flags or []) > 0:
            self._check_security_alert(event)
        
        return event
    
    def log_request_submitted(
        self,
        request_id: str,
        requester_email: str,
        requester_name: str,
        resource_type: str,
        resource_id: str
    ) -> AuditEvent:
        """Log emergency access request submission"""
        return self.log_event(
            event_type=EventType.REQUEST_SUBMITTED,
            severity=EventSeverity.INFO,
            event_description=f"Emergency access request submitted for {resource_type}:{resource_id}",
            actor_email=requester_email,
            actor_name=requester_name,
            request_id=request_id,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome="SUCCESS"
        )
    
    def log_agent_analysis(
        self,
        request_id: str,
        risk_level: str,
        agent_decision: str,
        agent_reasoning: str,
        security_flags: List[str]
    ) -> AuditEvent:
        """Log AI agent analysis"""
        severity = EventSeverity.WARNING if risk_level in ["HIGH", "CRITICAL"] else EventSeverity.INFO
        
        return self.log_event(
            event_type=EventType.REQUEST_ANALYZED,
            severity=severity,
            event_description=f"AI agent analyzed request, classified as {risk_level}",
            request_id=request_id,
            risk_level=risk_level,
            security_flags=security_flags,
            agent_involved=True,
            agent_decision=agent_decision,
            agent_reasoning=agent_reasoning,
            outcome="SUCCESS"
        )
    
    def log_prompt_injection_attempt(
        self,
        request_id: str,
        actor_email: str,
        indicators: List[str]
    ) -> AuditEvent:
        """Log prompt injection attempt"""
        return self.log_event(
            event_type=EventType.PROMPT_INJECTION_DETECTED,
            severity=EventSeverity.CRITICAL,
            event_description="Prompt injection attempt detected and blocked",
            actor_email=actor_email,
            request_id=request_id,
            security_flags=indicators,
            outcome="BLOCKED",
            outcome_reason="Request contains malicious prompt patterns"
        )
    
    def log_privilege_escalation_attempt(
        self,
        request_id: str,
        actor_email: str,
        requested_permissions: List[str]
    ) -> AuditEvent:
        """Log privilege escalation attempt"""
        return self.log_event(
            event_type=EventType.PRIVILEGE_ESCALATION_ATTEMPT,
            severity=EventSeverity.CRITICAL,
            event_description="Privilege escalation attempt detected",
            actor_email=actor_email,
            request_id=request_id,
            event_data={"requested_permissions": requested_permissions},
            security_flags=["privilege_escalation"],
            outcome="BLOCKED",
            outcome_reason="Excessive or prohibited permissions requested"
        )
    
    def log_approval_created(
        self,
        approval_id: str,
        request_id: str,
        risk_level: str
    ) -> AuditEvent:
        """Log approval request creation"""
        return self.log_event(
            event_type=EventType.APPROVAL_CREATED,
            severity=EventSeverity.INFO,
            event_description="Approval request created for human review",
            request_id=request_id,
            approval_id=approval_id,
            risk_level=risk_level,
            outcome="SUCCESS"
        )
    
    def log_approval_decision(
        self,
        approval_id: str,
        request_id: str,
        approver_email: str,
        approver_name: str,
        decision: str,
        reason: str
    ) -> AuditEvent:
        """Log approval decision"""
        severity = EventSeverity.INFO if decision == "APPROVED" else EventSeverity.WARNING
        
        return self.log_event(
            event_type=EventType.APPROVAL_DECISION,
            severity=severity,
            event_description=f"Approval {decision} by {approver_name}",
            actor_email=approver_email,
            actor_name=approver_name,
            request_id=request_id,
            approval_id=approval_id,
            event_data={"decision": decision, "reason": reason},
            outcome="SUCCESS"
        )
    
    def log_session_created(
        self,
        session_id: str,
        request_id: str,
        approval_id: str,
        requester_email: str,
        resource_type: str,
        resource_id: str,
        granted_permissions: List[str],
        duration_minutes: int
    ) -> AuditEvent:
        """Log temporary access session creation"""
        return self.log_event(
            event_type=EventType.SESSION_CREATED,
            severity=EventSeverity.INFO,
            event_description=f"Temporary access session created for {duration_minutes} minutes",
            actor_email=requester_email,
            request_id=request_id,
            approval_id=approval_id,
            session_id=session_id,
            resource_type=resource_type,
            resource_id=resource_id,
            event_data={
                "granted_permissions": granted_permissions,
                "duration_minutes": duration_minutes
            },
            outcome="SUCCESS"
        )
    
    def log_unauthorized_access_attempt(
        self,
        actor_email: str,
        resource_type: str,
        resource_id: str,
        reason: str
    ) -> AuditEvent:
        """Log unauthorized access attempt"""
        return self.log_event(
            event_type=EventType.UNAUTHORIZED_ACCESS_ATTEMPT,
            severity=EventSeverity.CRITICAL,
            event_description="Unauthorized access attempt blocked",
            actor_email=actor_email,
            resource_type=resource_type,
            resource_id=resource_id,
            security_flags=["unauthorized_access"],
            outcome="BLOCKED",
            outcome_reason=reason
        )
    
    def log_approval_bypass_attempt(
        self,
        request_id: str,
        actor_email: str,
        reason: str
    ) -> AuditEvent:
        """Log attempt to bypass approval"""
        return self.log_event(
            event_type=EventType.APPROVAL_BYPASS_ATTEMPT,
            severity=EventSeverity.CRITICAL,
            event_description="Approval bypass attempt detected and blocked",
            actor_email=actor_email,
            request_id=request_id,
            security_flags=["approval_bypass"],
            outcome="BLOCKED",
            outcome_reason=reason
        )
    
    def query_events(self, query: AuditQuery) -> List[AuditEvent]:
        """
        Query audit events with filters.
        In production: Query DynamoDB with GSI.
        """
        filtered_events = self._events
        
        if query.event_types:
            filtered_events = [e for e in filtered_events if e.event_type in query.event_types]
        
        if query.severity:
            filtered_events = [e for e in filtered_events if e.severity == query.severity]
        
        if query.actor_email:
            filtered_events = [e for e in filtered_events if e.actor_email == query.actor_email]
        
        if query.request_id:
            filtered_events = [e for e in filtered_events if e.request_id == query.request_id]
        
        if query.resource_type:
            filtered_events = [e for e in filtered_events if e.resource_type == query.resource_type]
        
        if query.outcome:
            filtered_events = [e for e in filtered_events if e.outcome == query.outcome]
        
        # Sort by timestamp descending
        filtered_events.sort(key=lambda e: e.timestamp, reverse=True)
        
        # Apply pagination
        start = query.offset
        end = start + query.limit
        
        return filtered_events[start:end]
    
    def get_security_alerts(self, resolved: Optional[bool] = None) -> List[SecurityAlert]:
        """Get security alerts"""
        if resolved is None:
            return self._alerts
        return [a for a in self._alerts if a.resolved == resolved]
    
    def _check_security_alert(self, event: AuditEvent):
        """Check if event should trigger security alert"""
        if event.severity != EventSeverity.CRITICAL:
            return
        
        # Create security alert for critical events
        alert = SecurityAlert(
            alert_id=f"alert_{uuid.uuid4().hex[:8]}",
            alert_type=event.event_type.value,
            severity=event.severity,
            title=f"Security Alert: {event.event_type.value.replace('_', ' ').title()}",
            description=event.event_description,
            related_event_ids=[event.event_id],
            suspected_actor_email=event.actor_email,
            attack_indicators=event.security_flags,
            auto_blocked=event.outcome == "BLOCKED",
            manual_review_required=True,
            notified_security_team=True  # In production: Actually send notification
        )
        
        self._alerts.append(alert)
        
        # In production: Send to security team via SNS/SES
        print(f"[SECURITY ALERT] {alert.title}: {alert.description}")


# Global audit service instance
audit_service = AuditService()
