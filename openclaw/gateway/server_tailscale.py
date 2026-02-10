"""Tailscale exposure for Gateway

Exposes Gateway over Tailscale network.
Matches TypeScript openclaw/src/gateway/server-tailscale.ts
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


async def start_gateway_tailscale_exposure(config: dict) -> dict | None:
    """
    Start Tailscale exposure
    
    Args:
        config: Gateway configuration
        
    Returns:
        Dict with Tailscale info or None
    """
    tailscale_config = config.get("tailscale", {})
    
    if not tailscale_config.get("enabled", False):
        logger.info("Tailscale exposure disabled")
        return None
    
    logger.info("Starting Tailscale exposure")
    
    # TODO: Configure Tailscale for Gateway exposure
    # This would use Tailscale SDK or CLI
    
    return {
        "enabled": True,
        "status": "active",
    }
