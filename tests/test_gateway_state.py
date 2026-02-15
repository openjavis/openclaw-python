"""
Unit tests for Gateway state management - aligned with openclaw-ts

Tests chatRunState, agentRunSeq, and dedupe managers.
"""
import asyncio
import time
import pytest

from openclaw.gateway.chat_run_state import (
    ChatRunRegistry,
    ChatRunEntry,
    ChatRunState,
    should_send_delta,
    mark_delta_sent,
    append_to_buffer,
)
from openclaw.gateway.agent_run_seq import AgentRunSeqTracker
from openclaw.gateway.dedupe import DedupeManager, DedupeEntry


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
