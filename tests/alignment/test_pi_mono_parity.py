"""
Alignment tests with pi-mono - verify parity with TypeScript implementation

Tests that Python implementation matches pi-mono behavior.
"""
import pytest

from openclaw.agents.agent_loop import AgentMessage, default_convert_to_llm
from openclaw.agents.events import AgentEventType
from openclaw.agents.tool_policy import ToolPolicyResolver, ToolPolicy


def test_event_types_complete():
    """Verify all required event types are present"""
    
    required_events = {
        "agent_start",
        "agent_end",
        "turn_start",
        "turn_end",
        "message_start",
        "message_update",
        "message_end",
        "tool_execution_start",
        "tool_execution_update",
        "tool_execution_end",
        "thinking_start",
        "thinking_delta",
        "thinking_end",
        "text_delta",
        "toolcall_start",
        "toolcall_delta",
        "toolcall_end",
        "error",
    }
    
    # Get all event type values
    actual_events = {e.value for e in AgentEventType}
    
    # Verify all required events are present
    missing = required_events - actual_events
    assert not missing, f"Missing event types: {missing}"


def test_message_conversion_filters_custom():
    """Verify custom messages are filtered during conversion"""
    
    messages = [
        AgentMessage(role="user", content="Hello", custom=False),
        AgentMessage(role="assistant", content="Internal note", custom=True),
        AgentMessage(role="assistant", content="Hi", custom=False),
    ]
    
    converted = default_convert_to_llm(messages)
    
    # Should filter out custom message
    assert len(converted) == 2
    assert converted[0].content == "Hello"
    assert converted[1].content == "Hi"


def test_tool_policy_profile_resolution():
    """Verify tool policy profile resolution matches pi-mono"""
    
    core_tools = ["bash", "read_file", "write_file", "web_search", "calculator"]
    resolver = ToolPolicyResolver(core_tools)
    
    # Test default profile
    policy = ToolPolicy(profile="default")
    tools = resolver.resolve(policy, provider="anthropic", sender_is_owner=True)
    assert "bash" in tools
    assert "read_file" in tools
    
    # Test strict profile
    policy = ToolPolicy(profile="strict")
    tools = resolver.resolve(policy, provider="anthropic", sender_is_owner=True)
    assert "read_file" in tools
    assert "bash" not in tools  # Not in strict profile
    
    # Test permissive profile
    policy = ToolPolicy(profile="permissive")
    tools = resolver.resolve(policy, provider="anthropic", sender_is_owner=True)
    assert len(tools) == len(core_tools)  # All tools


def test_tool_policy_owner_only_filtering():
    """Verify owner-only tools are filtered correctly"""
    
    core_tools = ["bash", "read_file", "write_file", "send_message"]
    resolver = ToolPolicyResolver(core_tools)
    
    policy = ToolPolicy(profile="default")
    
    # Owner should get all tools
    tools_owner = resolver.resolve(policy, provider="anthropic", sender_is_owner=True)
    assert "bash" in tools_owner
    assert "send_message" in tools_owner
    
    # Non-owner should not get owner-only tools
    tools_non_owner = resolver.resolve(policy, provider="anthropic", sender_is_owner=False)
    assert "bash" not in tools_non_owner  # Owner-only
    assert "send_message" not in tools_non_owner  # Owner-only
    assert "read_file" in tools_non_owner  # Not owner-only


def test_tool_policy_allowlist_intersection():
    """Verify allowlist applies as intersection"""
    
    core_tools = ["bash", "read_file", "write_file", "web_search", "calculator"]
    resolver = ToolPolicyResolver(core_tools)
    
    # Allowlist should intersect with profile
    policy = ToolPolicy(
        profile="default",
        allow=["bash", "read_file"]
    )
    
    tools = resolver.resolve(policy, provider="anthropic", sender_is_owner=True)
    assert set(tools) == {"bash", "read_file"}


def test_tool_policy_denylist_subtraction():
    """Verify denylist subtracts from allowed tools"""
    
    core_tools = ["bash", "read_file", "write_file", "web_search", "calculator"]
    resolver = ToolPolicyResolver(core_tools)
    
    # Denylist should subtract from profile
    policy = ToolPolicy(
        profile="default",
        deny=["bash"]
    )
    
    tools = resolver.resolve(policy, provider="anthropic", sender_is_owner=True)
    assert "bash" not in tools
    assert "read_file" in tools


def test_tool_policy_provider_override():
    """Verify provider-specific policies override global"""
    
    core_tools = ["bash", "read_file", "write_file", "web_search"]
    resolver = ToolPolicyResolver(core_tools)
    
    # Provider-specific profile overrides global
    policy = ToolPolicy(
        profile="default",
        by_provider={
            "gemini": ToolPolicy(profile="strict")
        }
    )
    
    # Gemini should use strict profile
    tools_gemini = resolver.resolve(policy, provider="gemini", sender_is_owner=True)
    assert "bash" not in tools_gemini  # Not in strict
    assert "read_file" in tools_gemini  # In strict
    
    # Anthropic should use default profile
    tools_anthropic = resolver.resolve(policy, provider="anthropic", sender_is_owner=True)
    assert "bash" in tools_anthropic  # In default


def test_agent_message_metadata():
    """Verify AgentMessage supports metadata"""
    
    msg = AgentMessage(
        role="user",
        content="Hello",
        metadata={"source": "web", "user_id": "123"}
    )
    
    assert msg.metadata["source"] == "web"
    assert msg.metadata["user_id"] == "123"


def test_agent_message_tool_fields():
    """Verify AgentMessage supports tool-related fields"""
    
    # Assistant message with tool calls
    msg_assistant = AgentMessage(
        role="assistant",
        content="",
        tool_calls=[{"id": "1", "name": "bash", "params": {}}]
    )
    assert msg_assistant.tool_calls is not None
    
    # Tool result message
    msg_tool = AgentMessage(
        role="toolResult",
        content="Result",
        tool_call_id="1"
    )
    assert msg_tool.tool_call_id == "1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
