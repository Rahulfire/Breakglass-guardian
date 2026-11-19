"""
AWS STS Service for generating temporary credentials
"""
import boto3
from typing import Dict, Optional
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

from backend.config import settings
from backend.models.access_session import TemporaryCredentials


class STSService:
    """
    Service for generating temporary AWS credentials using STS.
    Implements least-privilege access with session policies.
    """
    
    def __init__(self):
        """Initialize STS client"""
        self.sts_client = boto3.client('sts', region_name=settings.aws_region)
    
    def generate_temporary_credentials(
        self,
        session_id: str,
        role_arn: str,
        session_name: str,
        duration_minutes: int,
        permissions: list[str],
        resource_arn: str
    ) -> TemporaryCredentials:
        """
        Generate temporary AWS credentials with session policy.
        
        Args:
            session_id: Unique session identifier
            role_arn: IAM role ARN to assume
            session_name: Name for the STS session
            duration_minutes: Duration in minutes (max 120)
            permissions: List of allowed actions
            resource_arn: Specific resource ARN to restrict access
            
        Returns:
            TemporaryCredentials with access keys and session token
        """
        # Validate duration
        if duration_minutes > settings.max_session_duration_minutes:
            duration_minutes = settings.max_session_duration_minutes
        
        duration_seconds = duration_minutes * 60
        
        # Create session policy for additional restriction
        session_policy = self._create_session_policy(permissions, resource_arn)
        
        try:
            # Assume role with session policy
            response = self.sts_client.assume_role(
                RoleArn=role_arn,
                RoleSessionName=session_name,
                DurationSeconds=duration_seconds,
                Policy=session_policy
            )
            
            credentials = response['Credentials']
            
            return TemporaryCredentials(
                session_id=session_id,
                access_key_id=credentials['AccessKeyId'],
                secret_access_key=credentials['SecretAccessKey'],
                session_token=credentials['SessionToken'],
                expiration=credentials['Expiration'],
                region=settings.aws_region,
                granted_permissions=permissions,
                resource_scope=resource_arn
            )
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            raise RuntimeError(f"Failed to generate credentials: {error_code} - {error_message}")
    
    def _create_session_policy(self, permissions: list[str], resource_arn: str) -> str:
        """
        Create IAM session policy for additional access restriction.
        
        Session policies further limit the permissions granted by the role.
        This implements defense in depth - even if the role has broad permissions,
        the session policy restricts to only what's needed.
        """
        import json
        
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": permissions,
                    "Resource": resource_arn
                }
            ]
        }
        
        return json.dumps(policy)
    
    def validate_credentials_active(self, access_key_id: str) -> bool:
        """
        Validate if temporary credentials are still active.
        
        Note: STS credentials expire automatically, this is for additional checks.
        """
        try:
            # Try to get caller identity
            temp_client = boto3.client(
                'sts',
                aws_access_key_id=access_key_id,
                region_name=settings.aws_region
            )
            temp_client.get_caller_identity()
            return True
        except ClientError:
            return False
    
    def get_session_info(self, access_key_id: str) -> Optional[Dict]:
        """Get information about the session"""
        try:
            temp_client = boto3.client(
                'sts',
                aws_access_key_id=access_key_id,
                region_name=settings.aws_region
            )
            response = temp_client.get_caller_identity()
            return {
                "account": response['Account'],
                "user_id": response['UserId'],
                "arn": response['Arn']
            }
        except ClientError:
            return None


# Global STS service instance
sts_service = STSService()
