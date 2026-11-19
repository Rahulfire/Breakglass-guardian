"""
Configuration management for BreakGlass Guardian
"""
import os
from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        env_file_encoding='utf-8',
        extra='ignore'  # Ignore extra fields in .env
    )
    
    # AWS Configuration
    aws_region: str = Field(default="us-east-1")
    aws_account_id: str = Field(default="123456789012")
    
    # Local Mode Configuration
    use_local_mode: bool = Field(default=True)
    bedrock_enabled: bool = Field(default=False)
    
    # Bedrock Configuration
    bedrock_agent_id: str = Field(default="DEMO_AGENT")
    bedrock_agent_alias_id: str = Field(default="DEMO_ALIAS")
    bedrock_model_id: str = Field(default="anthropic.claude-3-sonnet-20240229-v1:0")
    bedrock_guardrail_id: str = Field(default="DEMO_GUARDRAIL")
    bedrock_guardrail_version: str = Field(default="1")
    
    # DynamoDB Tables
    dynamodb_requests_table: str = Field(default="breakglass-requests")
    dynamodb_approvals_table: str = Field(default="breakglass-approvals")
    dynamodb_sessions_table: str = Field(default="breakglass-sessions")
    dynamodb_audit_table: str = Field(default="breakglass-audit")
    
    # Security Configuration
    max_session_duration_minutes: int = Field(default=120)
    require_approval_for_risk_level: str = Field(default="MEDIUM")
    allowed_resource_types: Union[str, List[str]] = Field(default="ec2,s3,lambda,dynamodb,rds")
    allowed_aws_accounts: Union[str, List[str]] = Field(default="123456789012")
    
    # Approval Configuration
    approval_expiration_minutes: int = Field(default=60)
    require_mfa_for_approval: bool = Field(default=True)
    authorized_approvers: Union[str, List[str]] = Field(default="admin@company.com,security@company.com")
    
    # API Configuration
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    cors_origins: Union[str, List[str]] = Field(default="http://localhost:5173,http://localhost:3000")
    debug: bool = Field(default=False)
    
    # Logging
    log_level: str = Field(default="INFO")
    audit_log_retention_days: int = Field(default=365)
    
    # Risk Thresholds
    risk_threshold_low: int = Field(default=30)
    risk_threshold_medium: int = Field(default=60)
    risk_threshold_high: int = Field(default=85)
    
    @field_validator("allowed_resource_types", "allowed_aws_accounts", "authorized_approvers", "cors_origins", mode='before')
    @classmethod
    def parse_list(cls, v):
        """Parse comma-separated strings into lists"""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        if isinstance(v, (int, float)):
            return [str(v)]
        return v if v is not None else []
    
    @field_validator("require_approval_for_risk_level", mode='after')
    @classmethod
    def validate_risk_level(cls, v):
        """Validate risk level"""
        valid_levels = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        if v not in valid_levels:
            raise ValueError(f"Risk level must be one of {valid_levels}")
        return v


# Global settings instance
settings = Settings()


# Risk level enumeration
class RiskLevel:
    """Risk level constants"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    
    @staticmethod
    def get_score(level: str) -> int:
        """Convert risk level to numeric score"""
        scores = {
            "LOW": 25,
            "MEDIUM": 50,
            "HIGH": 75,
            "CRITICAL": 100
        }
        return scores.get(level, 100)
    
    @staticmethod
    def from_score(score: int) -> str:
        """Convert numeric score to risk level"""
        if score < settings.risk_threshold_low:
            return RiskLevel.LOW
        elif score < settings.risk_threshold_medium:
            return RiskLevel.MEDIUM
        elif score < settings.risk_threshold_high:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL


# Permission templates for different resource types
PERMISSION_TEMPLATES = {
    "ec2_restart": {
        "name": "EC2 Instance Restart",
        "description": "Restart a specific EC2 instance",
        "actions": ["ec2:RebootInstances", "ec2:DescribeInstances"],
        "resource_pattern": "arn:aws:ec2:{region}:{account}:instance/{instance_id}",
        "max_duration_minutes": 60,
        "risk_level": "MEDIUM"
    },
    "ec2_stop_start": {
        "name": "EC2 Instance Stop/Start",
        "description": "Stop and start a specific EC2 instance",
        "actions": ["ec2:StopInstances", "ec2:StartInstances", "ec2:DescribeInstances"],
        "resource_pattern": "arn:aws:ec2:{region}:{account}:instance/{instance_id}",
        "max_duration_minutes": 120,
        "risk_level": "MEDIUM"
    },
    "lambda_config_update": {
        "name": "Lambda Configuration Update",
        "description": "Update Lambda function configuration (environment variables only)",
        "actions": ["lambda:UpdateFunctionConfiguration", "lambda:GetFunctionConfiguration"],
        "resource_pattern": "arn:aws:lambda:{region}:{account}:function/{function_name}",
        "max_duration_minutes": 120,
        "risk_level": "MEDIUM"
    },
    "s3_read": {
        "name": "S3 Read Access",
        "description": "Read-only access to specific S3 bucket",
        "actions": ["s3:GetObject", "s3:ListBucket"],
        "resource_pattern": "arn:aws:s3:::{bucket_name}/*",
        "max_duration_minutes": 60,
        "risk_level": "LOW"
    },
    "dynamodb_read": {
        "name": "DynamoDB Read Access",
        "description": "Read-only access to specific DynamoDB table",
        "actions": ["dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan"],
        "resource_pattern": "arn:aws:dynamodb:{region}:{account}:table/{table_name}",
        "max_duration_minutes": 60,
        "risk_level": "LOW"
    },
    "rds_parameter_update": {
        "name": "RDS Parameter Update",
        "description": "Update RDS instance parameters",
        "actions": ["rds:ModifyDBInstance", "rds:DescribeDBInstances"],
        "resource_pattern": "arn:aws:rds:{region}:{account}:db:{instance_id}",
        "max_duration_minutes": 120,
        "risk_level": "HIGH"
    }
}


# Prohibited actions that should always be denied
PROHIBITED_ACTIONS = [
    "iam:*",
    "*:*",  # Wildcard all
    "sts:AssumeRole",  # Direct role assumption
    "cloudtrail:StopLogging",
    "cloudtrail:DeleteTrail",
    "guardduty:DeleteDetector",
    "securityhub:DisableSecurityHub",
    "config:DeleteConfigRule",
    "s3:DeleteBucket",
    "dynamodb:DeleteTable",
    "rds:DeleteDBInstance",
    "ec2:TerminateInstances"
]


# High-risk keywords that trigger CRITICAL classification
HIGH_RISK_KEYWORDS = [
    "administrator",
    "admin",
    "full access",
    "unrestricted",
    "wildcard",
    "*",
    "root",
    "superuser",
    "god mode",
    "bypass",
    "disable",
    "delete trail",
    "stop logging"
]
