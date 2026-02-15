"""
Tool policy system - aligned with openclaw-ts agents/tool-policy.ts

Multi-layer tool policy resolution with profile-based configurations.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal, Dict, List, Set

logger = logging.getLogger(__name__)


@dataclass
class ToolPolicy:
    """
    Tool policy configuration - aligned with openclaw-ts ToolPolicy
    
    Supports multi-layer configuration:
    - profile: Named policy presets (default, strict, permissive, coding)
    - allow: Explicit allowlist
    - deny: Explicit denylist
    - by_provider: Provider-specific overrides
    """
    profile: Literal["default", "strict", "permissive", "coding"] | None = None
    allow: List[str] | None = None  # Allowlist
    deny: List[str] | None = None   # Denylist
    by_provider: Dict[str, "ToolPolicy"] | None = None  # Provider-level policies


@dataclass
class PluginGroup:
    """
    Plugin tool group - aligned with openclaw-ts
    
    Groups related tools for easier policy configuration
    """
    name: str
    tools: List[str]


class ToolPolicyResolver:
    """
    Multi-layer tool policy resolver - aligned with openclaw-ts
    
    Resolution order:
    1. Profile Policy (tools.profile)
    2. Provider Profile (tools.byProvider[provider].profile)
    3. Global Allowlist (tools.allow)
    4. Provider Allowlist (tools.byProvider[provider].allow)
    5. Agent Allowlist (agents[id].tools.allow)
    6. Agent Provider Allowlist (agents[id].tools.byProvider[provider].allow)
    7. Global Denylist (tools.deny)
    8. Owner-only tools (filtered if not owner)
    
    Policy profiles:
    - default: Core tools for general use
    - strict: Minimal read-only tools
    - permissive: All available tools
    - coding: Tools optimized for code editing and development
    """
    
    # Profile definitions - aligned with openclaw-ts
    PROFILES: Dict[str, List[str]] = {
        "default": [
            # Core tools
            "bash",
            "read_file",
            "write_file",
            "edit_file",
            "web_search",
            "web_fetch",
            "list_files",
            "find_files",
            "grep",
            "send_message",
            # Utility tools
            "python_repl",
            "calculator",
            "datetime",
            "cron",
        ],
        "strict": [
            # Read-only tools
            "read_file",
            "list_files",
            "find_files",
            "grep",
            "web_search",
            "web_fetch",
            "datetime",
        ],
        "permissive": ["*"],  # All tools
        "coding": [
            # Development tools
            "bash",
            "read_file",
            "write_file",
            "edit_file",
            "apply_patch",
            "list_files",
            "find_files",
            "grep",
            "semantic_search",
            "read_lints",
            # Version control
            "git_status",
            "git_diff",
            "git_log",
            "git_commit",
            # Build tools
            "npm_install",
            "npm_run",
            "cargo_build",
            "make",
            # Testing
            "run_tests",
            "pytest",
        ],
    }
    
    # Owner-only tools - aligned with openclaw-ts
    OWNER_ONLY_TOOLS: Set[str] = {
        "bash",  # Shell access
        "python_repl",  # Code execution
        "eval",  # Arbitrary evaluation
        "exec",  # System commands
        "delete_file",  # Destructive operations
        "move_file",
        "send_message",  # Communication
    }
    
    def __init__(
        self, 
        core_tools: List[str],
        plugin_groups: Dict[str, PluginGroup] | None = None
    ):
        """
        Initialize policy resolver
        
        Args:
            core_tools: List of available core tool names
            plugin_groups: Optional plugin groups for group: references
        """
        self.core_tools = set(core_tools)
        self.plugin_groups = plugin_groups or {}
    
    def resolve(
        self,
        policy: ToolPolicy,
        provider: str,
        sender_is_owner: bool = True,
    ) -> List[str]:
        """
        Resolve tool policy to final tool list - aligned with openclaw-ts resolveToolPolicy()
        
        Args:
            policy: Tool policy configuration
            provider: LLM provider name
            sender_is_owner: Whether sender is the owner (affects owner-only tools)
            
        Returns:
            List of allowed tool names
        """
        # 1. Expand plugin group references (e.g., "group:plugins")
        expanded_policy = self._expand_plugin_groups(policy)
        
        # 2. Apply base profile
        allowed = self._apply_profile(expanded_policy.profile or "default")
        
        # 3. Apply provider-level profile (overrides base)
        if expanded_policy.by_provider and provider in expanded_policy.by_provider:
            provider_policy = expanded_policy.by_provider[provider]
            if provider_policy.profile:
                allowed = self._apply_profile(provider_policy.profile)
        
        # 4. Apply global allowlist (intersection)
        if expanded_policy.allow is not None:
            allowed &= set(expanded_policy.allow)
        
        # 5. Apply provider-level allowlist (intersection)
        if expanded_policy.by_provider and provider in expanded_policy.by_provider:
            provider_policy = expanded_policy.by_provider[provider]
            if provider_policy.allow is not None:
                allowed &= set(provider_policy.allow)
        
        # 6. Apply global denylist (subtraction)
        if expanded_policy.deny:
            allowed -= set(expanded_policy.deny)
        
        # 7. Apply provider-level denylist (subtraction)
        if expanded_policy.by_provider and provider in expanded_policy.by_provider:
            provider_policy = expanded_policy.by_provider[provider]
            if provider_policy.deny:
                allowed -= set(provider_policy.deny)
        
        # 8. Filter owner-only tools if not owner
        if not sender_is_owner:
            allowed -= self.OWNER_ONLY_TOOLS
            logger.debug(f"Filtered owner-only tools (sender is not owner)")
        
        # Filter to only available tools
        allowed = allowed & self.core_tools
        
        logger.debug(
            f"Resolved policy for provider={provider}, owner={sender_is_owner}: "
            f"{len(allowed)} tools allowed"
        )
        
        return sorted(list(allowed))
    
    def _apply_profile(self, profile: str) -> Set[str]:
        """
        Apply a profile to get initial tool set
        
        Args:
            profile: Profile name
            
        Returns:
            Set of allowed tools
        """
        if profile not in self.PROFILES:
            logger.warning(f"Unknown profile '{profile}', using 'default'")
            profile = "default"
        
        profile_tools = self.PROFILES[profile]
        
        # Handle wildcard profile (permissive)
        if "*" in profile_tools:
            return self.core_tools.copy()
        
        return set(profile_tools)
    
    def _expand_plugin_groups(self, policy: ToolPolicy) -> ToolPolicy:
        """
        Expand plugin group references - aligned with openclaw-ts
        
        Converts "group:name" references to actual tool lists
        
        Args:
            policy: Tool policy with possible group references
            
        Returns:
            Policy with expanded tool lists
        """
        if not policy.allow:
            return policy
        
        expanded_allow = []
        for item in policy.allow:
            if item.startswith("group:"):
                group_name = item[6:]  # Remove "group:" prefix
                if group_name in self.plugin_groups:
                    group = self.plugin_groups[group_name]
                    expanded_allow.extend(group.tools)
                    logger.debug(f"Expanded group:{group_name} to {len(group.tools)} tools")
                else:
                    logger.warning(f"Unknown plugin group: {group_name}")
            else:
                expanded_allow.append(item)
        
        # Create new policy with expanded allow list
        return ToolPolicy(
            profile=policy.profile,
            allow=expanded_allow,
            deny=policy.deny,
            by_provider=policy.by_provider
        )
    
    def add_plugin_group(self, group: PluginGroup) -> None:
        """
        Register a plugin group
        
        Args:
            group: Plugin group to register
        """
        self.plugin_groups[group.name] = group
        logger.debug(f"Registered plugin group: {group.name} ({len(group.tools)} tools)")
    
    def is_owner_only(self, tool_name: str) -> bool:
        """
        Check if a tool is owner-only
        
        Args:
            tool_name: Tool name
            
        Returns:
            True if tool is owner-only
        """
        return tool_name in self.OWNER_ONLY_TOOLS


def create_default_policy() -> ToolPolicy:
    """
    Create default tool policy - aligned with openclaw-ts
    
    Returns:
        Default tool policy
    """
    return ToolPolicy(profile="default")


def create_strict_policy() -> ToolPolicy:
    """
    Create strict (read-only) tool policy
    
    Returns:
        Strict tool policy
    """
    return ToolPolicy(profile="strict")


def create_permissive_policy() -> ToolPolicy:
    """
    Create permissive (all tools) policy
    
    Returns:
        Permissive tool policy
    """
    return ToolPolicy(profile="permissive")


def create_coding_policy() -> ToolPolicy:
    """
    Create coding-optimized tool policy
    
    Returns:
        Coding tool policy
    """
    return ToolPolicy(profile="coding")
