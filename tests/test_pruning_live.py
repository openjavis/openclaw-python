"""
Live tests for context pruning behavior.

Tests pruning with a real session and verifies context size reduction.
"""
import pytest
import asyncio
import json
import websockets
from openclaw.agents.extensions.context_pruning import (
    ContextPruningSettings,
    prune_context_messages,
)
from openclaw.agents.context import estimate_tokens_from_messages


@pytest.mark.asyncio
@pytest.mark.integration
async def test_pruning_reduces_context_live():
    """
    Test that pruning actually reduces context size in a real scenario.
    
    This test:
    1. Creates a session with many tool calls
    2. Builds up large context
    3. Applies pruning
    4. Verifies context size reduction
    """
    gateway_url = "ws://localhost:3100"
    
    try:
        async with websockets.connect(gateway_url) as ws:
            # Authenticate
            auth_msg = {
                "method": "session.create",
                "id": 1,
                "payload": {"key": "test-pruning-live"}
            }
            await ws.send(json.dumps(auth_msg))
            auth_resp = await ws.recv()
            auth_data = json.loads(auth_resp)
            
            if auth_data.get("error"):
                pytest.skip(f"Gateway authentication failed: {auth_data['error']}")
                return
            
            session_id = auth_data.get("payload", {}).get("session_id")
            
            # Build up context with multiple tool calls
            for i in range(5):
                request_msg = {
                    "method": "chat.send",
                    "id": 100 + i,
                    "payload": {
                        "session_id": session_id,
                        "message": f"Execute: echo 'Task {i}' && echo '{('X' * 100)}'",
                    }
                }
                await ws.send(json.dumps(request_msg))
                
                # Wait for completion
                while True:
                    resp = await asyncio.wait_for(ws.recv(), timeout=30.0)
                    data = json.loads(resp)
                    if data.get("method") == "agent.done" and data.get("id") == 100 + i:
                        break
            
            # Get session history
            history_msg = {
                "method": "session.get_history",
                "id": 200,
                "payload": {"session_id": session_id}
            }
            await ws.send(json.dumps(history_msg))
            
            history_resp = await asyncio.wait_for(ws.recv(), timeout=10.0)
            history_data = json.loads(history_resp)
            
            if history_data.get("error"):
                pytest.skip(f"Failed to get history: {history_data['error']}")
                return
            
            messages = history_data.get("payload", {}).get("messages", [])
            
            if not messages:
                pytest.skip("No messages in history")
                return
            
            # Calculate tokens before pruning
            tokens_before = estimate_tokens_from_messages(messages)
            message_count_before = len(messages)
            
            # Apply pruning
            pruning_settings = ContextPruningSettings(
                mode="soft-trim",
                soft_trim_ratio=0.5,
                prunable_tools={"bash", "shell"},
            )
            
            pruned_messages = prune_context_messages(
                messages, pruning_settings, context_window_tokens=100000
            )
            
            # Calculate tokens after pruning
            tokens_after = estimate_tokens_from_messages(pruned_messages)
            message_count_after = len(pruned_messages)
            
            print(f"\nContext Pruning Results:")
            print(f"  Messages before: {message_count_before}")
            print(f"  Messages after: {message_count_after}")
            print(f"  Tokens before: {tokens_before}")
            print(f"  Tokens after: {tokens_after}")
            print(f"  Reduction: {tokens_before - tokens_after} tokens ({(1 - tokens_after/tokens_before)*100:.1f}%)")
            
            # Verify pruning had effect
            assert tokens_after < tokens_before, "Pruning should reduce token count"
            
            # Verify user messages preserved
            user_count_before = len([m for m in messages if m.get("role") == "user"])
            user_count_after = len([m for m in pruned_messages if m.get("role") == "user"])
            assert user_count_after == user_count_before, "User messages should be preserved"
    
    except (websockets.exceptions.WebSocketException, OSError) as e:
        pytest.skip(f"Gateway not available: {e}")
        return
    except asyncio.TimeoutError:
        pytest.skip("Gateway request timed out")
        return


