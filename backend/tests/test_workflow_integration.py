from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from backend.main import app
from backend.services.approval_service import approval_service
from backend.api.requests import _requests_store
from backend.api.sessions import _sessions_store


client = TestClient(app)


def setup_function():
    approval_service._approvals.clear()
    _requests_store.clear()
    _sessions_store.clear()


def request_payload():
    return {
        "requester_email": "engineer@company.com",
        "requester_name": "John Engineer",
        "emergency_description": "Production EC2 instance is unresponsive and causing downtime",
        "resource_type": "ec2",
        "resource_id": "i-1234567890abcdef0",
        "resource_region": "us-east-1",
        "requested_action": "restart_instance",
        "duration_minutes": 30,
        "business_justification": "Customer-facing application is down and needs recovery",
    }


def test_request_approval_session_and_revocation_lifecycle():
    response = client.post("/api/requests/", json=request_payload())
    assert response.status_code == 201
    body = response.json()
    approval_id = body["approval_id"]
    assert approval_id
    assert body["request"]["status"] == "pending_approval"

    approval_response = client.post(
        f"/api/approvals/{approval_id}/decide",
        json={
            "approval_id": approval_id,
            "approver_email": "admin@company.com",
            "approver_name": "Admin User",
            "decision": "APPROVED",
            "reason": "Emergency is justified and narrowly scoped",
            "mfa_verified": True,
        },
    )
    assert approval_response.status_code == 200
    approval = approval_response.json()
    assert approval["status"] == "approved"

    session_response = client.post(
        "/api/sessions/",
        json={
            "session_id": "sess_integration",
            "request_id": body["request"]["request_id"],
            "approval_id": approval_id,
            "requester_email": "engineer@company.com",
            "requester_name": "John Engineer",
            "resource_type": "ec2",
            "resource_id": "i-1234567890abcdef0",
            "resource_region": "us-east-1",
            "aws_account_id": "123456789012",
            "granted_permissions": [
                "ec2:RebootInstances",
                "ec2:DescribeInstances",
            ],
            "status": "creating",
            "expires_at": (datetime.utcnow() + timedelta(minutes=30)).isoformat(),
            "duration_minutes": 30,
        },
    )
    assert session_response.status_code == 201
    assert session_response.json()["status"] == "active"

    revoke_response = client.post(
        "/api/sessions/sess_integration/revoke",
        json={
            "session_id": "sess_integration",
            "revoked_by_email": "admin@company.com",
            "revoked_by_name": "Admin User",
            "revocation_reason": "Emergency has been resolved",
        },
    )
    assert revoke_response.status_code == 200
    assert revoke_response.json()["status"] == "revoked"


def test_approval_requires_mfa():
    response = client.post("/api/requests/", json=request_payload())
    approval_id = response.json()["approval_id"]

    decision_response = client.post(
        f"/api/approvals/{approval_id}/decide",
        json={
            "approval_id": approval_id,
            "approver_email": "admin@company.com",
            "approver_name": "Admin User",
            "decision": "APPROVED",
            "reason": "Emergency is justified and narrowly scoped",
            "mfa_verified": False,
        },
    )
    assert decision_response.status_code == 403
