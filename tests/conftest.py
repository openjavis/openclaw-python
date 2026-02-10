"""Pytest configuration and fixtures"""

import pytest
import asyncio


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "unit: mark test as unit test")


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_config(tmp_path):
    """Create a temporary config file for testing"""
    config_file = tmp_path / "test_config.json"
    config_file.write_text('{"gateway": {"port": 18789}}')
    return config_file


@pytest.fixture
def mock_env(monkeypatch):
    """Mock environment variables"""
    test_env = {
        "GOOGLE_API_KEY": "test-key",
        "OPENCLAW_ENV": "test",
    }
    for key, value in test_env.items():
        monkeypatch.setenv(key, value)
    return test_env
