"""
Tests for SessionEntry data model
"""

import pytest
from openclaw.agents.session_entry import (
    SessionEntry,
    SessionOrigin,
    DeliveryContext,
    merge_session_entry,
)


def test_session_entry_creation():
    """Test creating a SessionEntry using camelCase field names."""
    entry = SessionEntry(
        sessionId="test-123",
        updatedAt=1000000,
    )

    assert entry.sessionId == "test-123"
    assert entry.updatedAt == 1000000
    assert entry.sessionFile is None
    assert entry.spawnedBy is None


def test_session_entry_with_all_fields():
    """Test SessionEntry with all fields populated."""
    origin = SessionOrigin(
        label="test",
        provider="anthropic",
        chatType="dm",
    )

    delivery = DeliveryContext(
        channel="telegram",
        to="user123",
    )

    entry = SessionEntry(
        sessionId="test-456",
        updatedAt=2000000,
        sessionFile="test-456.jsonl",
        spawnedBy="parent-session",
        thinkingLevel="high",
        label="Test Session",
        origin=origin,
        deliveryContext=delivery,
        inputTokens=100,
        outputTokens=200,
        totalTokens=300,
    )

    assert entry.sessionId == "test-456"
    assert entry.thinkingLevel == "high"
    assert entry.label == "Test Session"
    assert entry.origin.provider == "anthropic"
    assert entry.deliveryContext.channel == "telegram"
    assert entry.totalTokens == 300


def test_merge_session_entry_new():
    """Test merging into a new entry (existing=None)."""
    patch = {
        "sessionId": "new-123",
        "thinkingLevel": "medium",
        "label": "New Session",
    }

    result = merge_session_entry(None, patch)

    assert result.sessionId == "new-123"
    assert result.thinkingLevel == "medium"
    assert result.label == "New Session"
    assert result.updatedAt > 0


def test_merge_session_entry_new_snake_case():
    """merge_session_entry also accepts snake_case patch keys."""
    patch = {
        "session_id": "new-snake-123",
        "thinking_level": "medium",
        "label": "Snake Session",
    }

    result = merge_session_entry(None, patch)

    assert result.sessionId == "new-snake-123"
    assert result.thinkingLevel == "medium"
    assert result.label == "Snake Session"


def test_merge_session_entry_existing():
    """Test merging into existing entry."""
    existing = SessionEntry(
        sessionId="existing-123",
        updatedAt=1000000,
        thinkingLevel="low",
        label="Old Label",
    )

    patch = {
        "thinkingLevel": "high",
        "inputTokens": 50,
    }

    result = merge_session_entry(existing, patch)

    assert result.sessionId == "existing-123"
    assert result.thinkingLevel == "high"
    assert result.label == "Old Label"  # preserved
    assert result.inputTokens == 50
    assert result.updatedAt >= 1000000


def test_session_entry_model_dump():
    """Test converting SessionEntry to dict (uses camelCase keys by default)."""
    entry = SessionEntry(
        sessionId="dump-test",
        updatedAt=3000000,
        thinkingLevel="xhigh",
    )

    data = entry.model_dump(exclude_none=False)

    assert data["sessionId"] == "dump-test"
    assert data["updatedAt"] == 3000000
    assert data["thinkingLevel"] == "xhigh"
    assert "spawnedBy" in data


def test_session_origin_with_alias():
    """Test SessionOrigin with 'from' field alias."""
    origin = SessionOrigin(
        **{"from": "user123", "to": "bot456"}
    )

    assert origin.from_ == "user123"
    assert origin.to == "bot456"


def test_delivery_context():
    """Test DeliveryContext."""
    delivery = DeliveryContext(
        channel="discord",
        to="channel123",
        accountId="account456",
        threadId="thread789",
    )

    assert delivery.channel == "discord"
    assert delivery.to == "channel123"
    assert delivery.threadId == "thread789"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
