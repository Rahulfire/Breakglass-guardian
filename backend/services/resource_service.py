"""
Resource validation and metadata service
"""
import boto3
from typing import Dict, Optional, Tuple
from botocore.exceptions import ClientError

from backend.config import settings


class ResourceService:
    """
    Service for validating AWS resources and retrieving metadata.
    Ensures requested resources exist and are in the allowlist.
    """
    
    def __init__(self):
        """Initialize AWS clients"""
        self.ec2_client = boto3.client('ec2', region_name=settings.aws_region)
        self.s3_client = boto3.client('s3')
        self.lambda_client = boto3.client('lambda', region_name=settings.aws_region)
        self.dynamodb_client = boto3.client('dynamodb', region_name=settings.aws_region)
        self.rds_client = boto3.client('rds', region_name=settings.aws_region)
    
    def validate_resource_exists(
        self,
        resource_type: str,
        resource_id: str,
        region: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Validate that a resource exists in AWS.
        
        Args:
            resource_type: Type of resource (ec2, s3, lambda, etc.)
            resource_id: Resource identifier
            region: AWS region (optional)
            
        Returns:
            Tuple of (exists, message)
        """
        if region is None:
            region = settings.aws_region
        
        try:
            if resource_type == "ec2":
                return self._validate_ec2_instance(resource_id, region)
            elif resource_type == "s3":
                return self._validate_s3_bucket(resource_id)
            elif resource_type == "lambda":
                return self._validate_lambda_function(resource_id, region)
            elif resource_type == "dynamodb":
                return self._validate_dynamodb_table(resource_id, region)
            elif resource_type == "rds":
                return self._validate_rds_instance(resource_id, region)
            else:
                return False, f"Unsupported resource type: {resource_type}"
                
        except Exception as e:
            return False, f"Error validating resource: {str(e)}"
    
    def _validate_ec2_instance(self, instance_id: str, region: str) -> Tuple[bool, str]:
        """Validate EC2 instance exists"""
        try:
            response = self.ec2_client.describe_instances(InstanceIds=[instance_id])
            
            if not response['Reservations']:
                return False, f"EC2 instance {instance_id} not found"
            
            instance = response['Reservations'][0]['Instances'][0]
            state = instance['State']['Name']
            
            return True, f"EC2 instance exists (state: {state})"
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'InvalidInstanceID.NotFound':
                return False, f"EC2 instance {instance_id} not found"
            raise
    
    def _validate_s3_bucket(self, bucket_name: str) -> Tuple[bool, str]:
        """Validate S3 bucket exists"""
        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
            return True, f"S3 bucket {bucket_name} exists"
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                return False, f"S3 bucket {bucket_name} not found"
            elif error_code == '403':
                return False, f"Access denied to S3 bucket {bucket_name}"
            raise
    
    def _validate_lambda_function(self, function_name: str, region: str) -> Tuple[bool, str]:
        """Validate Lambda function exists"""
        try:
            response = self.lambda_client.get_function(FunctionName=function_name)
            return True, f"Lambda function {function_name} exists"
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return False, f"Lambda function {function_name} not found"
            raise
    
    def _validate_dynamodb_table(self, table_name: str, region: str) -> Tuple[bool, str]:
        """Validate DynamoDB table exists"""
        try:
            response = self.dynamodb_client.describe_table(TableName=table_name)
            status = response['Table']['TableStatus']
            return True, f"DynamoDB table {table_name} exists (status: {status})"
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return False, f"DynamoDB table {table_name} not found"
            raise
    
    def _validate_rds_instance(self, instance_id: str, region: str) -> Tuple[bool, str]:
        """Validate RDS instance exists"""
        try:
            response = self.rds_client.describe_db_instances(DBInstanceIdentifier=instance_id)
            
            if not response['DBInstances']:
                return False, f"RDS instance {instance_id} not found"
            
            instance = response['DBInstances'][0]
            status = instance['DBInstanceStatus']
            
            return True, f"RDS instance {instance_id} exists (status: {status})"
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'DBInstanceNotFound':
                return False, f"RDS instance {instance_id} not found"
            raise
    
    def get_resource_metadata(
        self,
        resource_type: str,
        resource_id: str
    ) -> Optional[Dict]:
        """
        Get metadata about a resource.
        
        Returns:
            Dictionary with resource metadata or None if not found
        """
        try:
            if resource_type == "ec2":
                return self._get_ec2_metadata(resource_id)
            elif resource_type == "s3":
                return self._get_s3_metadata(resource_id)
            elif resource_type == "lambda":
                return self._get_lambda_metadata(resource_id)
            elif resource_type == "dynamodb":
                return self._get_dynamodb_metadata(resource_id)
            elif resource_type == "rds":
                return self._get_rds_metadata(resource_id)
            else:
                return None
                
        except Exception as e:
            print(f"Error getting metadata: {e}")
            return None
    
    def _get_ec2_metadata(self, instance_id: str) -> Optional[Dict]:
        """Get EC2 instance metadata"""
        try:
            response = self.ec2_client.describe_instances(InstanceIds=[instance_id])
            
            if not response['Reservations']:
                return None
            
            instance = response['Reservations'][0]['Instances'][0]
            
            return {
                "instance_id": instance_id,
                "state": instance['State']['Name'],
                "instance_type": instance['InstanceType'],
                "launch_time": instance.get('LaunchTime'),
                "availability_zone": instance['Placement']['AvailabilityZone'],
                "tags": {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
            }
            
        except ClientError:
            return None
    
    def _get_s3_metadata(self, bucket_name: str) -> Optional[Dict]:
        """Get S3 bucket metadata"""
        try:
            location = self.s3_client.get_bucket_location(Bucket=bucket_name)
            versioning = self.s3_client.get_bucket_versioning(Bucket=bucket_name)
            
            return {
                "bucket_name": bucket_name,
                "region": location.get('LocationConstraint', 'us-east-1'),
                "versioning": versioning.get('Status', 'Disabled')
            }
            
        except ClientError:
            return None
    
    def _get_lambda_metadata(self, function_name: str) -> Optional[Dict]:
        """Get Lambda function metadata"""
        try:
            response = self.lambda_client.get_function(FunctionName=function_name)
            config = response['Configuration']
            
            return {
                "function_name": function_name,
                "runtime": config['Runtime'],
                "memory": config['MemorySize'],
                "timeout": config['Timeout'],
                "last_modified": config['LastModified']
            }
            
        except ClientError:
            return None
    
    def _get_dynamodb_metadata(self, table_name: str) -> Optional[Dict]:
        """Get DynamoDB table metadata"""
        try:
            response = self.dynamodb_client.describe_table(TableName=table_name)
            table = response['Table']
            
            return {
                "table_name": table_name,
                "status": table['TableStatus'],
                "item_count": table.get('ItemCount', 0),
                "size_bytes": table.get('TableSizeBytes', 0)
            }
            
        except ClientError:
            return None
    
    def _get_rds_metadata(self, instance_id: str) -> Optional[Dict]:
        """Get RDS instance metadata"""
        try:
            response = self.rds_client.describe_db_instances(DBInstanceIdentifier=instance_id)
            
            if not response['DBInstances']:
                return None
            
            instance = response['DBInstances'][0]
            
            return {
                "instance_id": instance_id,
                "engine": instance['Engine'],
                "status": instance['DBInstanceStatus'],
                "instance_class": instance['DBInstanceClass'],
                "storage_gb": instance['AllocatedStorage']
            }
            
        except ClientError:
            return None
    
    def check_resource_in_allowlist(
        self,
        resource_type: str,
        resource_id: str
    ) -> Tuple[bool, str]:
        """
        Check if resource is in the allowlist.
        
        In production: Query allowlist from database or configuration.
        For demo: Accept all resources (validation happens at policy level).
        
        Returns:
            Tuple of (is_allowed, message)
        """
        # In production: Check against actual allowlist
        # For now: Basic validation
        
        if not resource_id or len(resource_id) == 0:
            return False, "Resource ID cannot be empty"
        
        if "*" in resource_id:
            return False, "Wildcard resource IDs not allowed"
        
        # In production: Query allowlist table
        # allowed_resources = get_from_database(resource_type)
        # return resource_id in allowed_resources
        
        return True, f"Resource {resource_id} is in allowlist"


# Global resource service instance
resource_service = ResourceService()
