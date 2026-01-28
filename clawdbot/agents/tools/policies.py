"""
Enhanced tool execution policies and access control
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class PolicyDecision(str, Enum):
    """Policy decision result"""

    ALLOW = "allow"  # Allow execution
    DENY = "deny"  # Deny execution
    REQUIRE_APPROVAL = "require_approval"  # Require user approval


class PolicyViolation(Exception):
    """Exception raised when a tool policy is violated"""

    def __init__(self, message: str, policy_name: str, tool_name: str):
        super().__init__(message)
        self.policy_name = policy_name
        self.tool_name = tool_name


class ToolPolicy:
    """
    Base class for tool execution policies

    Policies can control:
    - Which tools can be used
    - When tools can be used
    - How often tools can be used
    - What arguments are allowed
    """

    def __init__(self, name: str):
        """
        Initialize policy

        Args:
            name: Policy name
        """
        self.name = name
        self.enabled = True

    def evaluate(
        self, tool_name: str, arguments: dict[str, Any], context: dict[str, Any]
    ) -> PolicyDecision:
        """
        Evaluate if tool execution should be allowed

        Args:
            tool_name: Name of the tool
            arguments: Tool arguments
            context: Execution context (session, user, etc.)

        Returns:
            PolicyDecision
        """
        raise NotImplementedError


class WhitelistPolicy(ToolPolicy):
    """Allow only whitelisted tools"""

    def __init__(self, allowed_tools: list[str]):
        """
        Initialize whitelist policy

        Args:
            allowed_tools: List of allowed tool names
        """
        super().__init__("whitelist")
        self.allowed_tools = set(allowed_tools)

    def evaluate(self, tool_name: str, arguments: dict, context: dict) -> PolicyDecision:
        if tool_name in self.allowed_tools:
            return PolicyDecision.ALLOW
        return PolicyDecision.DENY


class BlacklistPolicy(ToolPolicy):
    """Deny blacklisted tools"""

    def __init__(self, denied_tools: list[str]):
        """
        Initialize blacklist policy

        Args:
            denied_tools: List of denied tool names
        """
        super().__init__("blacklist")
        self.denied_tools = set(denied_tools)

    def evaluate(self, tool_name: str, arguments: dict, context: dict) -> PolicyDecision:
        if tool_name in self.denied_tools:
            return PolicyDecision.DENY
        return PolicyDecision.ALLOW


class RateLimitPolicy(ToolPolicy):
    """Rate limit tool usage"""

    def __init__(self, max_calls: int, window_seconds: int = 60, per_tool: bool = True):
        """
        Initialize rate limit policy

        Args:
            max_calls: Maximum calls allowed
            window_seconds: Time window in seconds
            per_tool: Apply limit per tool (True) or globally (False)
        """
        super().__init__("rate_limit")
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.per_tool = per_tool
        self._call_history: dict[str, list[datetime]] = {}

    def evaluate(self, tool_name: str, arguments: dict, context: dict) -> PolicyDecision:
        key = tool_name if self.per_tool else "global"
        now = datetime.now(UTC)

        # Initialize history
        if key not in self._call_history:
            self._call_history[key] = []

        # Clean old entries
        cutoff = now - timedelta(seconds=self.window_seconds)
        self._call_history[key] = [ts for ts in self._call_history[key] if ts > cutoff]

        # Check limit
        if len(self._call_history[key]) >= self.max_calls:
            logger.warning(
                f"Rate limit exceeded for {key}: "
                f"{len(self._call_history[key])}/{self.max_calls} "
                f"in {self.window_seconds}s"
            )
            return PolicyDecision.DENY

        # Record this call
        self._call_history[key].append(now)
        return PolicyDecision.ALLOW


class TimeWindowPolicy(ToolPolicy):
    """Allow tools only during specific time windows"""

    def __init__(
        self, start_hour: int = 0, end_hour: int = 24, allowed_days: list[int] | None = None
    ):
        """
        Initialize time window policy

        Args:
            start_hour: Start hour (0-23)
            end_hour: End hour (0-24)
            allowed_days: List of allowed weekdays (0=Monday, 6=Sunday), None=all days
        """
        super().__init__("time_window")
        self.start_hour = start_hour
        self.end_hour = end_hour
        self.allowed_days = set(allowed_days) if allowed_days else None

    def evaluate(self, tool_name: str, arguments: dict, context: dict) -> PolicyDecision:
        now = datetime.now(UTC)

        # Check day of week
        if self.allowed_days and now.weekday() not in self.allowed_days:
            logger.info(f"Tool {tool_name} denied: not an allowed day")
            return PolicyDecision.DENY

        # Check hour
        if not (self.start_hour <= now.hour < self.end_hour):
            logger.info(f"Tool {tool_name} denied: outside time window")
            return PolicyDecision.DENY

        return PolicyDecision.ALLOW


class ArgumentValidationPolicy(ToolPolicy):
    """Validate tool arguments against rules"""

    def __init__(self, validators: dict[str, Callable[[Any], bool]] | None = None):
        """
        Initialize argument validation policy

        Args:
            validators: Dict mapping tool names to validation functions
        """
        super().__init__("argument_validation")
        self.validators = validators or {}

    def evaluate(self, tool_name: str, arguments: dict, context: dict) -> PolicyDecision:
        if tool_name not in self.validators:
            return PolicyDecision.ALLOW

        try:
            validator = self.validators[tool_name]
            if validator(arguments):
                return PolicyDecision.ALLOW
            else:
                logger.warning(f"Argument validation failed for {tool_name}")
                return PolicyDecision.DENY
        except Exception as e:
            logger.error(f"Validator error for {tool_name}: {e}")
            return PolicyDecision.DENY


class ApprovalRequiredPolicy(ToolPolicy):
    """Require approval for specific tools"""

    def __init__(self, tools_requiring_approval: list[str]):
        """
        Initialize approval policy

        Args:
            tools_requiring_approval: List of tool names requiring approval
        """
        super().__init__("approval_required")
        self.tools_requiring_approval = set(tools_requiring_approval)

    def evaluate(self, tool_name: str, arguments: dict, context: dict) -> PolicyDecision:
        if tool_name in self.tools_requiring_approval:
            return PolicyDecision.REQUIRE_APPROVAL
        return PolicyDecision.ALLOW


class PolicyManager:
    """
    Manage and enforce tool policies

    Features:
    - Multiple policy types
    - Policy chaining
    - Audit logging
    - Dynamic policy updates

    Example:
        manager = PolicyManager()
        manager.add_policy(WhitelistPolicy(["bash", "read_file"]))
        manager.add_policy(RateLimitPolicy(max_calls=10, window_seconds=60))

        decision = manager.evaluate("bash", {"command": "ls"}, context)
    """

    def __init__(self):
        """Initialize policy manager"""
        self.policies: list[ToolPolicy] = []
        self._audit_log: list[dict[str, Any]] = []

    def add_policy(self, policy: ToolPolicy) -> None:
        """
        Add a policy

        Args:
            policy: ToolPolicy instance
        """
        self.policies.append(policy)
        logger.info(f"Added policy: {policy.name}")

    def remove_policy(self, policy_name: str) -> bool:
        """
        Remove a policy by name

        Args:
            policy_name: Name of policy to remove

        Returns:
            True if removed, False if not found
        """
        for i, policy in enumerate(self.policies):
            if policy.name == policy_name:
                self.policies.pop(i)
                logger.info(f"Removed policy: {policy_name}")
                return True
        return False

    def evaluate(
        self, tool_name: str, arguments: dict[str, Any], context: dict[str, Any] | None = None
    ) -> PolicyDecision:
        """
        Evaluate all policies for a tool execution

        Args:
            tool_name: Tool name
            arguments: Tool arguments
            context: Execution context

        Returns:
            PolicyDecision (DENY takes precedence, then REQUIRE_APPROVAL, then ALLOW)
        """
        if context is None:
            context = {}

        decisions = []

        for policy in self.policies:
            if not policy.enabled:
                continue

            try:
                decision = policy.evaluate(tool_name, arguments, context)
                decisions.append((policy.name, decision))

                # Log decision
                self._audit_log.append(
                    {
                        "timestamp": datetime.now(UTC).isoformat(),
                        "policy": policy.name,
                        "tool": tool_name,
                        "decision": decision.value,
                    }
                )

            except Exception as e:
                logger.error(f"Policy {policy.name} evaluation error: {e}")
                decisions.append((policy.name, PolicyDecision.DENY))

        # Determine final decision (DENY > REQUIRE_APPROVAL > ALLOW)
        if any(d == PolicyDecision.DENY for _, d in decisions):
            logger.warning(f"Tool {tool_name} DENIED by policies")
            return PolicyDecision.DENY

        if any(d == PolicyDecision.REQUIRE_APPROVAL for _, d in decisions):
            logger.info(f"Tool {tool_name} requires APPROVAL")
            return PolicyDecision.REQUIRE_APPROVAL

        return PolicyDecision.ALLOW

    def check_and_enforce(
        self, tool_name: str, arguments: dict[str, Any], context: dict[str, Any] | None = None
    ) -> None:
        """
        Check policies and raise exception if denied

        Args:
            tool_name: Tool name
            arguments: Tool arguments
            context: Execution context

        Raises:
            PolicyViolation: If tool execution is denied
        """
        decision = self.evaluate(tool_name, arguments, context)

        if decision == PolicyDecision.DENY:
            raise PolicyViolation(
                f"Tool '{tool_name}' execution denied by policy", "unknown", tool_name
            )

        if decision == PolicyDecision.REQUIRE_APPROVAL:
            raise PolicyViolation(
                f"Tool '{tool_name}' requires approval", "approval_required", tool_name
            )

    def get_audit_log(self, limit: int | None = None) -> list[dict[str, Any]]:
        """
        Get audit log

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of audit log entries
        """
        if limit:
            return self._audit_log[-limit:]
        return self._audit_log.copy()

    def clear_audit_log(self) -> None:
        """Clear audit log"""
        self._audit_log.clear()
        logger.info("Cleared audit log")
