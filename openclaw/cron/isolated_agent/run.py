"""Isolated agent execution for cron jobs"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ...agents.agent import Agent
from ...agents.providers import LLMProvider
from ...agents.tools.base import AgentTool
from .session import resolve_isolated_session

if TYPE_CHECKING:
    from ..types import AgentTurnPayload, CronJob

logger = logging.getLogger(__name__)


async def run_isolated_agent_turn(
    job: CronJob,
    provider: LLMProvider,
    tools: list[AgentTool],
    sessions_dir: Path,
    system_prompt: str | None = None,
) -> dict[str, Any]:
    """
    Run full isolated agent turn for cron job
    
    This function:
    1. Creates or loads session for the job
    2. Executes agent prompt
    3. Extracts summary from response
    4. Returns result for delivery
    
    Args:
        job: Cron job
        provider: LLM provider
        tools: Available tools
        sessions_dir: Sessions directory
        system_prompt: Optional system prompt
        
    Returns:
        Result dictionary with:
        - summary: Response summary
        - full_response: Full agent response
        - session_key: Session key used
    """
    # Validate payload
    from ..types import AgentTurnPayload
    
    if not isinstance(job.payload, AgentTurnPayload):
        raise ValueError(f"Job payload must be agentTurn, got {type(job.payload)}")
    
    payload: AgentTurnPayload = job.payload
    
    # Resolve session
    session = resolve_isolated_session(
        sessions_dir=sessions_dir,
        job_id=job.id,
        agent_id=job.agent_id
    )
    
    logger.info(f"Running isolated agent turn for job '{job.name}' in session {session.session_key}")
    
    try:
        # Determine model
        model = payload.model or "google/gemini-3-pro-preview"
        
        # Create agent
        agent = Agent(
            provider=provider,
            tools=tools,
            model=model,
            system_prompt=system_prompt
        )
        
        # Execute agent prompt
        logger.info(f"Executing prompt: {payload.prompt[:100]}...")
        
        messages = await agent.prompt(payload.prompt)
        
        # Extract response
        full_response = ""
        if messages:
            # Get last assistant message
            for msg in reversed(messages):
                if msg.role == "assistant":
                    full_response = msg.content
                    break
        
        # Extract summary (first paragraph or first 200 chars)
        summary = extract_summary(full_response)
        
        # Update session metadata
        session.update_metadata(
            model=model,
            token_count=len(full_response.split()),  # Rough estimate
        )
        
        logger.info(f"Isolated agent turn completed. Summary: {summary[:100]}...")
        
        return {
            "success": True,
            "summary": summary,
            "full_response": full_response,
            "session_key": session.session_key,
            "model": model,
        }
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error in isolated agent turn: {error_msg}", exc_info=True)
        
        return {
            "success": False,
            "error": error_msg,
            "session_key": session.session_key,
        }


def extract_summary(text: str, max_length: int = 200) -> str:
    """
    Extract summary from text
    
    Takes the first paragraph or first max_length characters.
    
    Args:
        text: Text to summarize
        max_length: Maximum summary length
        
    Returns:
        Summary string
    """
    if not text:
        return ""
    
    # Split into paragraphs
    paragraphs = text.split("\n\n")
    
    if paragraphs:
        first_para = paragraphs[0].strip()
        
        # If first paragraph is short enough, use it
        if len(first_para) <= max_length:
            return first_para
        
        # Otherwise truncate
        return first_para[:max_length].rsplit(" ", 1)[0] + "..."
    
    # Fallback: truncate text
    if len(text) <= max_length:
        return text
    
    return text[:max_length].rsplit(" ", 1)[0] + "..."


def detect_self_sent_via_messaging(messages: list[Any]) -> bool:
    """
    Check if agent already sent message via messaging tool
    
    This prevents duplicate delivery when agent uses a messaging tool
    to send its own response.
    
    Args:
        messages: Agent messages
        
    Returns:
        True if agent sent via messaging tool
    """
    # Check for tool calls to messaging/channel tools
    messaging_tools = [
        "send_telegram_message",
        "send_discord_message",
        "send_slack_message",
        "send_message",
        "channel_send",
    ]
    
    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tool_call in msg.tool_calls:
                tool_name = tool_call.get("name", "")
                if any(mt in tool_name.lower() for mt in messaging_tools):
                    logger.info("Agent sent message via messaging tool, skipping delivery")
                    return True
    
    return False


async def post_summary_to_main_session(
    job: CronJob,
    result: dict[str, Any],
    main_session_callback: Any,
) -> None:
    """
    Post summary to main session
    
    Args:
        job: Cron job
        result: Execution result
        main_session_callback: Callback to post to main session
    """
    if not result.get("success"):
        logger.warning("Not posting failed result to main session")
        return
    
    summary = result.get("summary", "")
    
    if not summary:
        logger.warning("No summary to post to main session")
        return
    
    # Format message
    message = f"🤖 Cron job '{job.name}' completed:\n\n{summary}"
    
    # Post to main session
    try:
        if main_session_callback:
            await main_session_callback(message)
            logger.info("Posted summary to main session")
    except Exception as e:
        logger.error(f"Error posting to main session: {e}", exc_info=True)
