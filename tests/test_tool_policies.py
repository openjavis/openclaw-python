"""
Tests for tool policies
"""

from datetime import UTC, datetime, timezone

import pytest

from openclaw.agents.tools.policies import (
    ApprovalRequiredPolicy,
    ArgumentValidationPolicy,
    BlacklistPolicy,
    PolicyDecision,
    PolicyManager,
    PolicyViolation,
    RateLimitPolicy,
    TimeWindowPolicy,
    WhitelistPolicy,
)


class TestPolicyDecision:
    """Test PolicyDecision enum"""

    def test_decision_values(self):
        """Test enum values"""
        assert PolicyDecision.ALLOW == "allow"
        assert PolicyDecision.DENY == "deny"
        assert PolicyDecision.REQUIRE_APPROVAL == "require_approval"


class TestWhitelistPolicy:
    """Test WhitelistPolicy"""

    def test_allowed_tool(self):
        """Test allowed tool"""
        policy = WhitelistPolicy(["bash", "read_file"])

        decision = policy.evaluate("bash", {}, {})
        assert decision == PolicyDecision.ALLOW

    def test_denied_tool(self):
        """Test denied tool"""
        policy = WhitelistPolicy(["bash"])

        decision = policy.evaluate("rm", {}, {})
        assert decision == PolicyDecision.DENY


class TestBlacklistPolicy:
    """Test BlacklistPolicy"""

    def test_allowed_tool(self):
        """Test allowed tool"""
        policy = BlacklistPolicy(["rm", "delete"])

        decision = policy.evaluate("bash", {}, {})
        assert decision == PolicyDecision.ALLOW

    def test_denied_tool(self):
        """Test denied tool"""
        policy = BlacklistPolicy(["rm"])

        decision = policy.evaluate("rm", {}, {})
        assert decision == PolicyDecision.DENY


class TestRateLimitPolicy:
    """Test RateLimitPolicy"""

    def test_within_limit(self):
        """Test calls within limit"""
        policy = RateLimitPolicy(max_calls=3, window_seconds=60)

        # First 3 calls should be allowed
        assert policy.evaluate("bash", {}, {}) == PolicyDecision.ALLOW
        assert policy.evaluate("bash", {}, {}) == PolicyDecision.ALLOW
        assert policy.evaluate("bash", {}, {}) == PolicyDecision.ALLOW

    def test_exceeds_limit(self):
        """Test calls exceeding limit"""
        policy = RateLimitPolicy(max_calls=2, window_seconds=60)

        policy.evaluate("bash", {}, {})
        policy.evaluate("bash", {}, {})

        # Third call should be denied
        decision = policy.evaluate("bash", {}, {})
        assert decision == PolicyDecision.DENY

    def test_per_tool_limit(self):
        """Test per-tool rate limiting"""
        policy = RateLimitPolicy(max_calls=1, window_seconds=60, per_tool=True)

        # Each tool gets its own limit
        assert policy.evaluate("bash", {}, {}) == PolicyDecision.ALLOW
        assert policy.evaluate("read_file", {}, {}) == PolicyDecision.ALLOW

        # Second call to same tool should be denied
        assert policy.evaluate("bash", {}, {}) == PolicyDecision.DENY

    def test_global_limit(self):
        """Test global rate limiting"""
        policy = RateLimitPolicy(max_calls=2, window_seconds=60, per_tool=False)

        policy.evaluate("bash", {}, {})
        policy.evaluate("read_file", {}, {})

        # Third call (any tool) should be denied
        assert policy.evaluate("other", {}, {}) == PolicyDecision.DENY


class TestTimeWindowPolicy:
    """Test TimeWindowPolicy"""

    def test_all_hours_allowed(self):
        """Test policy allowing all hours"""
        policy = TimeWindowPolicy(start_hour=0, end_hour=24)

        decision = policy.evaluate("bash", {}, {})
        assert decision == PolicyDecision.ALLOW

    def test_current_hour_in_window(self):
        """Test with current hour in window"""
        now = datetime.now(UTC)
        # Ensure end_hour is greater than start_hour for simple window
        policy = TimeWindowPolicy(
            start_hour=now.hour, end_hour=min(now.hour + 2, 24)  # Don't wrap around
        )

        decision = policy.evaluate("bash", {}, {})
        assert decision == PolicyDecision.ALLOW


class TestArgumentValidationPolicy:
    """Test ArgumentValidationPolicy"""

    def test_no_validator(self):
        """Test tool with no validator"""
        policy = ArgumentValidationPolicy()

        decision = policy.evaluate("bash", {"command": "ls"}, {})
        assert decision == PolicyDecision.ALLOW

    def test_valid_arguments(self):
        """Test with valid arguments"""

        def validate_bash(args):
            return "command" in args

        policy = ArgumentValidationPolicy({"bash": validate_bash})

        decision = policy.evaluate("bash", {"command": "ls"}, {})
        assert decision == PolicyDecision.ALLOW

    def test_invalid_arguments(self):
        """Test with invalid arguments"""

        def validate_bash(args):
            return "command" in args

        policy = ArgumentValidationPolicy({"bash": validate_bash})

        decision = policy.evaluate("bash", {}, {})
        assert decision == PolicyDecision.DENY


