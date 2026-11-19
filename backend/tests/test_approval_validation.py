"""
Test Suite: Approval Validation
Tests the approval workflow security controls
"""
import pytest
from datetime import datetime, timedelta
from backend.models.access_request import AccessRequest
from backend.models.approval import ApprovalRequest, ApprovalDecision, ApprovalStatus
from backend.security.approval_validator import ApprovalValidator
from backend.security.identity_validator import IdentityValidator
from backend.config import settings


class TestApprovalValidation:
    """
    Test approval workflow security.
    No user should be able to approve their own request.
    """
    
    def setup_method(self):
        """Setup test data"""
        self.request = AccessRequest(
            request_id="req_test123",
            requester_email="engineer@company.com",
            requester_name="John Engineer",
            emergency_description="EC2 instance needs restart",
            resource_type="ec2",
            resource_id="i-1234567890abcdef0",
            requested_action="restart_instance",
            duration_minutes=30,
            business_justification="Application downtime"
        )
        
        # Compute request hash
        self.request_hash = ApprovalValidator.compute_request_hash(self.request)
        
        self.approval = ApprovalRequest(
            approval_id="appr_test456",
            request_id=self.request.request_id,
            requester_email=self.request.requester_email,
            requester_name=self.request.requester_name,
            emergency_description=self.request.emergency_description,
            resource_type=self.request.resource_type,
            resource_id=self.request.resource_id,
            requested_action=self.request.requested_action,
            duration_minutes=self.request.duration_minutes,
            business_justification=self.request.business_justification,
            risk_classification="MEDIUM",
            risk_score=50,
            recommended_permissions=["ec2:RebootInstances"],
            agent_recommendation="RECOMMEND_APPROVAL",
            risk_explanation="Narrowly scoped operational action",
            status=ApprovalStatus.APPROVED,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=60),
            request_hash=self.request_hash,
            approver_email="admin@company.com",
            approver_name="Admin User",
            approval_decision="APPROVED",
            approved_at=datetime.utcnow()
        )
    
    def test_self_approval_same_email(self):
        """
        Test 1: Self-Approval with Same Email
        
        Attack: User tries to approve their own request
        Expected: Blocked by identity validator
        """
        same_email = self.request.requester_email
        
        is_different, msg = IdentityValidator.check_self_approval(
            self.request.requester_email,
            same_email
        )
        
        assert not is_different, "Self-approval should be detected"
        assert "self-approval" in msg.lower(), "Error message should indicate self-approval"
        
        print("✅ Test 1 PASSED: Self-approval with same email blocked")
    
    def test_self_approval_email_alias(self):
        """
        Test 2: Self-Approval via Email Alias
        
        Attack: User uses +alias to appear as different user
        Expected: Blocked by email normalization
        """
        alias_email = self.request.requester_email.replace("@", "+admin@")
        
        is_different, msg = IdentityValidator.check_self_approval(
            self.request.requester_email,
            alias_email
        )
        
        assert not is_different, "Email alias should be detected"
        assert "alias" in msg.lower(), "Error message should indicate alias detection"
        
        print("✅ Test 2 PASSED: Self-approval via alias blocked")
    
    def test_expired_approval(self):
        """
        Test 3: Expired Approval
        
        Attack: Use approval after expiration time
        Expected: Blocked by expiration check
        """
        # Create expired approval
        expired_approval = ApprovalRequest(
            **{**self.approval.dict(), 
               "expires_at": datetime.utcnow() - timedelta(minutes=10)}
        )
        
        is_valid, msg = ApprovalValidator.check_approval_expiration(expired_approval)
        
        assert not is_valid, "Expired approval should be invalid"
        assert "expired" in msg.lower(), "Error message should indicate expiration"
        
        print("✅ Test 3 PASSED: Expired approval blocked")
    
    def test_approval_replay_attack(self):
        """
        Test 4: Approval Replay Attack
        
        Attack: Reuse already-used approval
        Expected: Blocked by used flag
        """
        # Mark approval as used
        used_approval = ApprovalRequest(
            **{**self.approval.dict(), 
               "used": True,
               "used_at": datetime.utcnow() - timedelta(minutes=5)}
        )
        
        is_unused, msg = ApprovalValidator.check_approval_used(used_approval)
        
        assert not is_unused, "Used approval should be detected"
        assert "already been used" in msg.lower(), "Error message should indicate replay"
        
        print("✅ Test 4 PASSED: Approval replay blocked")
    
    def test_request_parameter_tampering(self):
        """
        Test 5: Request Parameter Tampering
        
        Attack: Modify request after approval granted
        Expected: Blocked by hash verification
        """
        # Create modified request
        modified_request = AccessRequest(
            **{**self.request.dict(),
               "resource_id": "i-different-instance",  # Changed!
               "duration_minutes": 120}  # Changed!
        )
        
        is_authentic, msg = ApprovalValidator.verify_approval_authenticity(
            self.approval,
            modified_request
        )
        
        assert not is_authentic, "Tampering should be detected"
        assert "modified" in msg.lower() or "match" in msg.lower(), "Error should indicate mismatch"
        
        print("✅ Test 5 PASSED: Parameter tampering detected")
    
    def test_unauthorized_approver(self):
        """
        Test 6: Unauthorized Approver
        
        Attack: User not in approver list tries to approve
        Expected: Blocked by approver authorization check
        """
        unauthorized_email = "unauthorized@example.com"
        
        is_authorized, msg = IdentityValidator.validate_approver(
            unauthorized_email,
            "Unauthorized User"
        )
        
        assert not is_authorized, "Unauthorized approver should be rejected"
        assert "not an authorized approver" in msg.lower(), "Error should indicate lack of authorization"
        
        print("✅ Test 6 PASSED: Unauthorized approver blocked")
    
    def test_approval_hash_mismatch(self):
        """
        Test 7: Approval Hash Mismatch
        
        Attack: Forge approval with incorrect hash
        Expected: Blocked by hash verification
        """
        # Create approval with wrong hash
        forged_approval = ApprovalRequest(
            **{**self.approval.dict(),
               "request_hash": "wrong_hash_value_12345"}
        )
        
        is_authentic, msg = ApprovalValidator.verify_approval_authenticity(
            forged_approval,
            self.request
        )
        
        assert not is_authentic, "Hash mismatch should be detected"
        
        print("✅ Test 7 PASSED: Hash mismatch detected")
    
    def test_complete_validation_success(self):
        """
        Test 8: Complete Validation Success (Control Test)
        
        Verify: Valid approval passes all checks
        Expected: Validation succeeds
        """
        is_valid, errors = ApprovalValidator.validate_complete_approval(
            self.approval,
            self.request,
            "admin@company.com",  # Different from requester
            "Admin User"
        )
        
        assert is_valid, f"Valid approval should pass: {errors}"
        assert len(errors) == 0, "No errors should be present"
        
        print("✅ Test 8 PASSED: Valid approval accepted")
    
    def test_complete_validation_multiple_failures(self):
        """
        Test 9: Multiple Validation Failures
        
        Verify: Multiple failures are all detected
        Expected: All errors reported
        """
        # Create approval with multiple issues
        bad_approval = ApprovalRequest(
            **{**self.approval.dict(),
               "status": ApprovalStatus.REJECTED,  # Wrong status
               "expires_at": datetime.utcnow() - timedelta(minutes=10),  # Expired
               "used": True,  # Already used
               "request_hash": "wrong_hash"}  # Wrong hash
        )
        
        is_valid, errors = ApprovalValidator.validate_complete_approval(
            bad_approval,
            self.request,
            "admin@company.com",
            "Admin User"
        )
        
        assert not is_valid, "Invalid approval should fail"
        assert len(errors) >= 3, "Multiple errors should be detected"
        
        print(f"✅ Test 9 PASSED: Multiple failures detected ({len(errors)} errors)")
    
    def test_authorized_approver_in_list(self):
        """
        Test 10: Authorized Approver Validation
        
        Verify: Approvers in authorized list are accepted
        Expected: Validation succeeds for authorized approvers
        """
        # Use first authorized approver from settings
        if settings.authorized_approvers:
            authorized_email = settings.authorized_approvers[0]
            
            is_authorized, msg = IdentityValidator.validate_approver(
                authorized_email,
                "Authorized Admin"
            )
            
            assert is_authorized, "Authorized approver should be accepted"
            print("✅ Test 10 PASSED: Authorized approver accepted")
        else:
            print("⚠️  Test 10 SKIPPED: No authorized approvers configured")


def test_all_approval_validations():
    """Run all approval validation tests"""
    test_suite = TestApprovalValidation()
    
    print("\n" + "="*60)
    print("APPROVAL VALIDATION TEST SUITE")
    print("="*60 + "\n")
    
    test_suite.setup_method()
    test_suite.test_self_approval_same_email()
    
    test_suite.setup_method()
    test_suite.test_self_approval_email_alias()
    
    test_suite.setup_method()
    test_suite.test_expired_approval()
    
    test_suite.setup_method()
    test_suite.test_approval_replay_attack()
    
    test_suite.setup_method()
    test_suite.test_request_parameter_tampering()
    
    test_suite.setup_method()
    test_suite.test_unauthorized_approver()
    
    test_suite.setup_method()
    test_suite.test_approval_hash_mismatch()
    
    test_suite.setup_method()
    test_suite.test_complete_validation_success()
    
    test_suite.setup_method()
    test_suite.test_complete_validation_multiple_failures()
    
    test_suite.setup_method()
    test_suite.test_authorized_approver_in_list()
    
    print("\n" + "="*60)
    print("ALL APPROVAL VALIDATION TESTS PASSED ✅")
    print("="*60 + "\n")


if __name__ == "__main__":
    test_all_approval_validations()