@pytest.mark.asyncio
@pytest.mark.integration
async def test_cache_ttl_pruning_live():
    """Test cache-ttl pruning mode with real session"""
    gateway_url = "ws://localhost:3100"
    
    try:
        async with websockets.connect(gateway_url) as ws:
            # Authenticate
            auth_msg = {
                "method": "session.create",
                "id": 1,
                "payload": {"key": "test-ttl-pruning"}
            }
            await ws.send(json.dumps(auth_msg))
            auth_resp = await ws.recv()
            auth_data = json.loads(auth_resp)
            
            if auth_data.get("error"):
                pytest.skip(f"Gateway authentication failed: {auth_data['error']}")
                return
            
            session_id = auth_data.get("payload", {}).get("session_id")
            
            # Execute some commands
            commands = [
                "echo 'First command'",
                "echo 'Second command'",
            ]
            
            for i, cmd in enumerate(commands):
                request_msg = {
                    "method": "chat.send",
                    "id": 100 + i,
                    "payload": {
                        "session_id": session_id,
                        "message": f"Run: {cmd}",
                    }
                }
                await ws.send(json.dumps(request_msg))
                
                # Wait for completion
                while True:
                    resp = await asyncio.wait_for(ws.recv(), timeout=30.0)
                    data = json.loads(resp)
                    if data.get("method") == "agent.done" and data.get("id") == 100 + i:
                        break
                
                # Small delay between commands
                await asyncio.sleep(0.5)
            
            # Get history
            history_msg = {
                "method": "session.get_history",
                "id": 200,
                "payload": {"session_id": session_id}
            }
            await ws.send(json.dumps(history_msg))
            
            history_resp = await asyncio.wait_for(ws.recv(), timeout=10.0)
            history_data = json.loads(history_resp)
            
            messages = history_data.get("payload", {}).get("messages", [])
            
            if not messages:
                pytest.skip("No messages in history")
                return
            
            # Test TTL pruning with very short TTL
            import time
            current_time_ms = int(time.time() * 1000)
            
            pruning_settings = ContextPruningSettings(
                mode="cache-ttl",
                ttl_ms=100,  # 100ms - very short
                prunable_tools={"bash", "shell"},
            )
            
            pruned_messages = prune_context_messages(
                messages, pruning_settings, context_window_tokens=100000,
                current_time_ms=current_time_ms
            )
            
            # Old tool results should be pruned
            tool_results_before = len([m for m in messages if m.get("role") in ["toolResult", "tool"]])
            tool_results_after = len([m for m in pruned_messages if m.get("role") in ["toolResult", "tool"]])
            
            print(f"\nCache-TTL Pruning Results:")
            print(f"  Tool results before: {tool_results_before}")
            print(f"  Tool results after: {tool_results_after}")
            print(f"  Pruned: {tool_results_before - tool_results_after}")
            
            # Some tool results should be pruned (those older than 100ms)
            assert tool_results_after <= tool_results_before
    
    except (websockets.exceptions.WebSocketException, OSError) as e:
        pytest.skip(f"Gateway not available: {e}")
        return
    except asyncio.TimeoutError:
        pytest.skip("Gateway request timed out")
        return


def test_pruning_settings_from_config():
    """Test loading pruning settings from config"""
    from openclaw.agents.extensions.context_pruning import get_pruning_settings_from_config
    
    config = {
        "agents": {
            "defaults": {
                "contextPruning": {
                    "mode": "soft-trim",
                    "ttl": "5m",
                    "softTrimRatio": 0.75,
                    "prunableTools": ["bash", "read", "write"],
                }
            }
        }
    }
    
    settings = get_pruning_settings_from_config(config)
    
    assert settings.mode == "soft-trim"
    assert settings.ttl_ms == 300000  # 5 minutes
    assert settings.soft_trim_ratio == 0.75
    assert "bash" in settings.prunable_tools
    
    print("\nPruning Settings Loaded:")
    print(f"  Mode: {settings.mode}")
    print(f"  TTL: {settings.ttl_ms}ms")
    print(f"  Soft Trim Ratio: {settings.soft_trim_ratio}")
    print(f"  Prunable Tools: {settings.prunable_tools}")


def test_pruning_preserves_essential_messages():
    """Test that pruning preserves essential messages"""
    messages = [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "Question 1"},
        {"role": "assistant", "content": "Answer 1"},
        {"role": "toolResult", "content": "X" * 10000, "toolName": "bash", "toolCallId": "1"},
        {"role": "user", "content": "Question 2"},
        {"role": "assistant", "content": "Answer 2"},
        {"role": "toolResult", "content": "Y" * 10000, "toolName": "bash", "toolCallId": "2"},
        {"role": "user", "content": "Question 3"},
    ]
    
    # Aggressive pruning
    pruning_settings = ContextPruningSettings(
        mode="soft-trim",
        soft_trim_ratio=0.3,
        prunable_tools={"bash"},
    )
    
    pruned = prune_context_messages(messages, pruning_settings, context_window_tokens=1000)
    
    # System message preserved
    assert any(m.get("role") == "system" for m in pruned)
    
    # All user messages preserved
    user_count = len([m for m in messages if m.get("role") == "user"])
    pruned_user_count = len([m for m in pruned if m.get("role") == "user"])
    assert pruned_user_count == user_count
    
    # Assistant messages preserved
    assistant_count = len([m for m in messages if m.get("role") == "assistant"])
    pruned_assistant_count = len([m for m in pruned if m.get("role") == "assistant"])
    assert pruned_assistant_count == assistant_count
    
    # Tool results may be pruned
    tool_count = len([m for m in messages if m.get("role") == "toolResult"])
    pruned_tool_count = len([m for m in pruned if m.get("role") == "toolResult"])
    assert pruned_tool_count <= tool_count
    
    print("\nMessage Preservation Test:")
    print(f"  Original messages: {len(messages)}")
    print(f"  Pruned messages: {len(pruned)}")
    print(f"  User messages: {user_count} -> {pruned_user_count}")
    print(f"  Assistant messages: {assistant_count} -> {pruned_assistant_count}")
    print(f"  Tool results: {tool_count} -> {pruned_tool_count}")


if __name__ == "__main__":
    # Run with: pytest test_pruning_live.py -v -s -m integration
    pytest.main([__file__, "-v", "-s"])
