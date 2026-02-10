"""
Session workspace management utilities
Based on openclaw TypeScript: src/agents/sandbox/shared.ts

Each session gets its own isolated workspace directory for file generation.
This prevents file pollution and enables proper session isolation.
"""

import hashlib
import re
from pathlib import Path


def slugify_session_key(session_key: str) -> str:
    """
    Convert session key to safe directory name
    Based on TypeScript: slugifySessionKey()
    
    Creates a safe directory name with hash for uniqueness:
    - Lowercase
    - Replace non-alphanumeric with dash
    - Append 8-char hash for collision prevention
    
    Args:
        session_key: Session identifier (e.g., "telegram-8366053063")
    
    Returns:
        Safe directory name (e.g., "telegram-8366053063-a1b2c3d4")
    
    Examples:
        >>> slugify_session_key("telegram-8366053063")
        'telegram-8366053063-a1b2c3d4'
        
        >>> slugify_session_key("Discord#User#1234")
        'discord-user-1234-5e6f7g8h'
    """
    trimmed = session_key.strip() or "session"
    
    # Create SHA1 hash and take first 8 chars
    hash_obj = hashlib.sha1(trimmed.encode("utf-8"))
    hash_short = hash_obj.hexdigest()[:8]
    
    # Sanitize: lowercase, replace non-alphanumeric with dash
    safe = re.sub(r"[^a-z0-9._-]+", "-", trimmed.lower())
    safe = re.sub(r"^-+|-+$", "", safe)  # Remove leading/trailing dashes
    
    base = safe[:32] or "session"
    return f"{base}-{hash_short}"


def resolve_session_workspace_dir(workspace_root: Path | str, session_key: str) -> Path:
    """
    Get session-specific workspace directory
    Based on TypeScript: resolveSandboxWorkspaceDir()
    
    Each session gets its own isolated workspace:
    {workspace_root}/{slugified-session-key}/
    
    This ensures:
    - File isolation between sessions
    - Easy cleanup (delete session directory)
    - Organized file structure
    - No cross-session file pollution
    
    Args:
        workspace_root: Base workspace directory (e.g., ~/.openclaw/workspace)
        session_key: Session identifier
    
    Returns:
        Path to session-specific workspace directory
    
    Example:
        >>> resolve_session_workspace_dir("~/.openclaw/workspace", "telegram-8366053063")
        Path('/home/user/.openclaw/workspace/telegram-8366053063-a1b2c3d4')
    """
    root = Path(workspace_root).expanduser().resolve()
    slug = slugify_session_key(session_key)
    session_dir = root / slug
    
    # Ensure directory exists
    session_dir.mkdir(parents=True, exist_ok=True)
    
    return session_dir


def get_session_presentations_dir(session_workspace: Path) -> Path:
    """
    Get presentations subdirectory for session
    
    Args:
        session_workspace: Session workspace directory
    
    Returns:
        Path to presentations/ subdirectory
    
    Example:
        >>> get_session_presentations_dir(Path("/workspace/session-abc123"))
        Path('/workspace/session-abc123/presentations')
    """
    presentations_dir = session_workspace / "presentations"
    presentations_dir.mkdir(parents=True, exist_ok=True)
    return presentations_dir


def get_session_documents_dir(session_workspace: Path) -> Path:
    """
    Get documents subdirectory for session
    
    Args:
        session_workspace: Session workspace directory
    
    Returns:
        Path to documents/ subdirectory
    """
    docs_dir = session_workspace / "documents"
    docs_dir.mkdir(parents=True, exist_ok=True)
    return docs_dir


def get_session_images_dir(session_workspace: Path) -> Path:
    """
    Get images subdirectory for session
    
    Args:
        session_workspace: Session workspace directory
    
    Returns:
        Path to images/ subdirectory
    """
    images_dir = session_workspace / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    return images_dir


def get_session_temp_dir(session_workspace: Path) -> Path:
    """
    Get temp subdirectory for session
    
    Args:
        session_workspace: Session workspace directory
    
    Returns:
        Path to temp/ subdirectory
    """
    temp_dir = session_workspace / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


# For backward compatibility with existing code
def get_presentations_dir(workspace_dir: Path) -> Path:
    """Alias for get_session_presentations_dir (backward compatibility)"""
    return get_session_presentations_dir(workspace_dir)


def get_documents_dir(workspace_dir: Path) -> Path:
    """Alias for get_session_documents_dir (backward compatibility)"""
    return get_session_documents_dir(workspace_dir)


def get_images_dir(workspace_dir: Path) -> Path:
    """Alias for get_session_images_dir (backward compatibility)"""
    return get_session_images_dir(workspace_dir)
