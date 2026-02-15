"""Unit tests for session key utilities"""
import pytest
from openclaw.sessions.session_key_utils import (
    build_session_key,
    extract_agent_id,
    extract_session_id,
    is_valid_session_key,
    parse_agent_session_key,
)


def test_parse_valid_key():
    parsed = parse_agent_session_key("agent1:session-abc")
    assert parsed is not None
    assert parsed.agent_id == "agent1"
    assert parsed.session_id == "session-abc"
    assert parsed.full_key == "agent1:session-abc"


def test_parse_invalid_key():
    assert parse_agent_session_key("") is None
    assert parse_agent_session_key("nocolon") is None
    assert parse_agent_session_key(":session") is None
    assert parse_agent_session_key("agent:") is None


def test_build_session_key():
    key = build_session_key("agent1", "sess1")
    assert key == "agent1:sess1"


def test_extract_ids():
    assert extract_agent_id("a:b") == "a"
    assert extract_session_id("a:b") == "b"
    assert extract_agent_id("invalid") is None


def test_is_valid_session_key():
    assert is_valid_session_key("agent:session") is True
    assert is_valid_session_key("") is False
