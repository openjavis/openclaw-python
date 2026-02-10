"""Subagent registry persistence

Stores registry to disk for recovery across restarts.
Matches TypeScript openclaw/src/agents/subagent-registry.store.ts
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .subagent_registry import SubagentRunRecord

logger = logging.getLogger(__name__)


def get_registry_file_path() -> Path:
    """Get path to registry file"""
    from ..config.paths import get_openclaw_data_dir
    
    data_dir = get_openclaw_data_dir()
    return data_dir / "subagent-registry.json"


def save_subagent_registry_to_disk(runs: dict[str, "SubagentRunRecord"]):
    """
    Save subagent registry to disk
    
    Args:
        runs: Dict of run_id -> SubagentRunRecord
    """
    file_path = get_registry_file_path()
    
    try:
        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to serializable format
        data = {
            "version": 1,
            "runs": {
                run_id: record.to_dict()
                for run_id, record in runs.items()
            }
        }
        
        # Write atomically (write to temp, then rename)
        temp_file = file_path.with_suffix(".tmp")
        with open(temp_file, "w") as f:
            json.dump(data, f, indent=2)
        
        temp_file.replace(file_path)
        
    except Exception as e:
        logger.error(f"Failed to save subagent registry: {e}")


def load_subagent_registry_from_disk() -> dict[str, "SubagentRunRecord"]:
    """
    Load subagent registry from disk
    
    Returns:
        Dict of run_id -> SubagentRunRecord
    """
    from .subagent_registry import SubagentRunRecord
    
    file_path = get_registry_file_path()
    
    if not file_path.exists():
        return {}
    
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
        
        runs_data = data.get("runs", {})
        
        # Convert back to SubagentRunRecord objects
        runs = {}
        for run_id, record_data in runs_data.items():
            try:
                record = SubagentRunRecord(**record_data)
                runs[run_id] = record
            except Exception as e:
                logger.warning(f"Failed to load run {run_id}: {e}")
        
        return runs
        
    except Exception as e:
        logger.error(f"Failed to load subagent registry: {e}")
        return {}
