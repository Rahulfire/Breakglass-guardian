"""
AWS IAM Service for role and permission management
"""
import boto3
from typing import Dict, List, Optional, Tuple
from botocore.exceptions import ClientError

from backend.config import settings, PERMISSION_TEMPLATES


class IAMService:
    """
    Service for interacting with AWS IAM.
    Validates roles, permissions, and manages IAM resources.
    """
    
    def __init__(self):
        """Initialize IAM client"""
        self.iam_client = boto3.client('iam', region_name=settings.aws_region)
    
    def validate_role_exists(self, role_name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that an IAM role exists.
        
        Returns:
            Tuple of (exists, role_arn)
        """
        try:
            response = self.iam_client.get_role(RoleName=role_name)
            return True, response['Role']['Arn']
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchEntity':
                return False, None
            raise
    
    def get_role_arn(self, role_name: str) -> str:
        """Get full ARN for a role"""
        return f"arn:aws:iam::{settings.aws_account_id}:role/{role_name}"
    
    def get_restricted_role_for_template(self, template_name: str) -> str:
        """
        Get the appropriate restricted IAM role for a permission template.
        
        In production, map templates to pre-created restricted roles.
        """
        # Map templates to role names
        role_mapping = {
            "ec2_restart": "BreakGlassRestrictedEC2",
            "ec2_stop_start": "BreakGlassRestrictedEC2",
            "lambda_config_update": "BreakGlassRestrictedLambda",
            "s3_read": "BreakGlassRestrictedS3Read",
            "dynamodb_read": "BreakGlassRestrictedDynamoDBRead",
            "rds_parameter_update": "BreakGlassRestrictedRDS"
        }
        
        role_name = role_mapping.get(template_name, "BreakGlassRestrictedDefault")
        return self.get_role_arn(role_name)
    
    def validate_permission_template(self, template_name: str) -> Tuple[bool, str]:
        """
        Validate that a permission template is allowed.
        
        Returns:
            Tuple of (is_valid, message)
        """
        if template_name not in PERMISSION_TEMPLATES:
            return False, f"Unknown permission template: {template_name}"
        
        template = PERMISSION_TEMPLATES[template_name]
        
        # Validate template has required fields
        required_fields = ['name', 'actions', 'risk_level']
        for field in required_fields:
            if field not in template:
                return False, f"Template missing required field: {field}"
        
        return True, f"Template '{template['name']}' is valid"
    
    def get_template_permissions(self, template_name: str) -> List[str]:
        """Get list of permissions from a template"""
        if template_name not in PERMISSION_TEMPLATES:
            return []
        return PERMISSION_TEMPLATES[template_name]['actions']
    
    def build_resource_arn(
        self,
        resource_type: str,
        resource_id: str,
        region: Optional[str] = None
    ) -> str:
        """
        Build full ARN for a resource.
        
        Args:
            resource_type: Type of resource (ec2, s3, lambda, etc.)
            resource_id: Resource identifier
            region: AWS region (defaults to configured region)
        """
        if region is None:
            region = settings.aws_region
        
        account = settings.aws_account_id
        
        # ARN patterns by resource type
        arn_patterns = {
            "ec2": f"arn:aws:ec2:{region}:{account}:instance/{resource_id}",
            "s3": f"arn:aws:s3:::{resource_id}/*",  # S3 is region-agnostic
            "lambda": f"arn:aws:lambda:{region}:{account}:function:{resource_id}",
            "dynamodb": f"arn:aws:dynamodb:{region}:{account}:table/{resource_id}",
            "rds": f"arn:aws:rds:{region}:{account}:db:{resource_id}"
        }
        
        return arn_patterns.get(resource_type, f"arn:aws:{resource_type}:{region}:{account}:{resource_id}")
    
    def list_breakglass_roles(self) -> List[Dict]:
        """
        List all BreakGlass IAM roles.
        
        Returns list of roles with their details.
        """
        try:
            roles = []
            paginator = self.iam_client.get_paginator('list_roles')
            
            for page in paginator.paginate(PathPrefix='/BreakGlass/'):
                for role in page['Roles']:
                    roles.append({
                        'name': role['RoleName'],
                        'arn': role['Arn'],
                        'created': role['CreateDate'],
                        'description': role.get('Description', '')
                    })
            
            return roles
        except ClientError as e:
            print(f"Error listing roles: {e}")
            return []
    
    def validate_trust_policy(self, role_name: str) -> Tuple[bool, str]:
        """
        Validate that a role's trust policy is appropriate for BreakGlass.
        
        Trust policy should only allow specific principals.
        """
        try:
            response = self.iam_client.get_role(RoleName=role_name)
            trust_policy = response['Role']['AssumeRolePolicyDocument']
            
            # In production: Validate trust policy only allows authorized principals
            # For now: Basic validation
            if 'Statement' not in trust_policy:
                return False, "Trust policy missing Statement"
            
            return True, "Trust policy valid"
            
        except ClientError as e:
            return False, f"Error validating trust policy: {e}"


# Global IAM service instance
iam_service = IAMService()
