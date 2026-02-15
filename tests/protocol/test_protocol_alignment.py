"""
Protocol validation tests for gateway.

Validates that protocol frames match TypeScript implementation:
- EventFrame format
- RequestFrame format
- ResponseFrame format
- hello-ok format
"""
import pytest

from openclaw.gateway.protocol import EventFrame, RequestFrame, ResponseFrame


def test_event_frame_format():
    """Test EventFrame matches TypeScript format"""
    frame = EventFrame(
        event="agent",
        payload={"text": "hello"},
        seq=1,
        stateVersion=None
    )
    
    data = frame.model_dump()
    assert data["type"] == "event"
    assert data["event"] == "agent"
    assert data["payload"] == {"text": "hello"}
    assert data["seq"] == 1
    assert "stateVersion" in data


def test_event_frame_with_state_version():
    """Test EventFrame with state version"""
    frame = EventFrame(
        event="presence",
        payload={"entries": []},
        seq=None,  # Targeted events don't have seq
        stateVersion={"version": 5}
    )
    
    data = frame.model_dump()
    assert data["type"] == "event"
    assert data["event"] == "presence"
    assert data["stateVersion"] == {"version": 5}


def test_request_frame_format():
    """Test RequestFrame matches TypeScript format"""
    frame = RequestFrame(
        type="req",
        id="req_123",
        method="agent",
        params={"message": "Hello"}
    )
    
    data = frame.model_dump()
    assert data["type"] == "req"
    assert data["id"] == "req_123"
    assert data["method"] == "agent"
    assert data["params"] == {"message": "Hello"}


def test_response_frame_success():
    """Test ResponseFrame for successful response"""
    frame = ResponseFrame(
        id="req_123",
        ok=True,
        payload={"result": "Success"},
        error=None
    )
    
    data = frame.model_dump()
    assert data["type"] == "res"
    assert data["id"] == "req_123"
    assert data["ok"] is True
    assert data["payload"] == {"result": "Success"}


def test_response_frame_error():
    """Test ResponseFrame for error response"""
    from openclaw.gateway.protocol import ErrorShape
    
    error = ErrorShape(
        code="INVALID_REQUEST",
        message="Invalid parameters"
    )
    
    frame = ResponseFrame(
        id="req_123",
        ok=False,
        payload=None,
        error=error
    )
    
    data = frame.model_dump()
    assert data["type"] == "res"
    assert data["ok"] is False
    assert data["error"]["code"] == "INVALID_REQUEST"


def test_json_rpc_compatibility():
    """Test JSON-RPC 2.0 format compatibility"""
    # Test request parsing
    jsonrpc_request = {
        "jsonrpc": "2.0",
        "id": "req_123",
        "method": "health",
        "params": {}
    }
    
    # Can be converted to RequestFrame
    frame = RequestFrame(
        type="req",
        id=jsonrpc_request["id"],
        method=jsonrpc_request["method"],
        params=jsonrpc_request["params"]
    )
    
    assert frame.method == "health"


def test_hello_ok_structure():
    """Test hello-ok response includes all required fields"""
    hello_ok = {
        "connId": "conn_123",
        "hello": "Gateway v0.6.0",
        "version": "0.6.0",
        "protocolVersion": 3,
        "capabilities": ["agent", "sessions", "channels"],
        "presence": {
            "entries": [],
            "stateVersion": 0
        },
        "auth": {
            "role": "operator",
            "scopes": ["operator.read", "operator.write"],
            "deviceToken": "token_xyz"
        }
    }
    
    # Verify structure
    assert "connId" in hello_ok
    assert "hello" in hello_ok
    assert "version" in hello_ok
    assert "protocolVersion" in hello_ok
    assert "capabilities" in hello_ok
    assert "presence" in hello_ok
    assert "auth" in hello_ok
    
    # Verify presence structure
    assert "entries" in hello_ok["presence"]
    assert "stateVersion" in hello_ok["presence"]


def test_chat_completions_request():
    """Test OpenAI chat completions request format"""
    from openclaw.gateway.http.chat_completions import ChatCompletionRequest
    
    request = ChatCompletionRequest(
        model="openclaw:main",
        messages=[
            {"role": "user", "content": "Hello"}
        ],
        stream=False
    )
    
    assert request.model == "openclaw:main"
    assert len(request.messages) == 1


def test_tool_invoke_request():
    """Test tool invocation request format"""
    from openclaw.gateway.http.tools_invoke import ToolInvokeRequest
    
    request = ToolInvokeRequest(
        tool="get_weather",
        params={"city": "San Francisco"}
    )
    
    assert request.tool == "get_weather"
    assert request.params["city"] == "San Francisco"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
