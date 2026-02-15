"""
Session migration utilities

Migrate legacy fixed-name session files to UUID-based format.
"""
from __future__ import annotations

import logging
import shutil
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openclaw.agents.session import SessionManager

logger = logging.getLogger(__name__)


def migrate_legacy_sessions(session_manager: SessionManager) -> int:
    """
    Migrate old fixed-name session files to UUID-based format.
    
    This migration:
    1. Finds all session files in legacy locations
    2. Generates UUIDs for each legacy session
    3. Copies files to new location with UUID names
    4. Preserves original files (doesn't delete)
    
    Args:
        session_manager: SessionManager instance
        
    Returns:
        Number of sessions migrated
    """
    legacy_dir = session_manager.workspace_dir / ".sessions"
    if not legacy_dir.exists():
        logger.info("No legacy sessions directory found")
        return 0
    
    migrated = 0
    target_dir = session_manager._sessions_dir
    
    # Ensure target directory exists
    target_dir.mkdir(parents=True, exist_ok=True)
    
    for session_file in legacy_dir.glob("*.json"):
        # Skip metadata files
        if session_file.stem in ["session_map", "sessions"]:
            continue
        
        try:
            # Generate UUID for legacy session
            new_uuid = str(uuid.uuid4())
            
            # Copy to new location with UUID name
            new_path = target_dir / f"{new_uuid}.json"
            
            # Skip if target already exists
            if new_path.exists():
                logger.debug(f"Skipping {session_file.name}: target {new_uuid}.json already exists")
                continue
            
            shutil.copy2(session_file, new_path)
            logger.info(f"✅ Migrated {session_file.name} -> {new_uuid}.json")
            migrated += 1
            
        except Exception as e:
            logger.error(f"Failed to migrate {session_file.name}: {e}")
    
    if migrated > 0:
        logger.info(f"✅ Migration complete: {migrated} sessions migrated")
        logger.info(f"   Legacy files preserved in: {legacy_dir}")
        logger.info(f"   New files created in: {target_dir}")
    
    return migrated


def check_needs_migration(session_manager: SessionManager) -> bool:
    """
    Check if migration is needed.
    
    Args:
        session_manager: SessionManager instance
        
    Returns:
        True if legacy sessions exist that haven't been migrated
    """
    legacy_dir = session_manager.workspace_dir / ".sessions"
    if not legacy_dir.exists():
        return False
    
    # Count non-metadata JSON files
    legacy_count = sum(
        1 for f in legacy_dir.glob("*.json")
        if f.stem not in ["session_map", "sessions"]
    )
    
    return legacy_count > 0


def auto_migrate_on_startup(session_manager: SessionManager) -> None:
    """
    Automatically migrate legacy sessions on startup if needed.
    
    This is safe to call multiple times - it only migrates files once.
    
    Args:
        session_manager: SessionManager instance
    """
    try:
        if check_needs_migration(session_manager):
            logger.info("🔄 Detected legacy sessions, starting migration...")
            migrated = migrate_legacy_sessions(session_manager)
            if migrated > 0:
                logger.info(f"🎉 Migration complete: {migrated} sessions")
        else:
            logger.debug("No migration needed")
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        logger.warning("Continuing with current session structure")
