"""
Performance tests for critical paths.

Benchmarks throughput, latency, and scalability of key components.
"""
import asyncio
import time
import pytest


@pytest.mark.performance
async def test_concurrent_sessions():
    """Test handling 100 concurrent sessions"""
    from openclaw.agents.session import SessionManager
    
    session_manager = SessionManager(agent_id="main")
    
    start_time = time.time()
    
    # Create 100 concurrent sessions
    sessions = []
    for i in range(100):
        session = session_manager.get_or_create_session(
            session_key=f"agent:main:test:{i}",
            channel="test",
            peer_kind="dm",
            peer_id=f"user_{i}"
        )
        sessions.append(session)
    
    duration = time.time() - start_time
    
    # Should create 100 sessions quickly
    assert len(sessions) == 100
    assert duration < 1.0  # Less than 1 second
    
    print(f"\n✓ Created 100 sessions in {duration:.3f}s ({100/duration:.1f} sessions/sec)")


@pytest.mark.performance
async def test_session_routing_performance():
    """Test session routing performance"""
    from openclaw.routing import resolve_agent_route
    
    config = {
        "agents": {"default": "main", "list": [{"id": "main"}, {"id": "assistant"}]},
        "session": {
            "dmScope": "per-peer",
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
    
    start_time = time.time()
    iterations = 1000
    
    # Perform 1000 route resolutions
    for i in range(iterations):
        route = resolve_agent_route(
            config=config,
            channel="telegram",
            account_id="default",
            peer={"kind": "dm", "id": f"user_{i}"}
        )
    
    duration = time.time() - start_time
    throughput = iterations / duration
    
    # Should handle > 10k routes/sec
    assert throughput > 10000
    
    print(f"\n✓ Resolved {iterations} routes in {duration:.3f}s ({throughput:.1f} routes/sec)")


@pytest.mark.performance
async def test_message_debouncing_throughput():
    """Test message debouncing throughput"""
    from openclaw.auto_reply.debounce import MessageDebouncer
    
    debouncer = MessageDebouncer(interval_ms=100)
    
    processed_count = 0
    
    async def callback(peer_id: str, messages: list):
        nonlocal processed_count
        processed_count += len(messages)
    
    start_time = time.time()
    iterations = 1000
    
    # Add 1000 messages rapidly
    for i in range(iterations):
        await debouncer.add_message(
            peer_id=f"user_{i % 10}",  # 10 different users
            message={"text": f"Message {i}"},
            callback=callback
        )
    
    # Wait for all to process
    await asyncio.sleep(0.5)
    
    duration = time.time() - start_time
    
    # All messages should be processed
    assert processed_count == iterations
    
    print(f"\n✓ Processed {iterations} messages in {duration:.3f}s ({iterations/duration:.1f} msg/sec)")


@pytest.mark.performance
async def test_event_broadcast_latency():
    """Test event broadcast latency"""
    import asyncio
    from openclaw.gateway.protocol.events import EventFrame
    
    # Simulate event broadcasting
    event_count = 1000
    events = []
    
    start_time = time.time()
    
    for i in range(event_count):
        event = EventFrame(
            event="test.event",
            payload={"index": i},
            seq=i
        )
        events.append(event)
    
    duration = time.time() - start_time
    throughput = event_count / duration
    
    # Should create > 100k events/sec
    assert throughput > 100000
    
    print(f"\n✓ Created {event_count} events in {duration:.3f}s ({throughput:.1f} events/sec)")


@pytest.mark.performance
async def test_hook_dispatch_performance():
    """Test hook dispatch performance"""
    from openclaw.hooks.registry import HookRegistry
    
    registry = HookRegistry()
    
    call_count = 0
    
    async def handler(context):
        nonlocal call_count
        call_count += 1
    
    # Register 10 handlers
    for i in range(10):
        registry.register_hook(["test.event"], handler)
    
    start_time = time.time()
    iterations = 100
    
    # Dispatch event 100 times
    for i in range(iterations):
        await registry.dispatch_event("test.event", {"index": i})
    
    duration = time.time() - start_time
    
    # All handlers should be called
    assert call_count == iterations * 10
    
    print(f"\n✓ Dispatched {iterations} events to 10 handlers in {duration:.3f}s ({iterations/duration:.1f} dispatches/sec)")


@pytest.mark.performance
async def test_identity_link_resolution_performance():
    """Test identity link resolution performance"""
    import tempfile
    from pathlib import Path
    from openclaw.routing.identity_links import IdentityLinkStore
    
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "identity_links.json"
        store = IdentityLinkStore(config_path=config_path)
        
        # Create 100 identity links
        for i in range(100):
            store.add_link(
                identity1=f"telegram:{i}",
                identity2=f"discord:{i}",
                canonical=f"user_{i}"
            )
        
        start_time = time.time()
        iterations = 1000
        
        # Resolve 1000 identities
        for i in range(iterations):
            canonical = store.resolve_identity(f"telegram:{i % 100}", "telegram")
            assert canonical is not None
        
        duration = time.time() - start_time
        throughput = iterations / duration
        
        # Should handle > 10k resolutions/sec
        assert throughput > 10000
        
        print(f"\n✓ Resolved {iterations} identities in {duration:.3f}s ({throughput:.1f} resolutions/sec)")


@pytest.mark.performance
async def test_plugin_hook_registration_performance():
    """Test plugin hook registration performance"""
    from openclaw.hooks.registry import HookRegistry
    
    registry = HookRegistry()
    
    async def dummy_handler(ctx):
        pass
    
    start_time = time.time()
    
    # Register 100 plugins with 10 hooks each
    for plugin_id in range(100):
        hooks = [
            (f"event_{i}", dummy_handler, i)
            for i in range(10)
        ]
        registry.register_plugin_hooks(f"plugin_{plugin_id}", hooks)
    
    duration = time.time() - start_time
    
    # Should register 1000 hooks quickly
    total_hooks = 100 * 10
    assert duration < 1.0
    
    print(f"\n✓ Registered {total_hooks} hooks in {duration:.3f}s ({total_hooks/duration:.1f} hooks/sec)")


if __name__ == "__main__":
    # Run with: pytest tests/performance/test_throughput.py -v -s
    pytest.main([__file__, "-v", "-s", "-m", "performance"])
