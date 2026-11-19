"""
Risk classification engine with deterministic rules
"""
from typing import List, Tuple
from backend.config import settings, RiskLevel, HIGH_RISK_KEYWORDS, PROHIBITED_ACTIONS
from backend.models.access_request import AccessRequest


class RiskEngine:
    """
    Deterministic risk assessment engine.
    Does not rely solely on LLM reasoning - uses rule-based logic.
    """
    
    @staticmethod
    def calculate_risk_score(request: AccessRequest) -> Tuple[int, RiskLevel, List[str]]:
        """
        Calculate risk score and classify risk level.
        
        Returns:
            Tuple of (score, risk_level, risk_factors)
        """
        score = 0
        risk_factors = []
        
        # Check for prohibited actions
        prohibited_score, prohibited_factors = RiskEngine._check_prohibited_actions(request)
        score += prohibited_score
        risk_factors.extend(prohibited_factors)
        
        # Check for high-risk keywords
        keyword_score, keyword_factors = RiskEngine._check_high_risk_keywords(request)
        score += keyword_score
        risk_factors.extend(keyword_factors)
        
        # Evaluate requested permissions
        permission_score, permission_factors = RiskEngine._evaluate_permissions(request)
        score += permission_score
        risk_factors.extend(permission_factors)
        
        # Evaluate duration
        duration_score, duration_factors = RiskEngine._evaluate_duration(request)
        score += duration_score
        risk_factors.extend(duration_factors)
        
        # Evaluate resource type
        resource_score, resource_factors = RiskEngine._evaluate_resource_type(request)
        score += resource_score
        risk_factors.extend(resource_factors)
        
        # Check for suspicious content
        suspicious_score, suspicious_factors = RiskEngine._check_suspicious_content(request)
        score += suspicious_score
        risk_factors.extend(suspicious_factors)
        
        # Cap score at 100
        score = min(score, 100)
        
        # Classify risk level
        risk_level = RiskLevel.from_score(score)
        
        return score, risk_level, risk_factors
    
    @staticmethod
    def _check_prohibited_actions(request: AccessRequest) -> Tuple[int, List[str]]:
        """Check if request contains prohibited actions"""
        score = 0
        factors = []
        
        request_text = f"{request.requested_action} {request.emergency_description} {request.business_justification}".lower()
        
        for prohibited in PROHIBITED_ACTIONS:
            if prohibited.lower().replace(":", " ") in request_text:
                score += 100  # Instant CRITICAL
                factors.append(f"Prohibited action detected: {prohibited}")
        
        # Check requested permissions if provided
        if request.requested_permissions:
            for perm in request.requested_permissions:
                if perm in PROHIBITED_ACTIONS:
                    score += 100
                    factors.append(f"Prohibited permission requested: {perm}")
                
                # Wildcard detection
                if "*" in perm:
                    if perm == "*:*" or perm.endswith(":*"):
                        score += 100
                        factors.append(f"Wildcard permission requested: {perm}")
                    else:
                        score += 30
                        factors.append(f"Broad wildcard permission: {perm}")
        
        return score, factors
    
    @staticmethod
    def _check_high_risk_keywords(request: AccessRequest) -> Tuple[int, List[str]]:
        """Check for high-risk keywords in request"""
        score = 0
        factors = []
        
        text_fields = [
            request.emergency_description,
            request.business_justification,
            request.requested_action
        ]
        
        combined_text = " ".join(text_fields).lower()
        
        for keyword in HIGH_RISK_KEYWORDS:
            if keyword.lower() in combined_text:
                score += 40
                factors.append(f"High-risk keyword detected: {keyword}")
        
        return score, factors
    
    @staticmethod
    def _evaluate_permissions(request: AccessRequest) -> Tuple[int, List[str]]:
        """Evaluate requested permissions scope"""
        score = 0
        factors = []
        
        if not request.requested_permissions:
            # No specific permissions provided - moderate risk
            score += 10
            factors.append("No specific permissions listed")
            return score, factors
        
        perm_count = len(request.requested_permissions)
        
        if perm_count > 10:
            score += 40
            factors.append(f"Large number of permissions requested: {perm_count}")
        elif perm_count > 5:
            score += 20
            factors.append(f"Multiple permissions requested: {perm_count}")
        
        # Check for write/delete operations
        dangerous_verbs = ["delete", "terminate", "remove", "destroy", "drop"]
        for perm in request.requested_permissions:
            perm_lower = perm.lower()
            for verb in dangerous_verbs:
                if verb in perm_lower:
                    score += 30
                    factors.append(f"Destructive permission: {perm}")
                    break
        
        # Check for IAM-related permissions
        for perm in request.requested_permissions:
            if perm.lower().startswith("iam:"):
                score += 50
                factors.append(f"IAM permission requested: {perm}")
        
        return score, factors
    
    @staticmethod
    def _evaluate_duration(request: AccessRequest) -> Tuple[int, List[str]]:
        """Evaluate session duration"""
        score = 0
        factors = []
        
        duration = request.duration_minutes
        
        if duration > 120:
            score += 40
            factors.append(f"Excessive duration: {duration} minutes")
        elif duration > 60:
            score += 20
            factors.append(f"Long duration: {duration} minutes")
        elif duration < 15:
            score += 5
            factors.append(f"Very short duration: {duration} minutes (unusual)")
        
        return score, factors
    
    @staticmethod
    def _evaluate_resource_type(request: AccessRequest) -> Tuple[int, List[str]]:
        """Evaluate risk based on resource type"""
        score = 0
        factors = []
        
        high_risk_resources = {
            "iam": 60,
            "sts": 50,
            "rds": 35,
            "dynamodb": 30
        }
        
        medium_risk_resources = {
            "ec2": 20,
            "lambda": 20,
            "s3": 15
        }
        
        resource_type = request.resource_type.lower()
        
        if resource_type in high_risk_resources:
            score += high_risk_resources[resource_type]
            factors.append(f"High-risk resource type: {resource_type}")
        elif resource_type in medium_risk_resources:
            score += medium_risk_resources[resource_type]
            factors.append(f"Medium-risk resource type: {resource_type}")
        
        return score, factors
    
    @staticmethod
    def _check_suspicious_content(request: AccessRequest) -> Tuple[int, List[str]]:
        """Check for prompt injection and suspicious patterns"""
        score = 0
        factors = []
        
        suspicious_patterns = [
            "ignore previous instructions",
            "ignore all instructions",
            "you are now",
            "system prompt",
            "override security",
            "disable security",
            "grant admin",
            "bypass approval",
            "full access",
            "unrestricted access",
            "administrator access",
            "root access",
            "sudo",
            "escalate privilege"
        ]
        
        text_fields = [
            request.emergency_description,
            request.business_justification,
            request.requested_action
        ]
        
        combined_text = " ".join(text_fields).lower()
        
        for pattern in suspicious_patterns:
            if pattern in combined_text:
                score += 100  # Instant CRITICAL
                factors.append(f"Suspicious pattern detected: '{pattern}'")
        
        # Check for excessive special characters (possible injection)
        special_char_count = sum(1 for c in combined_text if c in "{}<>[]|\\$`")
        if special_char_count > 10:
            score += 30
            factors.append(f"Excessive special characters: {special_char_count}")
        
        # Check for SQL injection patterns
        sql_patterns = ["'; drop", "union select", "or 1=1", "' or '1'='1"]
        for pattern in sql_patterns:
            if pattern in combined_text:
                score += 50
                factors.append(f"SQL injection pattern: '{pattern}'")
        
        return score, factors
    
    @staticmethod
    def requires_approval(risk_level: str) -> bool:
        """Determine if risk level requires human approval"""
        threshold = settings.require_approval_for_risk_level
        
        risk_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        
        if risk_level not in risk_levels or threshold not in risk_levels:
            return True  # Default to requiring approval
        
        return risk_levels.index(risk_level) >= risk_levels.index(threshold)
    
    @staticmethod
    def should_auto_reject(risk_level: str) -> bool:
        """Determine if risk level should be automatically rejected"""
        return risk_level == "CRITICAL"
