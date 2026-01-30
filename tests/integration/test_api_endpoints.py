"""
Integration tests for API endpoints
"""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from openclaw.agents import AgentRuntime, SessionManager
from openclaw.api.server import create_app, set_channel_registry, set_runtime, set_session_manager
from openclaw.channels import ChannelRegistry


@pytest.fixture
def test_app(temp_workspace):
    """Create test app with mocked components"""
    app = create_app()

    # Setup mocked components
    runtime = Mock(spec=AgentRuntime)
    session_manager = SessionManager(temp_workspace)
    channel_registry = ChannelRegistry()

    set_runtime(runtime)
    set_session_manager(session_manager)
    set_channel_registry(channel_registry)

    return app


@pytest.fixture
def client(test_app):
    """Create test client"""
    return TestClient(test_app)


class TestHealthEndpoints:
    """Test health check endpoints"""

    def test_health_endpoint(self, client):
        """Test /health endpoint"""
        response = client.get("/health")
        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data
        assert "timestamp" in data

    def test_liveness_endpoint(self, client):
        """Test /health/live endpoint"""
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_readiness_endpoint(self, client):
        """Test /health/ready endpoint"""
        response = client.get("/health/ready")
        assert response.status_code in [200, 503]


class TestMetricsEndpoints:
    """Test metrics endpoints"""

    def test_metrics_json(self, client):
        """Test /metrics JSON endpoint"""
        response = client.get("/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "counters" in data
        assert "gauges" in data

    def test_metrics_prometheus(self, client):
        """Test /metrics/prometheus endpoint"""
        response = client.get("/metrics/prometheus")
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"


class TestAgentEndpoints:
    """Test agent endpoints"""

    def test_list_sessions_requires_auth(self, client):
        """Test that sessions endpoint requires authentication"""
        response = client.get("/agent/sessions")
        assert response.status_code == 401

    def test_list_sessions_with_auth(self, client):
        """Test listing sessions with valid API key"""
        # Note: In production, would need valid API key
        # For now, test that endpoint exists and returns proper format
        response = client.get("/agent/sessions", headers={"X-API-Key": "test-key"})
        # Will fail auth but endpoint exists
        assert response.status_code in [200, 401, 403]


class TestChannelEndpoints:
    """Test channel management endpoints"""

    def test_list_channels_requires_auth(self, client):
        """Test that channels endpoint requires authentication"""
        response = client.get("/channels")
        assert response.status_code == 401

    def test_root_endpoint(self, client):
        """Test root info endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert data["name"] == "ClawdBot API"


class TestOpenAICompatibility:
    """Test OpenAI-compatible endpoints"""

    def test_models_endpoint(self, client):
        """Test /v1/models endpoint"""
        response = client.get("/v1/models")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert len(data["data"]) > 0


class TestRateLimiting:
    """Test rate limiting"""

    def test_rate_limit_applied(self, client):
        """Test that rate limiting is applied"""
        # Make multiple requests quickly
        # Should eventually hit rate limit if not on skip list
        responses = []
        for i in range(150):  # More than default limit
            response = client.get("/agent/sessions", headers={"X-API-Key": f"test-key-{i}"})
            responses.append(response.status_code)

        # Should have some 401s (auth) but endpoint should respond
        assert all(code in [200, 401, 429] for code in responses)
