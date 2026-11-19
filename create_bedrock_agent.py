#!/usr/bin/env python3
"""
Create AWS Bedrock Agent for BreakGlass Guardian
"""

import boto3
import json
import time
from botocore.exceptions import ClientError

def create_bedrock_agent():
    """Create Bedrock Agent with action group"""
    
    region = 'us-east-1'
    bedrock_agent = boto3.client('bedrock-agent', region_name=region)
    bedrock_runtime = boto3.client('bedrock-runtime', region_name=region)
    sts = boto3.client('sts')
    
    # Get account ID
    account_id = sts.get_caller_identity()['Account']
    
    print("\n" + "="*60)
    print("Creating Bedrock Agent for BreakGlass Guardian")
    print("="*60 + "\n")
    
    print(f"[INFO] AWS Account: {account_id}")
    print(f"[INFO] Region: {region}\n")
    
    # Check if CloudFormation stack exists
    cf = boto3.client('cloudformation', region_name=region)
    stack_name = 'breakglass-bedrock'
    
    try:
        stack_info = cf.describe_stacks(StackName=stack_name)
        stacks = stack_info['Stacks']
        if stacks:
            outputs = {o['OutputKey']: o['OutputValue'] for o in stacks[0].get('Outputs', [])}
            agent_role_arn = outputs.get('AgentRoleArn')
            lambda_arn = outputs.get('AgentActionFunctionArn')
            print(f"[OK] Found stack: {stack_name}")
            print(f"[INFO] Agent Role: {agent_role_arn}")
            print(f"[INFO] Lambda Function: {lambda_arn}\n")
    except ClientError as e:
        if 'does not exist' in str(e):
            print(f"[ERROR] CloudFormation stack '{stack_name}' not found!")
            print(f"[INFO] Please deploy the Bedrock infrastructure first:")
            print(f"       aws cloudformation deploy --template-file infrastructure/bedrock/agent.yaml --stack-name {stack_name} --capabilities CAPABILITY_NAMED_IAM --region {region}\n")
            return None
        raise
    
    # Agent instruction
    agent_instruction = """You are a security analyst for the BreakGlass Guardian system. Your role is to:

1. Analyze emergency access requests for security risks
2. Validate that requested permissions are appropriate and minimal
3. Assess the business justification provided
4. Detect suspicious patterns or potential security threats
5. Recommend approval or rejection with clear reasoning

When analyzing requests, consider:
- Is the justification clear and legitimate?
- Are the requested permissions minimal and scoped?
- Is the duration reasonable?
- Are there any suspicious keywords or patterns?
- Does the request align with the stated emergency?

Always prioritize security while enabling legitimate emergency access."""

    # Check if agent already exists
    agent_name = 'BreakGlassGuardian'
    existing_agent = None
    
    try:
        agents = bedrock_agent.list_agents()
        for agent in agents.get('agentSummaries', []):
            if agent['agentName'] == agent_name:
                existing_agent = agent
                print(f"[INFO] Found existing agent: {agent['agentId']}")
                break
    except Exception as e:
        print(f"[WARN] Could not list agents: {e}")
    
    if existing_agent:
        agent_id = existing_agent['agentId']
        print(f"[INFO] Using existing agent: {agent_id}\n")
    else:
        # Create agent
        print(f"[INFO] Creating Bedrock Agent...")
        try:
            create_response = bedrock_agent.create_agent(
                agentName=agent_name,
                agentResourceRoleArn=agent_role_arn,
                description='AI security analyst for BreakGlass emergency access requests',
                foundationModel='anthropic.claude-sonnet-4-5-20250929-v1:0',
                instruction=agent_instruction,
                idleSessionTTLInSeconds=600
            )
            
            agent_id = create_response['agent']['agentId']
            print(f"[OK] Agent created: {agent_id}\n")
            
            # Wait for agent to be ready
            print("[INFO] Waiting for agent to be ready...")
            time.sleep(3)
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ValidationException' and 'model access' in str(e):
                print(f"[ERROR] Model access not enabled!")
                print(f"[INFO] Please enable model access first:")
                print(f"       Run: .\\enable-bedrock.ps1\n")
                return None
            raise
    
    # Create or update action group
    print(f"[INFO] Setting up action group...")
    
    action_group_name = 'SecurityAnalysis'
    
    # API Schema for action group
    api_schema = {
        "openapi": "3.0.0",
        "info": {
            "title": "BreakGlass Security Analysis API",
            "version": "1.0.0",
            "description": "API for analyzing emergency access requests"
        },
        "paths": {
            "/analyze-request": {
                "post": {
                    "summary": "Analyze security request",
                    "description": "Analyze an access request for security risks",
                    "operationId": "analyzeRequest",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "justification": {"type": "string"},
                                        "permissions": {"type": "string"},
                                        "resource_type": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Analysis result",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "analysis": {"type": "object"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/validate-permissions": {
                "post": {
                    "summary": "Validate permissions",
                    "description": "Validate requested IAM permissions",
                    "operationId": "validatePermissions",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "permissions": {"type": "string"},
                                        "resource_type": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Validation result"
                        }
                    }
                }
            },
            "/assess-risk": {
                "post": {
                    "summary": "Assess risk level",
                    "description": "Assess overall risk of access request",
                    "operationId": "assessRisk",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "duration_minutes": {"type": "integer"},
                                        "resource_type": {"type": "string"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Risk assessment"
                        }
                    }
                }
            }
        }
    }
    
    try:
        # List existing action groups
        action_groups = bedrock_agent.list_agent_action_groups(
            agentId=agent_id,
            agentVersion='DRAFT'
        )
        
        existing_action_group = None
        for ag in action_groups.get('actionGroupSummaries', []):
            if ag['actionGroupName'] == action_group_name:
                existing_action_group = ag
                break
        
        if existing_action_group:
            # Update existing action group
            bedrock_agent.update_agent_action_group(
                agentId=agent_id,
                agentVersion='DRAFT',
                actionGroupId=existing_action_group['actionGroupId'],
                actionGroupName=action_group_name,
                actionGroupExecutor={
                    'lambda': lambda_arn
                },
                apiSchema={
                    'payload': json.dumps(api_schema)
                }
            )
            print(f"[OK] Action group updated\n")
        else:
            # Create new action group
            bedrock_agent.create_agent_action_group(
                agentId=agent_id,
                agentVersion='DRAFT',
                actionGroupName=action_group_name,
                actionGroupExecutor={
                    'lambda': lambda_arn
                },
                apiSchema={
                    'payload': json.dumps(api_schema)
                },
                description='Security analysis actions for access requests'
            )
            print(f"[OK] Action group created\n")
        
    except Exception as e:
        print(f"[WARN] Action group setup: {e}")
    
    # Prepare agent
    print(f"[INFO] Preparing agent...")
    try:
        bedrock_agent.prepare_agent(agentId=agent_id)
        print(f"[OK] Agent prepared\n")
        
        # Wait for preparation
        time.sleep(5)
        
    except Exception as e:
        print(f"[WARN] Agent preparation: {e}")
    
    # Create alias
    print(f"[INFO] Creating agent alias...")
    alias_name = 'prod'
    
    try:
        aliases = bedrock_agent.list_agent_aliases(agentId=agent_id)
        existing_alias = None
        
        for alias in aliases.get('agentAliasSummaries', []):
            if alias['agentAliasName'] == alias_name:
                existing_alias = alias
                break
        
        if existing_alias:
            alias_id = existing_alias['agentAliasId']
            print(f"[INFO] Using existing alias: {alias_id}\n")
        else:
            alias_response = bedrock_agent.create_agent_alias(
                agentId=agent_id,
                agentAliasName=alias_name,
                description='Production alias for BreakGlass Guardian'
            )
            alias_id = alias_response['agentAlias']['agentAliasId']
            print(f"[OK] Alias created: {alias_id}\n")
        
    except Exception as e:
        print(f"[WARN] Alias creation: {e}")
        alias_id = "TSTALIASID"
    
    # Print summary
    print("="*60)
    print("✓ Bedrock Agent Setup Complete!")
    print("="*60 + "\n")
    
    print(f"Agent ID: {agent_id}")
    print(f"Alias ID: {alias_id}")
    print(f"Model: anthropic.claude-sonnet-4-5-20250929-v1:0")
    print()
    
    print("Update your .env file with:")
    print(f"BEDROCK_AGENT_ID={agent_id}")
    print(f"BEDROCK_AGENT_ALIAS_ID={alias_id}")
    print()
    
    return {
        'agent_id': agent_id,
        'alias_id': alias_id
    }

if __name__ == "__main__":
    try:
        result = create_bedrock_agent()
        if result:
            print("[SUCCESS] Bedrock Agent is ready!")
            exit(0)
        else:
            print("[FAILED] Could not create Bedrock Agent")
            exit(1)
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        exit(1)
