"""Delivery system for isolated agent results"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...channels.base import BaseChannel
    from ..types import CronDelivery, CronJob

logger = logging.getLogger(__name__)


class DeliveryTarget:
    """Resolved delivery target"""
    
    def __init__(self, channel: str, target_id: str):
        """
        Initialize delivery target
        
        Args:
            channel: Channel ID (telegram, discord, slack, etc.)
            target_id: Target user/chat ID
        """
        self.channel = channel
        self.target_id = target_id
    
    def __repr__(self) -> str:
        return f"DeliveryTarget(channel={self.channel}, target={self.target_id})"


async def resolve_delivery_target(
    job: CronJob,
    session_history: list[dict[str, Any]] | None = None,
) -> DeliveryTarget | None:
    """
    Resolve delivery target for job
    
    Args:
        job: Cron job
        session_history: Session message history
        
    Returns:
        Resolved delivery target or None
    """
    if not job.delivery:
        logger.debug("No delivery configuration")
        return None
    
    delivery = job.delivery
    
    # If explicit target provided, use it
    if delivery.target and delivery.channel != "last":
        logger.info(f"Using explicit delivery target: {delivery.channel}:{delivery.target}")
        return DeliveryTarget(
            channel=delivery.channel,
            target_id=delivery.target
        )
    
    # If channel is "last", resolve from session history
    if delivery.channel == "last":
        if not session_history:
            logger.warning("Cannot resolve 'last' channel: no session history")
            return None
        
        # Find last message with channel info
        for msg in reversed(session_history):
            if isinstance(msg, dict):
                metadata = msg.get("metadata", {})
                channel = metadata.get("channel")
                target_id = metadata.get("chat_id") or metadata.get("user_id")
                
                if channel and target_id:
                    logger.info(f"Resolved 'last' channel to: {channel}:{target_id}")
                    return DeliveryTarget(
                        channel=channel,
                        target_id=str(target_id)
                    )
        
        logger.warning("Cannot resolve 'last' channel: no channel info in history")
        return None
    
    # Channel specified but no target - cannot deliver
    logger.warning(f"Channel '{delivery.channel}' specified but no target")
    return None


async def deliver_result(
    job: CronJob,
    result: dict[str, Any],
    channel_registry: dict[str, BaseChannel],
    session_history: list[dict[str, Any]] | None = None,
) -> bool:
    """
    Deliver isolated agent result to channel
    
    Args:
        job: Cron job
        result: Execution result
        channel_registry: Registry of available channels
        session_history: Session history for resolving "last" channel
        
    Returns:
        True if delivery succeeded
    """
    if not job.delivery:
        logger.debug("No delivery configuration")
        return True  # No delivery needed = success
    
    # Check if agent already sent via messaging tool
    if result.get("self_sent", False):
        logger.info("Agent already sent message via messaging tool")
        return True
    
    # Resolve target
    target = await resolve_delivery_target(job, session_history)
    
    if not target:
        if job.delivery.best_effort:
            logger.warning("Could not resolve delivery target (best effort mode)")
            return True
        else:
            logger.error("Could not resolve delivery target")
            return False
    
    # Get channel
    channel = channel_registry.get(target.channel)
    
    if not channel:
        error_msg = f"Channel '{target.channel}' not found"
        if job.delivery.best_effort:
            logger.warning(f"{error_msg} (best effort mode)")
            return True
        else:
            logger.error(error_msg)
            return False
    
    # Check if channel is running
    if not channel.is_running():
        error_msg = f"Channel '{target.channel}' is not running"
        if job.delivery.best_effort:
            logger.warning(f"{error_msg} (best effort mode)")
            return True
        else:
            logger.error(error_msg)
            return False
    
    # Prepare message
    if not result.get("success"):
        # Delivery failed result
        error = result.get("error", "Unknown error")
        message = f"⚠️ Cron job '{job.name}' failed:\n\n{error}"
    else:
        # Delivery successful result
        summary = result.get("summary", "")
        if not summary:
            summary = result.get("full_response", "")
        
        if not summary:
            logger.warning("No content to deliver")
            return True
        
        message = f"🤖 **{job.name}**\n\n{summary}"
    
    # Deliver
    try:
        logger.info(f"Delivering to {target.channel}:{target.target_id}")
        
        await channel.send_text(target.target_id, message)
        
        logger.info("Delivery succeeded")
        return True
        
    except Exception as e:
        error_msg = f"Delivery failed: {e}"
        
        if job.delivery.best_effort:
            logger.warning(f"{error_msg} (best effort mode)", exc_info=True)
            return True
        else:
            logger.error(error_msg, exc_info=True)
            return False


def format_delivery_message(job: CronJob, result: dict[str, Any]) -> str:
    """
    Format delivery message
    
    Args:
        job: Cron job
        result: Execution result
        
    Returns:
        Formatted message
    """
    if not result.get("success"):
        error = result.get("error", "Unknown error")
        return f"⚠️ Cron job '{job.name}' failed:\n\n{error}"
    
    summary = result.get("summary", "")
    if not summary:
        summary = result.get("full_response", "No response")
    
    # Add emoji based on job type
    emoji = "🤖"
    if "reminder" in job.name.lower():
        emoji = "⏰"
    elif "alert" in job.name.lower():
        emoji = "🔔"
    elif "report" in job.name.lower():
        emoji = "📊"
    
    return f"{emoji} **{job.name}**\n\n{summary}"
