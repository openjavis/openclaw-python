"""
Tests for message conversion (Session → LLMMessage → Gemini)
"""
import pytest

from openclaw.agents.providers.base import LLMMessage
from openclaw.agents.session import Message


def test_llm_message_with_tool_calls():
    """Test that LLMMessage correctly stores tool_calls"""
    msg = LLMMessage(
        role="assistant",
        content="Let me search for that",
        tool_calls=[{
            "id": "call_123",
            "name": "web_search",
            "arguments": {"query": "python tutorial"}
        }]
    )
    
    assert msg.role == "assistant"
    assert msg.tool_calls is not None
    assert len(msg.tool_calls) == 1
    assert msg.tool_calls[0]["name"] == "web_search"


def test_llm_message_tool_result():
    """Test that LLMMessage correctly stores tool result information"""
    msg = LLMMessage(
        role="tool",
        content="Search results: ...",
        tool_call_id="call_123",
        name="web_search"
    )
    
    assert msg.role == "tool"
    assert msg.tool_call_id == "call_123"
    assert msg.name == "web_search"


def test_session_message_with_tool_calls():
    """Test that Session Message correctly stores tool_calls"""
    msg = Message(
        role="assistant",
        content="Let me search",
        tool_calls=[{
            "id": "call_123",
            "name": "web_search",
            "arguments": {"query": "test"}
        }]
    )
    
    assert msg.tool_calls is not None
    assert len(msg.tool_calls) == 1


def test_session_message_tool_result():
    """Test that Session Message correctly stores tool result"""
    msg = Message(
        role="tool",
        content="Results...",
        tool_call_id="call_123",
        name="web_search"
    )
    
    assert msg.tool_call_id == "call_123"
    assert msg.name == "web_search"


def test_session_message_serialization():
    """Test that Session Message serializes tool_calls correctly"""
    msg = Message(
        role="assistant",
        content="Test",
        tool_calls=[{"id": "123", "name": "test_tool", "arguments": {}}]
    )
    
    # Test Pydantic serialization
    data = msg.model_dump()
    
    assert "tool_calls" in data
    assert data["tool_calls"] is not None
    assert len(data["tool_calls"]) == 1


def test_session_message_deserialization():
    """Test that Session Message deserializes tool_calls correctly"""
    data = {
        "role": "assistant",
        "content": "Test",
        "timestamp": "2026-02-15T00:00:00",
        "tool_calls": [{"id": "123", "name": "test_tool", "arguments": {}}]
    }
    
    msg = Message(**data)
    
    assert msg.tool_calls is not None
    assert len(msg.tool_calls) == 1
    assert msg.tool_calls[0]["name"] == "test_tool"


def test_message_conversion_chain():
    """Test full conversion chain: Session Message → LLMMessage"""
    # Simulate a session message with tool calls
    session_msg = Message(
        role="assistant",
        content="I'll help you with that",
        tool_calls=[{
            "id": "call_abc",
            "name": "bash",
            "arguments": {"command": "ls -la"}
        }]
    )
    
    # Convert to LLMMessage (as done in runtime.py)
    llm_msg = LLMMessage(
        role=session_msg.role,
        content=session_msg.content,
        images=getattr(session_msg, 'images', None),
        tool_calls=getattr(session_msg, 'tool_calls', None),
        tool_call_id=getattr(session_msg, 'tool_call_id', None),
        name=getattr(session_msg, 'name', None)
    )
    
    # Verify conversion
    assert llm_msg.role == "assistant"
    assert llm_msg.tool_calls is not None
    assert len(llm_msg.tool_calls) == 1
    assert llm_msg.tool_calls[0]["name"] == "bash"


def test_tool_result_conversion_chain():
    """Test full conversion chain for tool result: Session Message → LLMMessage"""
    # Simulate a tool result message
    session_msg = Message(
        role="tool",
        content="Command output: ...",
        tool_call_id="call_abc",
        name="bash"
    )
    
    # Convert to LLMMessage
    llm_msg = LLMMessage(
        role=session_msg.role,
        content=session_msg.content,
        images=getattr(session_msg, 'images', None),
        tool_calls=getattr(session_msg, 'tool_calls', None),
        tool_call_id=getattr(session_msg, 'tool_call_id', None),
        name=getattr(session_msg, 'name', None)
    )
    
    # Verify conversion
    assert llm_msg.role == "tool"
    assert llm_msg.tool_call_id == "call_abc"
    assert llm_msg.name == "bash"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
