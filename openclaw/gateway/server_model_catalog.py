"""Model catalog loading

Loads available LLM models from configuration.
Matches TypeScript openclaw/src/gateway/server-model-catalog.ts
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def load_gateway_model_catalog(config: dict) -> dict[str, Any]:
    """
    Load model catalog
    
    Args:
        config: Gateway configuration
        
    Returns:
        Model catalog dict
    """
    logger.info("Loading model catalog")
    
    # Extract model configurations from config
    models = config.get("models", {})
    providers = config.get("providers", {})
    
    catalog = {
        "models": models,
        "providers": providers,
        "default_model": config.get("agent", {}).get("defaultModel"),
        "default_provider": config.get("agent", {}).get("defaultProvider"),
    }
    
    logger.info(f"Loaded catalog with {len(models)} models")
    
    return catalog
