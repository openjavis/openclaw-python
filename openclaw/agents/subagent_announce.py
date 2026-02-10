"""Subagent completion announcement

Notifies requester when subagent completes.
Matches TypeScript openclaw/src/agents/subagent-announce.ts
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def run_subagent_announce_flow(
    child_session_key: str,
    child_run_id: str,
    requester_session_key: str,
    requester_origin: dict[str, Any] | None,
    requester_display_key: str,
    task: str,
    timeout_ms: int,
    cleanup: str,
    wait_for_completion: bool = True,
    started_at: int | None = None,
    ended_at: int | None = None,
    label: str | None = None,
    outcome: dict[str, Any] | None = None,
) -> bool:
    """
    Run subagent completion announcement flow
    
    Notifies the requester that the subagent has completed,
    sending results back to the original conversation.
    
    Args:
        child_session_key: Child agent session key
        child_run_id: Run ID
        requester_session_key: Requester session key
        requester_origin: Origin context
        requester_display_key: Display key
        task: Task description
        timeout_ms: Timeout
        cleanup: Cleanup strategy
        wait_for_completion: Whether to wait
        started_at: Start timestamp
        ended_at: End timestamp
        label: Optional label
        outcome: Outcome data
        
    Returns:
        True if announcement succeeded
    """
    logger.info(
        f"Announcing subagent completion: {child_run_id} "
        f"to {requester_display_key}"
    )
    
    try:
        # TODO: Implement actual announcement via Gateway RPC
        # This would send a message back to the requester's session
        # containing the subagent's results
        
        # For now, just log
        logger.info(
            f"Subagent {child_run_id} completed task: {task[:50]}... "
            f"(outcome: {outcome})"
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to announce subagent completion: {e}")
        return False
