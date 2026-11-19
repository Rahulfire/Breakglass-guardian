"""
Policy validation for resource access and permissions
"""
from typing import List, Tuple, Optional
from backend.config import settings, PERMISSION_TEMPLATES, PROHIBITED_ACTIONS
from backend.models.access_request import AccessRequest


class PolicyValidator:
    """
    Validates requests against security policies.
    Independent of AI agent decisions.
    """
    
    @staticmethod
    def validate_resource_access(request: AccessRequest) -> Tuple[bool, str]:
        """
        Validate if resource is in allowlist.
        
        Returns:
            Tuple of (is_valid, message)
        """
        resource_type = request.resource_type.lower()
        
        # Check if resource type is allowed
        if resource_type not in [rt.lower() for rt in settings.allowed_resource_types]:
            return False, f"Resource type '{resource_type}' is not in allowed types"
        
        # In production, check against actual resource allowlist from config or database
        # For now, we validate that resource_id is not suspicious
        if not request.resource_id or len(request.resource_id) == 0:
            return False, "Resource ID cannot be empty"
        
        if "*" in request.resource_id:
            return False, "Wildcard resource IDs are not allowed"
        
        # Validate resource ID format based on type
        validation_result = PolicyValidator._validate_resource_id_format(
            resource_type, request.resource_id
        )
        
        if not validation_result[0]:
            return validation_result
        
        return True, f"Resource access validated for {resource_type}:{request.resource_id}"
    
    @staticmethod
    def _validate_resource_id_format(resource_type: str, resource_id: str) -> Tuple[bool, str]:
        """Validate resource ID format"""
        
        format_rules = {
            "ec2": lambda id: id.startswith("i-") and len(id) > 3,
            "s3": lambda id: len(id) > 3 and "/" not in id,  # Bucket name
            "lambda": lambda id: len(id) > 0 and len(id) < 140,
            "dynamodb": lambda id: len(id) > 0 and len(id) < 255,
            "rds": lambda id: len(id) > 0 and len(id) < 63
        }
        
        if resource_type in format_rules:
            if not format_rules[resource_type](resource_id):
                return False, f"Invalid format for {resource_type} resource ID"
        
        return True, "Resource ID format valid"
    
    @staticmethod
    def validate_permissions(
        requested_permissions: Optional[List[str]],
        recommended_template: Optional[str] = None
    ) -> Tuple[bool, str, List[str]]:
        """
        Validate requested permissions against templates.
        
        Returns:
            Tuple of (is_valid, message, approved_permissions)
        """
        if not requested_permissions:
            if recommended_template and recommended_template in PERMISSION_TEMPLATES:
                template = PERMISSION_TEMPLATES[recommended_template]
                return True, f"Using template: {template['name']}", template["actions"]
            return False, "No permissions specified and no template recommended", []
        
        # Check for prohibited actions
        for perm in requested_permissions:
            if perm in PROHIBITED_ACTIONS:
                return False, f"Prohibited action requested: {perm}", []
            
            # Check for dangerous wildcards
            if perm == "*:*" or perm == "*":
                return False, "Unrestricted wildcard permissions not allowed", []
        
        # If template recommended, validate against it
        if recommended_template and recommended_template in PERMISSION_TEMPLATES:
            template = PERMISSION_TEMPLATES[recommended_template]
            template_actions = set(template["actions"])
            requested_set = set(requested_permissions)
            
            # Requested permissions should be subset of template
            if not requested_set.issubset(template_actions):
                extra_perms = requested_set - template_actions
                return False, f"Requested permissions exceed template: {extra_perms}", []
            
            return True, f"Permissions validated against template: {template['name']}", list(requested_set)
        
        # Without a template, perform basic validation
        # Limit to reasonable number of permissions
        if len(requested_permissions) > 20:
            return False, f"Too many permissions requested: {len(requested_permissions)}", []
        
        return True, "Permissions require approval", requested_permissions
    
    @staticmethod
    def validate_session_duration(duration_minutes: int, template: Optional[str] = None) -> Tuple[bool, str]:
        """
        Validate requested session duration.
        
        Returns:
            Tuple of (is_valid, message)
        """
        if duration_minutes < 5:
            return False, "Duration must be at least 5 minutes"
        
        if duration_minutes > settings.max_session_duration_minutes:
            return False, f"Duration exceeds maximum of {settings.max_session_duration_minutes} minutes"
        
        # Check against template if provided
        if template and template in PERMISSION_TEMPLATES:
            template_max = PERMISSION_TEMPLATES[template].get("max_duration_minutes", 120)
            if duration_minutes > template_max:
                return False, f"Duration exceeds template maximum of {template_max} minutes"
        
        return True, f"Duration of {duration_minutes} minutes is valid"
    
    @staticmethod
    def validate_aws_account(account_id: str) -> Tuple[bool, str]:
        """
        Validate AWS account is in allowlist.
        
        Returns:
            Tuple of (is_valid, message)
        """
        # Validate format
        if not account_id.isdigit() or len(account_id) != 12:
            return False, "Invalid AWS account ID format"
        
        # Check against allowlist
        if str(account_id) not in [str(a) for a in settings.allowed_aws_accounts]:
            return False, f"AWS account {account_id} is not in allowed accounts"
        
        return True, f"AWS account {account_id} is authorized"
    
    @staticmethod
    def get_permission_template(template_name: str) -> Optional[dict]:
        """Get permission template by name"""
        return PERMISSION_TEMPLATES.get(template_name)
    
    @staticmethod
    def recommend_template(request: AccessRequest) -> Optional[str]:
        """
        Recommend appropriate permission template based on request.
        This is a simple rule-based recommendation.
        """
        resource_type = request.resource_type.lower()
        action = request.requested_action.lower()
        
        # EC2 templates
        if resource_type == "ec2":
            if "restart" in action or "reboot" in action:
                return "ec2_restart"
            elif "stop" in action or "start" in action:
                return "ec2_stop_start"
        
        # Lambda templates
        if resource_type == "lambda":
            if "config" in action or "environment" in action:
                return "lambda_config_update"
        
        # S3 templates
        if resource_type == "s3":
            if "read" in action or "get" in action or "list" in action:
                return "s3_read"
        
        # DynamoDB templates
        if resource_type == "dynamodb":
            if "read" in action or "query" in action or "scan" in action:
                return "dynamodb_read"
        
        # RDS templates
        if resource_type == "rds":
            if "parameter" in action or "config" in action:
                return "rds_parameter_update"
        
        return None
    
    @staticmethod
    def validate_complete_request(request: AccessRequest) -> Tuple[bool, List[str], List[str]]:
        """
        Perform complete policy validation on request.
        
        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        errors = []
        warnings = []
        
        # Validate resource access
        resource_valid, resource_msg = PolicyValidator.validate_resource_access(request)
        if not resource_valid:
            errors.append(resource_msg)
        
        # Recommend template
        recommended_template = PolicyValidator.recommend_template(request)
        
        # Validate permissions
        perms_valid, perms_msg, _ = PolicyValidator.validate_permissions(
            request.requested_permissions,
            recommended_template
        )
        if not perms_valid:
            errors.append(perms_msg)
        elif "require approval" in perms_msg.lower():
            warnings.append(perms_msg)
        
        # Validate duration
        duration_valid, duration_msg = PolicyValidator.validate_session_duration(
            request.duration_minutes,
            recommended_template
        )
        if not duration_valid:
            errors.append(duration_msg)
        
        # Validate AWS account
        account_valid, account_msg = PolicyValidator.validate_aws_account(
            settings.aws_account_id
        )
        if not account_valid:
            errors.append(account_msg)
        
        return len(errors) == 0, errors, warnings
