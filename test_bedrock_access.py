#!/usr/bin/env python3
"""Test Bedrock API access"""

import json
import boto3
from botocore.exceptions import ClientError

def test_bedrock():
    print("\n" + "="*50)
    print("Testing AWS Bedrock Access")
    print("="*50 + "\n")
    
    try:
        # Create Bedrock client
        bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        
        # Test model invocation
        model_id = "anthropic.claude-sonnet-4-5-20250929-v1:0"
        
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 100,
            "messages": [
                {
                    "role": "user",
                    "content": "Say hello in one word"
                }
            ]
        })
        
        print(f"[INFO] Testing model: {model_id}")
        print(f"[INFO] Region: us-east-1\n")
        
        response = bedrock.invoke_model(
            modelId=model_id,
            body=body
        )
        
        response_body = json.loads(response['body'].read())
        content = response_body.get('content', [])
        
        if content:
            message = content[0].get('text', '')
            print(f"✅ [SUCCESS] Bedrock is working!")
            print(f"   Model response: {message}")
        else:
            print(f"⚠️  [WARNING] Response received but no content")
            
        print(f"\n✅ Bedrock API is fully functional!")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        print(f"❌ [ERROR] Bedrock access failed")
        print(f"   Error Code: {error_code}")
        print(f"   Message: {error_message}\n")
        
        if error_code == 'AccessDeniedException':
            print("📝 [ACTION REQUIRED]")
            print("   You need to enable model access in AWS Console:")
            print("   1. Go to: https://console.aws.amazon.com/bedrock/")
            print("   2. Click: Model access (left sidebar)")
            print("   3. Click: Manage model access")
            print("   4. Enable: Anthropic Claude models")
            print("   5. Click: Save changes")
            print("   6. Wait 1-2 minutes for activation\n")
        
        return False
        
    except Exception as e:
        print(f"❌ [ERROR] Unexpected error: {str(e)}\n")
        return False

if __name__ == "__main__":
    success = test_bedrock()
    exit(0 if success else 1)
