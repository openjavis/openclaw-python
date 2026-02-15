"""
Tests for event scope guard filtering.

Validates that scope guards correctly filter events based on client permissions.
"""
import pytest

from openclaw.gateway.protocol.scope_guards import (
    EVENT_SCOPE_GUARDS,
    event_passes_scope_guard,
    get_required_scopes,
)


def test_operator_read_scope():
    """Test operator.read scope allows read events"""
    scopes = {"operator.read"}
    
    assert event_passes_scope_guard("agent", scopes) is True
    assert event_passes_scope_guard("chat", scopes) is True
    assert event_passes_scope_guard("cron", scopes) is True
    assert event_passes_scope_guard("presence", scopes) is True


def test_operator_admin_scope():
    """Test operator.admin scope allows admin events"""
    scopes = {"operator.admin"}
    
    assert event_passes_scope_guard("node.pair.requested", scopes) is True
    assert event_passes_scope_guard("node.pair.resolved", scopes) is True
    assert event_passes_scope_guard("device.pair.requested", scopes) is True


def test_operator_approvals_scope():
    """Test operator.approvals scope allows approval events"""
    scopes = {"operator.approvals"}
    
    assert event_passes_scope_guard("exec.approval.requested", scopes) is True
    assert event_passes_scope_guard("exec.approval.resolved", scopes) is True


def test_empty_scopes():
    """Test empty scopes only pass unguarded events"""
    scopes = set()
    
    # Unguarded events should pass
    assert event_passes_scope_guard("tick", scopes) is True
    assert event_passes_scope_guard("shutdown", scopes) is True
    assert event_passes_scope_guard("connect.challenge", scopes) is True
    
    # Guarded events should fail
    assert event_passes_scope_guard("agent", scopes) is False
    assert event_passes_scope_guard("node.pair.requested", scopes) is False


def test_multiple_scopes():
    """Test client with multiple scopes"""
    scopes = {"operator.read", "operator.admin"}
    
    # Should pass both read and admin events
    assert event_passes_scope_guard("agent", scopes) is True
    assert event_passes_scope_guard("node.pair.requested", scopes) is True


def test_insufficient_scopes():
    """Test client with insufficient scopes"""
    scopes = {"operator.read"}
    
    # Should not pass admin events
    assert event_passes_scope_guard("node.pair.requested", scopes) is False
    assert event_passes_scope_guard("exec.approval.requested", scopes) is False


def test_get_required_scopes():
    """Test getting required scopes for events"""
    # Guarded events
    agent_scopes = get_required_scopes("agent")
    assert agent_scopes == {"operator.read"}
    
    admin_scopes = get_required_scopes("node.pair.requested")
    assert admin_scopes == {"operator.admin"}
    
    # Unguarded events
    tick_scopes = get_required_scopes("tick")
    assert tick_scopes is None


def test_all_guard_entries_valid():
    """Test all scope guard entries are properly formatted"""
    for event, scopes in EVENT_SCOPE_GUARDS.items():
        assert isinstance(event, str)
        assert isinstance(scopes, set)
        assert len(scopes) > 0
        
        # Verify all scopes follow pattern
        for scope in scopes:
            assert "." in scope  # Should be like "operator.read"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
