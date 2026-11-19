"""Optional Bedrock analysis performed only after backend policy validation."""
import json
from typing import Any

import boto3

from backend.config import settings
from backend.models.access_request import AccessRequest


class BedrockAgent:
    """Invoke Bedrock for supplementary analysis without delegating authorization."""

    def __init__(self) -> None:
        if not settings.bedrock_enabled:
            raise RuntimeError("Bedrock integration is disabled")
        self.agent_client = boto3.client("bedrock-agent-runtime", region_name=settings.aws_region)
        self.runtime_client = boto3.client("bedrock-runtime", region_name=settings.aws_region)

    def analyze(self, request: AccessRequest) -> dict[str, Any]:
        payload = {
            "emergency_description": request.emergency_description,
            "requested_action": request.requested_action,
            "resource_type": request.resource_type.value,
            "resource_id": request.resource_id,
            "business_justification": request.business_justification,
        }

        if settings.bedrock_agent_id and not settings.bedrock_agent_id.startswith("DEMO"):
            return self._invoke_agent(payload, request.request_id)

        return self._invoke_model(payload)

    def _invoke_agent(self, payload: dict[str, Any], request_id: str | None) -> dict[str, Any]:
        response = self.agent_client.invoke_agent(
            agentId=settings.bedrock_agent_id,
            agentAliasId=settings.bedrock_agent_alias_id,
            sessionId=request_id or "request-analysis",
            inputText=json.dumps(payload),
        )
        content = b"".join(
            event["chunk"]["bytes"]
            for event in response.get("completion", [])
            if "chunk" in event
        ).decode("utf-8")
        return self._parse_json(content)

    def _invoke_model(self, payload: dict[str, Any]) -> dict[str, Any]:
        prompt = (
            "Analyze this emergency AWS access request and return a JSON object only. "
            "Do not grant access or approve it. Include explanation and risk notes.\n"
            + json.dumps(payload)
        )
        response = self.runtime_client.invoke_model(
            modelId=settings.bedrock_model_id,
            body=json.dumps({
                "messages": [
                    {
                        "role": "user",
                        "content": [{"text": prompt}],
                    }
                ],
                "inferenceConfig": {
                    "maxTokens": 300,
                    "temperature": 0,
                },
            }),
            contentType="application/json",
            accept="application/json",
        )
        body = json.loads(response["body"].read())
        content = ""
        message = body.get("output", {}).get("message", {})
        content = "".join(
            block.get("text", "")
            for block in message.get("content", [])
            if isinstance(block, dict)
        )
        if not content:
            content = "".join(
                block.get("text", "")
                for block in body.get("content", [])
                if isinstance(block, dict)
            )
        return self._parse_json(content)

    @staticmethod
    def _parse_json(content: str) -> dict[str, Any]:
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Bedrock returned a non-JSON analysis") from exc
        if not isinstance(parsed, dict):
            raise RuntimeError("Bedrock analysis must be a JSON object")
        return parsed
