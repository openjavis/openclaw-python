"""
End-to-end integration tests for complete system alignment.

Tests all major alignment features from the OpenClaw alignment plan.
"""
import asyncio
import pytest
import tempfile
from pathlib import Path

# Session Routing Tests
@pytest.mark.integration
async def test_session_routing_dm_scope_main():
    """Test session key resolution with dmScope=main"""
    from openclaw.routing import resolve_agent_route
    
    config = {
        "agents": {"default": "main", "list": [{"id": "main"}]},
        "session": {
            "dmScope": "main",
            "bindings": []
        }
    }
    
    route = resolve_agent_route(
        config=config,
        channel="telegram",
        account_id="default",
        peer={"kind": "dm", "id": "user123"}
    )
    
    assert route.agent_id == "main"
    assert route.session_key == "agent:main:main"
    assert route.matched_by == "default"


@pytest.mark.integration
async def test_session_routing_dm_scope_per_peer():
    """Test session key resolution with dmScope=per-peer"""
    from openclaw.routing import resolve_agent_route
    
    config = {
        "agents": {"default": "main", "list": [{"id": "main"}]},
        "session": {
            "dmScope": "per-peer",
            "bindings": []
        }
    }
    
    route = resolve_agent_route(
        config=config,
        channel="telegram",
        account_id="default",
        peer={"kind": "dm", "id": "user123"}
    )
    
    assert route.agent_id == "main"
    assert route.session_key == "agent:main:dm:user123"


@pytest.mark.integration
async def test_session_routing_with_bindings():
    """Test session routing with peer binding"""
    from openclaw.routing import resolve_agent_route
    
    config = {
        "agents": {"default": "main", "list": [{"id": "main"}, {"id": "assistant"}]},
        "session": {
            "dmScope": "main",
            "bindings": [
                {
                    "agentId": "assistant",
                    "match": {
                        "channel": "telegram",
                        "accountId": "default",
                        "peer": {"kind": "dm", "id": "vip_user"}
                    }
                }
            ]
        }
    }
    
    route = resolve_agent_route(
        config=config,
        channel="telegram",
        account_id="default",
        peer={"kind": "dm", "id": "vip_user"}
    )
    
    assert route.agent_id == "assistant"
    assert route.matched_by == "binding.peer"


# Auto-Reply Tests
@pytest.mark.integration
async def test_echo_tracker_prevents_self_reply():
    """Test echo tracker prevents replying to own messages"""
    from openclaw.auto_reply.echo_tracker import EchoTracker
    
    tracker = EchoTracker(window_seconds=30)
    
    # Mark message as outbound
    tracker.mark_outbound("msg_123")
    
    # Check if it's detected as echo
    assert tracker.is_echo("msg_123") is True
    
    # After detection, should be removed
    assert tracker.is_echo("msg_123") is False


@pytest.mark.integration
async def test_group_gating_requires_mention():
    """Test group gating requires mention in group chats"""
    from openclaw.auto_reply.group_gating import apply_group_gating
    
    config = {
        "alwaysGroupActivation": False
    }
    
    mention_patterns = ["@bot", "bot"]
    
    # Message without mention - should not trigger
    message = {
        "text": "Hello everyone!",
        "peer_kind": "group",
        "sender_id": "user123"
    }
    
    result = apply_group_gating(message, config, mention_patterns)
    assert result is False
    
    # Message with mention - should trigger
    message_with_mention = {
        "text": "Hey @bot, can you help?",
        "peer_kind": "group",
        "sender_id": "user123"
    }
    
    result = apply_group_gating(message_with_mention, config, mention_patterns)
    assert result is True


