"""
API endpoints for emergency access requests
"""
from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
import uuid
from datetime import datetime

from backend.models.access_request import (
    AccessRequest, AgentAnalysis, BackendValidation,
    AccessRequestFull, RequestStatus, RequestListResponse
)
from backend.security.risk_engine import RiskEngine
from backend.security.policy_validator import PolicyValidator
from backend.security.identity_validator import IdentityValidator
from backend.services.audit_service import audit_service
from backend.models.audit_event import EventType, EventSeverity

router = APIRouter()

# In-memory storage for demo (in production: use DynamoDB)
_requests_store: dict[str, AccessRequestFull] = {}


@router.post("/", response_model=AccessRequestFull, status_code=status.HTTP_201_CREATED)
async def submit_request(request: AccessRequest):
    """
    Submit a new emergency access request.
    
    The request will be:
    1. Validated for suspicious content
    2. Analyzed by AI agent
    3. Validated by backend policies
    4. Classified by risk level
    5. Routed for approval if needed
    """
    # Generate request ID
    request.request_id = f"req_{uuid.uuid4().hex[:12]}"
    request.created_at = datetime.utcnow()
    request.updated_at = datetime.utcnow()
    request.status = RequestStatus.ANALYZING
    
    # Validate requester identity
    identity_valid, identity_msg = IdentityValidator.validate_requester(
        request.requester_email,
        request.requester_name
    )
    
    if not identity_valid:
        audit_service.log_unauthorized_access_attempt(
            actor_email=request.requester_email,
            resource_type=request.resource_type,
            resource_id=request.resource_id,
            reason=identity_msg
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=identity_msg
        )
    
    # Log request submission
    audit_service.log_request_submitted(
        request_id=request.request_id,
        requester_email=request.requester_email,
        requester_name=request.requester_name,
        resource_type=request.resource_type,
        resource_id=request.resource_id
    )
    
    # Perform risk assessment
    risk_score, risk_level, risk_factors = RiskEngine.calculate_risk_score(request)
    
    # Check for prompt injection
    if any("prompt injection" in factor.lower() or "suspicious pattern" in factor.lower() 
           for factor in risk_factors):
        audit_service.log_prompt_injection_attempt(
            request_id=request.request_id,
            actor_email=request.requester_email,
            indicators=risk_factors
        )
        request.status = RequestStatus.REJECTED
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request contains suspicious content and has been rejected"
        )
    
    # Check for privilege escalation
    if risk_level == "CRITICAL":
        audit_service.log_privilege_escalation_attempt(
            request_id=request.request_id,
            actor_email=request.requester_email,
            requested_permissions=request.requested_permissions or []
        )
        request.status = RequestStatus.REJECTED
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Request classified as CRITICAL risk and has been auto-rejected"
        )
    
    # Perform backend validation
    policy_valid, policy_errors, policy_warnings = PolicyValidator.validate_complete_request(request)
    
    # Recommend template
    recommended_template = PolicyValidator.recommend_template(request)
    
    # Create agent analysis (simulated - in production: call Bedrock Agent)
    agent_analysis = AgentAnalysis(
        request_id=request.request_id,
        incident_summary=request.emergency_description[:200],
        risk_classification=risk_level,
        risk_score=risk_score,
        risk_explanation="; ".join(risk_factors) if risk_factors else "Standard operational request",
        requested_permissions=request.requested_permissions or [],
        recommended_permissions=PolicyValidator.get_permission_template(recommended_template)["actions"] if recommended_template else [],
        recommended_template=recommended_template,
        affected_resources=[request.resource_id],
        potential_impact="Operational action on specified resource",
        approval_required=RiskEngine.requires_approval(risk_level),
        approval_reason=f"{risk_level} risk requests require human approval",
        suspicious_indicators=[f for f in risk_factors if "suspicious" in f.lower() or "injection" in f.lower()],
        agent_decision="RECOMMEND_APPROVAL" if policy_valid and risk_level != "CRITICAL" else "RECOMMEND_REJECTION",
        agent_explanation="Request appears legitimate and narrowly scoped" if policy_valid else "Policy violations detected"
    )
    
    # Log agent analysis
    audit_service.log_agent_analysis(
        request_id=request.request_id,
        risk_level=risk_level,
        agent_decision=agent_analysis.agent_decision,
        agent_reasoning=agent_analysis.agent_explanation,
        security_flags=agent_analysis.suspicious_indicators
    )
    
    # Create backend validation
    backend_validation = BackendValidation(
        request_id=request.request_id,
        validation_passed=policy_valid,
        resource_allowed=True,  # Simplified for demo
        resource_validation_message="Resource validated",
        permissions_valid=policy_valid,
        permissions_validation_message="Permissions require approval" if policy_valid else "; ".join(policy_errors),
        duration_valid=request.duration_minutes <= 120,
        duration_validation_message="Duration valid",
        requester_authorized=identity_valid,
        requester_validation_message=identity_msg,
        final_risk_level=risk_level,
        backend_risk_score=risk_score,
        violations=policy_errors,
        warnings=policy_warnings
    )
    
    # Determine final status
    if policy_valid and agent_analysis.approval_required:
        request.status = RequestStatus.PENDING_APPROVAL
    elif policy_valid and not agent_analysis.approval_required:
        request.status = RequestStatus.APPROVED
    else:
        request.status = RequestStatus.REJECTED
    
    # Create full request object
    request_full = AccessRequestFull(
        request=request,
        agent_analysis=agent_analysis,
        backend_validation=backend_validation
    )
    
    # Store request
    _requests_store[request.request_id] = request_full
    
    return request_full


@router.get("/{request_id}", response_model=AccessRequestFull)
async def get_request(request_id: str):
    """Get request details by ID"""
    if request_id not in _requests_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Request {request_id} not found"
        )
    
    return _requests_store[request_id]


@router.get("/", response_model=RequestListResponse)
async def list_requests(
    status_filter: Optional[str] = None,
    risk_level: Optional[str] = None,
    requester_email: Optional[str] = None,
    page: int = 1,
    page_size: int = 50
):
    """List all requests with optional filters"""
    requests = list(_requests_store.values())
    
    # Apply filters
    if status_filter:
        requests = [r for r in requests if r.request.status == status_filter]
    
    if risk_level:
        requests = [r for r in requests if r.agent_analysis and r.agent_analysis.risk_classification == risk_level]
    
    if requester_email:
        requests = [r for r in requests if r.request.requester_email == requester_email]
    
    # Sort by creation date descending
    requests.sort(key=lambda r: r.request.created_at or datetime.min, reverse=True)
    
    # Pagination
    total = len(requests)
    start = (page - 1) * page_size
    end = start + page_size
    paginated = requests[start:end]
    
    return RequestListResponse(
        requests=paginated,
        total=total,
        page=page,
        page_size=page_size,
        has_more=end < total
    )