class TestApprovalRequiredPolicy:
    """Test ApprovalRequiredPolicy"""

    def test_requires_approval(self):
        """Test tool requiring approval"""
        policy = ApprovalRequiredPolicy(["dangerous_tool"])

        decision = policy.evaluate("dangerous_tool", {}, {})
        assert decision == PolicyDecision.REQUIRE_APPROVAL

    def test_no_approval_needed(self):
        """Test tool not requiring approval"""
        policy = ApprovalRequiredPolicy(["dangerous_tool"])

        decision = policy.evaluate("safe_tool", {}, {})
        assert decision == PolicyDecision.ALLOW


class TestPolicyManager:
    """Test PolicyManager"""

    def test_init(self):
        """Test initializing manager"""
        manager = PolicyManager()
        assert len(manager.policies) == 0

    def test_add_policy(self):
        """Test adding a policy"""
        manager = PolicyManager()
        policy = WhitelistPolicy(["bash"])

        manager.add_policy(policy)
        assert len(manager.policies) == 1

    def test_remove_policy(self):
        """Test removing a policy"""
        manager = PolicyManager()
        policy = WhitelistPolicy(["bash"])
        manager.add_policy(policy)

        removed = manager.remove_policy("whitelist")
        assert removed
        assert len(manager.policies) == 0

    def test_evaluate_no_policies(self):
        """Test evaluation with no policies"""
        manager = PolicyManager()

        decision = manager.evaluate("bash", {}, {})
        assert decision == PolicyDecision.ALLOW

    def test_evaluate_allow(self):
        """Test evaluation returning ALLOW"""
        manager = PolicyManager()
        manager.add_policy(WhitelistPolicy(["bash"]))

        decision = manager.evaluate("bash", {}, {})
        assert decision == PolicyDecision.ALLOW

    def test_evaluate_deny(self):
        """Test evaluation returning DENY"""
        manager = PolicyManager()
        manager.add_policy(WhitelistPolicy(["bash"]))

        decision = manager.evaluate("rm", {}, {})
        assert decision == PolicyDecision.DENY

    def test_evaluate_require_approval(self):
        """Test evaluation returning REQUIRE_APPROVAL"""
        manager = PolicyManager()
        manager.add_policy(ApprovalRequiredPolicy(["dangerous"]))

        decision = manager.evaluate("dangerous", {}, {})
        assert decision == PolicyDecision.REQUIRE_APPROVAL

    def test_deny_takes_precedence(self):
        """Test that DENY takes precedence over other decisions"""
        manager = PolicyManager()
        manager.add_policy(WhitelistPolicy(["bash"]))  # Would allow
        manager.add_policy(BlacklistPolicy(["bash"]))  # Would deny

        decision = manager.evaluate("bash", {}, {})
        assert decision == PolicyDecision.DENY

    def test_approval_takes_precedence_over_allow(self):
        """Test that REQUIRE_APPROVAL takes precedence over ALLOW"""
        manager = PolicyManager()
        manager.add_policy(WhitelistPolicy(["bash"]))  # Would allow
        manager.add_policy(ApprovalRequiredPolicy(["bash"]))  # Requires approval

        decision = manager.evaluate("bash", {}, {})
        assert decision == PolicyDecision.REQUIRE_APPROVAL

    def test_check_and_enforce_allow(self):
        """Test check_and_enforce with allowed tool"""
        manager = PolicyManager()
        manager.add_policy(WhitelistPolicy(["bash"]))

        # Should not raise
        manager.check_and_enforce("bash", {}, {})

    def test_check_and_enforce_deny(self):
        """Test check_and_enforce with denied tool"""
        manager = PolicyManager()
        manager.add_policy(WhitelistPolicy(["bash"]))

        with pytest.raises(PolicyViolation):
            manager.check_and_enforce("rm", {}, {})

    def test_check_and_enforce_approval(self):
        """Test check_and_enforce with approval required"""
        manager = PolicyManager()
        manager.add_policy(ApprovalRequiredPolicy(["dangerous"]))

        with pytest.raises(PolicyViolation):
            manager.check_and_enforce("dangerous", {}, {})

    def test_audit_log(self):
        """Test audit logging"""
        manager = PolicyManager()
        manager.add_policy(WhitelistPolicy(["bash"]))

        manager.evaluate("bash", {}, {})
        manager.evaluate("rm", {}, {})

        log = manager.get_audit_log()
        assert len(log) == 2
        assert log[0]["tool"] == "bash"
        assert log[1]["tool"] == "rm"

    def test_audit_log_limit(self):
        """Test audit log with limit"""
        manager = PolicyManager()
        manager.add_policy(WhitelistPolicy(["bash"]))

        for i in range(5):
            manager.evaluate("bash", {}, {})

        log = manager.get_audit_log(limit=2)
        assert len(log) == 2

    def test_clear_audit_log(self):
        """Test clearing audit log"""
        manager = PolicyManager()
        manager.add_policy(WhitelistPolicy(["bash"]))

        manager.evaluate("bash", {}, {})
        manager.clear_audit_log()

        log = manager.get_audit_log()
        assert len(log) == 0
