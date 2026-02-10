"""Skills environment overrides (matches TypeScript agents/skills/env-overrides.ts)"""

import os
import logging
from typing import Any

logger = logging.getLogger(__name__)


def resolve_skill_env_overrides(
    skill_metadata: dict[str, Any],
) -> dict[str, str]:
    """
    Resolve environment variable overrides for a skill.
    
    Skills can specify required env vars and defaults in their metadata:
    ```yaml
    env:
      API_KEY: ${MY_API_KEY}
      BASE_URL: https://api.example.com
    ```
    
    Args:
        skill_metadata: Skill metadata dict (from SKILL.md frontmatter)
    
    Returns:
        Dict of environment variable overrides
    """
    env_config = skill_metadata.get("env", {})
    
    if not env_config:
        return {}
    
    overrides = {}
    
    for key, value in env_config.items():
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            # Environment variable reference
            env_var = value[2:-1]
            env_value = os.environ.get(env_var)
            if env_value:
                overrides[key] = env_value
            else:
                logger.debug(f"Skill env var not set: {env_var}")
        else:
            # Literal value
            overrides[key] = str(value)
    
    return overrides


def check_required_env_vars(
    skill_metadata: dict[str, Any],
) -> tuple[bool, list[str]]:
    """
    Check if all required environment variables are set.
    
    Args:
        skill_metadata: Skill metadata dict
    
    Returns:
        Tuple of (all_satisfied, missing_vars)
    """
    required_env = skill_metadata.get("requiredEnv", [])
    
    if not required_env:
        return True, []
    
    missing = []
    for var in required_env:
        if not os.environ.get(var):
            missing.append(var)
    
    return len(missing) == 0, missing