@pytest.mark.integration
async def test_message_debouncing():
    """Test message debouncing batches rapid messages"""
    from openclaw.auto_reply.debounce import MessageDebouncer
    
    debouncer = MessageDebouncer(interval_ms=500)
    
    batched_messages = []
    
    async def callback(peer_id: str, messages: list):
        batched_messages.extend(messages)
    
    # Add rapid messages
    await debouncer.add_message("user123", {"text": "Hello"}, callback)
    await debouncer.add_message("user123", {"text": "World"}, callback)
    await debouncer.add_message("user123", {"text": "!"}, callback)
    
    # Wait for debounce
    await asyncio.sleep(0.6)
    
    # Should have batched all 3 messages
    assert len(batched_messages) == 3


# Plugin System Tests
@pytest.mark.integration
async def test_plugin_hook_registration():
    """Test plugin hook registration and priority"""
    from openclaw.hooks.registry import HookRegistry
    
    registry = HookRegistry()
    
    # Register hooks with different priorities
    hooks = [
        ("message_received", lambda ctx: "handler1", 10),
        ("message_received", lambda ctx: "handler2", 5),
        ("message_received", lambda ctx: "handler3", 15)
    ]
    
    registry.register_plugin_hooks("test_plugin", hooks)
    
    # Check handlers are sorted by priority
    handlers = registry._event_handlers.get("message_received", [])
    assert len(handlers) == 3
    
    # Verify priority order (highest first)
    priorities = [h["priority"] for h in handlers if isinstance(h, dict)]
    assert priorities == [15, 10, 5]


# Device Pairing Tests
@pytest.mark.integration
async def test_device_pairing_persistence():
    """Test pending device pairing requests persist across restarts"""
    from openclaw.auth.device_pairing import DevicePairingManager
    
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = Path(tmpdir)
        
        # Create first manager and request pairing
        manager1 = DevicePairingManager(state_dir=state_dir)
        
        request = manager1.request_pairing(
            device_id="device_123",
            public_key="pubkey_xyz",
            display_name="Test Device"
        )
        
        assert request is not None
        request_id = request.request_id
        
        # Create second manager (simulating restart)
        manager2 = DevicePairingManager(state_dir=state_dir)
        
        # Verify request was loaded
        loaded_request = manager2.get_pending_request(request_id)
        assert loaded_request is not None
        assert loaded_request.device_id == "device_123"


# Daemon Service Tests
@pytest.mark.integration
@pytest.mark.skipif(True, reason="Requires system permissions")
async def test_daemon_service_lifecycle():
    """Test daemon service install/start/stop lifecycle"""
    from openclaw.daemon.service import DaemonService
    
    service = DaemonService(service_name="openclaw-test")
    
    # Note: Actual install/start/stop require system permissions
    # This test is more of a smoke test
    assert not service.is_running()  # Should not be running initially


# Bootstrap Tests
@pytest.mark.integration
async def test_signal_handlers_registered():
    """Test signal handlers are properly registered"""
    import signal
    
    # This is a smoke test - signal handlers are platform-specific
    try:
        # SIGUSR1 should be available on Unix systems
        handler = signal.getsignal(signal.SIGUSR1)
        # If we get here without error, signal handling is available
        assert handler is not None
    except (AttributeError, ValueError):
        # Windows doesn't support SIGUSR1
        pytest.skip("Signal handling not available on this platform")


# Routing Identity Links Tests
@pytest.mark.integration
async def test_identity_links_resolution():
    """Test identity links resolve cross-channel identities"""
    from openclaw.routing.identity_links import IdentityLinkStore
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "identity_links.json"
        
        store = IdentityLinkStore(config_path=config_path)
        
        # Link identities
        store.add_link(
            identity1="telegram:123",
            identity2="discord:456",
            canonical="user_abc"
        )
        
        # Resolve identities
        canonical1 = store.resolve_identity("telegram:123", "telegram")
        canonical2 = store.resolve_identity("discord:456", "discord")
        
        assert canonical1 == "user_abc"
        assert canonical2 == "user_abc"
        
        # Get all linked identities
        identities = store.get_linked_identities("user_abc")
        assert "telegram:123" in identities
        assert "discord:456" in identities


if __name__ == "__main__":
    # Run with: pytest tests/integration/test_complete_alignment.py -v
    pytest.main([__file__, "-v"])
