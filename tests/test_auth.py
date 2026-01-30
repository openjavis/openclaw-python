"""
Tests for authentication module
"""

from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from openclaw.auth import APIKey, APIKeyManager, RateLimiter, RateLimitExceeded


class TestAPIKey:
    """Test APIKey model"""

    def test_valid_key(self):
        key = APIKey(key_id="test-id", key_hash="hash123", name="test-key")
        assert key.is_valid()

    def test_expired_key(self):
        key = APIKey(
            key_id="test-id",
            key_hash="hash123",
            name="test-key",
            expires_at=datetime.now(UTC) - timedelta(days=1),
        )
        assert not key.is_valid()

    def test_disabled_key(self):
        key = APIKey(key_id="test-id", key_hash="hash123", name="test-key", enabled=False)
        assert not key.is_valid()

    def test_permissions(self):
        key = APIKey(
            key_id="test-id", key_hash="hash123", name="test-key", permissions={"read", "write"}
        )
        assert key.has_permission("read")
        assert key.has_permission("write")
        assert not key.has_permission("admin")


class TestAPIKeyManager:
    """Test APIKeyManager class"""

    def test_create_key(self):
        manager = APIKeyManager()
        raw_key = manager.create_key("test-app")

        assert raw_key.startswith("clb_")
        assert len(manager.list_keys()) >= 1

    def test_validate_key(self):
        manager = APIKeyManager()
        raw_key = manager.create_key("test-app")

        api_key = manager.validate_key(raw_key)
        assert api_key is not None
        assert api_key.name == "test-app"

    def test_invalid_key(self):
        manager = APIKeyManager()

        api_key = manager.validate_key("invalid-key")
        assert api_key is None

    def test_revoke_key(self):
        manager = APIKeyManager()
        raw_key = manager.create_key("test-app")

        # Get key_id
        api_key = manager.validate_key(raw_key)
        key_id = api_key.key_id

        # Revoke
        manager.revoke_key(key_id)

        # Should no longer validate
        assert manager.validate_key(raw_key) is None

    def test_delete_key(self):
        manager = APIKeyManager()
        raw_key = manager.create_key("test-app")

        api_key = manager.validate_key(raw_key)
        key_id = api_key.key_id

        initial_count = len(manager.list_keys())
        manager.delete_key(key_id)

        assert len(manager.list_keys()) == initial_count - 1

    def test_cleanup_expired(self):
        manager = APIKeyManager()

        # Create expired key
        manager.create_key("test-app", expires_days=-1)

        cleaned = manager.cleanup_expired()
        assert cleaned >= 1


class TestRateLimiter:
    """Test RateLimiter class"""

    def test_rate_limit_allows_under_limit(self):
        limiter = RateLimiter(requests_per_minute=10)

        # Should allow first 10 requests
        for i in range(10):
            assert limiter.check(f"user-{i}") is True

    def test_rate_limit_blocks_over_limit(self):
        limiter = RateLimiter(requests_per_minute=5)

        identifier = "test-user"

        # First 5 should succeed
        for i in range(5):
            assert limiter.check(identifier) is True

        # 6th should fail
        assert limiter.check(identifier) is False

    def test_rate_limit_reset(self):
        limiter = RateLimiter(requests_per_minute=5)

        identifier = "test-user"

        # Use up limit
        for i in range(5):
            limiter.check(identifier)

        # Reset
        limiter.reset(identifier)

        # Should allow again
        assert limiter.check(identifier) is True

    def test_get_stats(self):
        limiter = RateLimiter(requests_per_minute=10)

        identifier = "test-user"
        limiter.check(identifier)
        limiter.check(identifier)

        stats = limiter.get_stats(identifier)
        assert stats["current_requests"] == 2
        assert stats["limit"] == 10
        assert stats["remaining"] == 8

    @pytest.mark.asyncio
    async def test_rate_limit_exception(self):
        limiter = RateLimiter(requests_per_minute=2)

        identifier = "test-user"

        # Use up limit
        limiter.check(identifier)
        limiter.check(identifier)

        # Create mock request
        from fastapi import Request

        mock_request = Mock(spec=Request)
        mock_request.headers = {"x-api-key": identifier}
        mock_request.client.host = "127.0.0.1"

        # Should raise RateLimitExceeded
        with pytest.raises(RateLimitExceeded):
            await limiter.check_request(mock_request)
