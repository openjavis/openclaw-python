"""
Tests for model failover functionality
"""

import pytest

from openclaw.agents.failover import FailoverReason, FallbackChain, FallbackError, FallbackManager


class TestFailoverReason:
    """Test FailoverReason enum"""

    def test_reason_values(self):
        """Test enum values"""
        assert FailoverReason.AUTH == "auth"
        assert FailoverReason.RATE_LIMIT == "rate_limit"
        assert FailoverReason.TIMEOUT == "timeout"


class TestFallbackError:
    """Test FallbackError exception"""

    def test_error_creation(self):
        """Test creating fallback error"""
        error = FallbackError(
            "Test error",
            reason=FailoverReason.RATE_LIMIT,
            provider="anthropic",
            model="claude-opus",
        )

        assert error.message == "Test error"
        assert error.reason == FailoverReason.RATE_LIMIT
        assert error.provider == "anthropic"
        assert error.model == "claude-opus"

    def test_error_to_dict(self):
        """Test error serialization"""
        error = FallbackError("Test", reason=FailoverReason.AUTH, provider="openai")

        data = error.to_dict()

        assert data["message"] == "Test"
        assert data["reason"] == "auth"
        assert data["provider"] == "openai"


class TestFallbackChain:
    """Test FallbackChain class"""

    def test_chain_creation(self):
        """Test creating a fallback chain"""
        chain = FallbackChain(
            primary="anthropic/claude-opus", fallbacks=["anthropic/claude-sonnet", "openai/gpt-4"]
        )

        assert chain.primary == "anthropic/claude-opus"
        assert len(chain.fallbacks) == 2
        assert len(chain) == 3

    def test_get_models(self):
        """Test getting all models in chain"""
        chain = FallbackChain(primary="model-a", fallbacks=["model-b", "model-c"])

        models = chain.get_models()

        assert models == ["model-a", "model-b", "model-c"]


class TestFallbackManager:
    """Test FallbackManager class"""

    def test_manager_creation(self):
        """Test creating manager"""
        chain = FallbackChain(primary="model-a", fallbacks=["model-b"])
        manager = FallbackManager(chain)

        assert manager.chain == chain
        assert manager.current_index == 0

    def test_get_current_model(self):
        """Test getting current model"""
        chain = FallbackChain(primary="model-a", fallbacks=["model-b"])
        manager = FallbackManager(chain)

        assert manager.get_current_model() == "model-a"

    def test_get_next_model(self):
        """Test getting next model"""
        chain = FallbackChain(primary="model-a", fallbacks=["model-b", "model-c"])
        manager = FallbackManager(chain)

        assert manager.get_next_model() == "model-b"
        assert manager.get_next_model() == "model-c"
        assert manager.get_next_model() is None  # Chain exhausted

    def test_should_failover_auth_error(self):
        """Test failover decision for auth error"""
        manager = FallbackManager()

        error = Exception("authentication failed")
        should_fail, reason = manager.should_failover(error)

        assert should_fail
        assert reason == FailoverReason.AUTH

    def test_should_failover_rate_limit(self):
        """Test failover decision for rate limit"""
        manager = FallbackManager()

        error = Exception("rate limit exceeded")
        should_fail, reason = manager.should_failover(error)

        assert should_fail
        assert reason == FailoverReason.RATE_LIMIT

    def test_should_not_failover_unknown(self):
        """Test no failover for unknown errors"""
        manager = FallbackManager()

        error = Exception("some random error")
        should_fail, reason = manager.should_failover(error)

        # Unknown errors don't trigger failover by default
        assert not should_fail

    def test_record_attempt(self):
        """Test recording attempts"""
        chain = FallbackChain(primary="model-a", fallbacks=[])
        manager = FallbackManager(chain)

        manager.record_attempt("model-a")
        manager.record_attempt("model-a")

        assert manager.attempts_per_model["model-a"] == 2

    def test_reset(self):
        """Test resetting manager"""
        chain = FallbackChain(primary="model-a", fallbacks=["model-b"])
        manager = FallbackManager(chain)

        manager.get_next_model()
        manager.record_attempt("model-a")

        manager.reset()

        assert manager.current_index == 0
        assert len(manager.attempts_per_model) == 0
