"""Tests for diagnostic event system (matches TypeScript diagnostic-events.test.ts)"""

import asyncio
import pytest
from openclaw.infra.diagnostic_events import (
    log_webhook_received,
    log_webhook_processed,
    log_webhook_error,
    log_message_queued,
    log_message_processed,
    log_session_state_change,
    log_session_stuck,
    log_run_attempt,
    get_diagnostic_stats,
    on_diagnostic_event,
)


def test_webhook_logging():
    """Test webhook event logging"""
    initial_stats = get_diagnostic_stats()
    initial_count = initial_stats.webhooks_received
    
    log_webhook_received("telegram", {"user_id": "123"})
    
    stats = get_diagnostic_stats()
    assert stats.webhooks_received == initial_count + 1


def test_webhook_processed():
    """Test webhook processed logging"""
    initial_stats = get_diagnostic_stats()
    initial_count = initial_stats.webhooks_processed
    
    log_webhook_processed("telegram", 150.5)
    
    stats = get_diagnostic_stats()
    assert stats.webhooks_processed == initial_count + 1


def test_webhook_error():
    """Test webhook error logging"""
    initial_stats = get_diagnostic_stats()
    initial_count = initial_stats.webhooks_errors
    
    log_webhook_error("telegram", "Connection timeout")
    
    stats = get_diagnostic_stats()
    assert stats.webhooks_errors == initial_count + 1


def test_message_queued():
    """Test message queued logging"""
    initial_stats = get_diagnostic_stats()
    initial_count = initial_stats.messages_queued
    
    log_message_queued("telegram:123:456")
    
    stats = get_diagnostic_stats()
    assert stats.messages_queued == initial_count + 1


def test_message_processed():
    """Test message processed logging"""
    initial_stats = get_diagnostic_stats()
    initial_count = initial_stats.messages_processed
    
    log_message_processed("telegram:123:456", 2500.0)
    
    stats = get_diagnostic_stats()
    assert stats.messages_processed == initial_count + 1


def test_session_state_change():
    """Test session state change logging"""
    initial_stats = get_diagnostic_stats()
    
    log_session_state_change("session-1", "idle", "processing")
    
    stats = get_diagnostic_stats()
    assert stats.sessions_processing > initial_stats.sessions_processing


def test_session_stuck():
    """Test stuck session logging"""
    initial_stats = get_diagnostic_stats()
    initial_count = initial_stats.stuck_sessions
    
    log_session_stuck("session-1", 150.0)
    
    stats = get_diagnostic_stats()
    assert stats.stuck_sessions == initial_count + 1


def test_run_attempt():
    """Test run attempt logging"""
    initial_stats = get_diagnostic_stats()
    
    log_run_attempt("session-1", "claude-opus-4")
    
    stats = get_diagnostic_stats()
    assert stats.active_runs > initial_stats.active_runs


def test_event_listener():
    """Test diagnostic event listener"""
    events = []
    
    def listener(event_type, data):
        events.append((event_type, data))
    
    unsubscribe = on_diagnostic_event(listener)
    
    log_webhook_received("test", {})
    
    # Give event loop time to process
    import time
    time.sleep(0.01)
    
    assert len(events) > 0
    assert events[-1][0] == "webhook.received"
    
    unsubscribe()


def test_diagnostic_stats_uptime():
    """Test diagnostic stats uptime tracking"""
    stats = get_diagnostic_stats()
    
    assert stats.uptime_seconds >= 0
    assert stats.uptime_seconds < 3600  # Less than 1 hour for test


def test_event_sequencing():
    """Test event sequencing (matches TypeScript test)"""
    events = []
    
    def listener(event_type, data):
        events.append(event_type)
    
    unsubscribe = on_diagnostic_event(listener)
    
    # Log events in sequence
    log_message_queued("session-1")
    log_session_state_change("session-1", "idle", "processing")
    log_run_attempt("session-1", "claude")
    log_message_processed("session-1", 1000.0)
    log_session_state_change("session-1", "processing", "idle")
    
    import time
    time.sleep(0.01)
    
    # Verify events were emitted
    assert "message.queued" in events
    assert "session.state_change" in events
    assert "run.attempt" in events
    assert "message.processed" in events
    
    unsubscribe()
