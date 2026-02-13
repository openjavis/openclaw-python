"""
Integration tests for core modules interaction

Tests how Session, Context, Tools, and Channels work together.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path


@pytest.mark.integration
class TestSessionToolIntegration:
    """Test Session and Tool integration."""
    
    @pytest.mark.asyncio
    async def test_tool_execution_recorded_in_session(self, tmp_path):
        """Test that tool execution is recorded in session."""
        from openclaw.agents.session import SessionManager
        from openclaw.agents.tools.registry import ToolRegistry
        
        workspace = tmp_path / "workspace"
        manager = SessionManager(workspace_dir=workspace)
        session = manager.get_or_create_session(session_id="tool-test")
        
        # Record tool call
        session.add_assistant_message(
            "Let me execute that",
            tool_calls=[{
                "id": "call_123",
                "type": "function",
                "function": {"name": "bash", "arguments": '{"command": "ls"}'}
            }]
        )
        
        # Record tool result
        session.add_tool_message(
            tool_call_id="call_123",
            content="file1.txt\nfile2.txt",
            name="bash"
        )
        
        # Verify recording
        messages = session.get_messages()
        assert len(messages) == 2
        assert messages[0].tool_calls is not None
        assert messages[1].role == "tool"
        
        print("✓ Tool execution recorded in session")


@pytest.mark.integration
class TestContextHistoryFlow:
    """Test context building with history."""
    
    @pytest.mark.asyncio
    async def test_build_context_with_long_history(self, tmp_path):
        """Test building context from long session history."""
        from openclaw.agents.session import SessionManager
        from openclaw.agents.context import (
            sanitize_session_history,
            limit_history_turns,
            convert_to_llm,
        )
        
        workspace = tmp_path / "workspace"
        manager = SessionManager(workspace_dir=workspace)
        session = manager.get_or_create_session(session_id="long-history")
        
        # Add many messages
        for i in range(50):
            session.add_user_message(f"Question {i}")
            session.add_assistant_message(f"Answer {i}")
        
        # Process with pipeline
        all_messages = session.get_messages()
        sanitized = sanitize_session_history(all_messages)
        limited = limit_history_turns(sanitized, limit=10)
        llm_messages = convert_to_llm(limited)
        
        # Should have limited messages
        assert len(llm_messages) < len(all_messages)
        assert len(llm_messages) <= 22  # ~10 user turns + 10 assistant + maybe a couple more
        
        print(f"✓ Long history handled: {len(all_messages)} → {len(llm_messages)}")


@pytest.mark.integration
class TestCompleteSystemFlow:
    """Test complete system workflow."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_message_processing(self, tmp_path):
        """Test end-to-end message processing."""
        from openclaw.agents.session import SessionManager
        from openclaw.agents.context import (
            sanitize_session_history,
            validate_anthropic_turns,
            convert_to_llm,
        )
        
        workspace = tmp_path / "workspace"
        manager = SessionManager(workspace_dir=workspace)
        
        # Simulate multi-turn conversation
        session = manager.get_or_create_session(
            channel="telegram",
            peer_kind="dm",
            peer_id="user123"
        )
        
        # Conversation
        session.add_system_message("You are a helpful coding assistant")
        session.add_user_message("Write a Python function")
        session.add_assistant_message("Sure! Here's a function...")
        session.add_user_message("Can you explain it?")
        session.add_assistant_message("Of course...")
        
        # Process for LLM
        messages = session.get_messages()
        sanitized = sanitize_session_history(messages)
        validated = validate_anthropic_turns(sanitized)
        llm_format = convert_to_llm(validated)
        
        # Verify structure
        assert llm_format[0]["role"] == "system"
        assert any(m["role"] == "user" for m in llm_format)
        assert any(m["role"] == "assistant" for m in llm_format)
        
        # Verify completeness
        user_count = sum(1 for m in llm_format if m["role"] == "user")
        assistant_count = sum(1 for m in llm_format if m["role"] == "assistant")
        
        assert user_count == 2
        assert assistant_count == 2
        
        print("✓ End-to-end flow complete and correct")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
