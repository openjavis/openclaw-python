"""
Bootstrap Hook System

Allows hooks to modify bootstrap files before injection into system prompt.
Matches TypeScript openclaw/src/agents/bootstrap-hooks.ts

Example hook:
    # hooks/agent/bootstrap.py
    async def handler(context):
        # Modify SOUL.md content
        for file in context["bootstrap_files"]:
            if file.name == "SOUL.md":
                file.content = "Custom persona..."
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


async def apply_bootstrap_hook_overrides(
    files: list[Any],  # WorkspaceBootstrapFile type
    workspace_dir: Path,
    config: dict | None = None,
    session_key: str | None = None,
) -> list[Any]:
    """
    Apply bootstrap hook overrides.
    
    Allows hooks to modify bootstrap files before injection into system prompt.
    
    The hook system allows extensions to:
    - Modify existing bootstrap files (e.g., customize SOUL.md)
    - Add new bootstrap files
    - Remove bootstrap files
    - Transform file content based on session context
    
    Args:
        files: List of WorkspaceBootstrapFile objects
        workspace_dir: Workspace directory path
        config: Optional configuration dictionary
        session_key: Optional session key for session-specific customization
        
    Returns:
        Modified list of bootstrap files
    """
    # Create hook context
    context = {
        "workspace_dir": workspace_dir,
        "bootstrap_files": files,
        "config": config,
        "session_key": session_key,
    }
    
    # Try to trigger hook: "agent:bootstrap"
    try:
        # Check if hooks module exists
        from openclaw.hooks import trigger_hook
        
        await trigger_hook("agent", "bootstrap", context)
        
        # Return modified files
        modified_files = context.get("bootstrap_files", files)
        
        logger.info(f"Applied bootstrap hooks: {len(files)} -> {len(modified_files)} files")
        
        return modified_files
        
    except ImportError:
        # Hooks module not available, return original files
        logger.debug("Hooks module not available, skipping bootstrap hooks")
        return files
    except Exception as e:
        # Hook execution failed, log and return original files
        logger.warning(f"Bootstrap hook execution failed: {e}", exc_info=True)
        return files


async def apply_bootstrap_file_transformations(
    files: list[Any],
    workspace_dir: Path,
    transformations: list[callable] | None = None,
) -> list[Any]:
    """
    Apply custom transformations to bootstrap files.
    
    This is a simpler alternative to the full hook system.
    Useful for inline transformations without setting up hooks.
    
    Args:
        files: List of WorkspaceBootstrapFile objects
        workspace_dir: Workspace directory path
        transformations: List of transformation functions
        
    Returns:
        Transformed bootstrap files
    """
    if not transformations:
        return files
    
    modified_files = list(files)
    
    for transform_fn in transformations:
        try:
            modified_files = await transform_fn(modified_files, workspace_dir)
        except Exception as e:
            logger.warning(f"Bootstrap transformation failed: {e}", exc_info=True)
    
    return modified_files


def create_bootstrap_file_filter(
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
) -> callable:
    """
    Create a bootstrap file filter transformation.
    
    Args:
        include_patterns: List of glob patterns to include
        exclude_patterns: List of glob patterns to exclude
        
    Returns:
        Filter transformation function
    """
    import fnmatch
    
    async def filter_transform(files: list[Any], workspace_dir: Path) -> list[Any]:
        filtered = []
        
        for file in files:
            file_name = getattr(file, "name", "")
            
            # Check exclude patterns
            if exclude_patterns:
                excluded = any(
                    fnmatch.fnmatch(file_name, pattern)
                    for pattern in exclude_patterns
                )
                if excluded:
                    logger.debug(f"Excluding bootstrap file: {file_name}")
                    continue
            
            # Check include patterns
            if include_patterns:
                included = any(
                    fnmatch.fnmatch(file_name, pattern)
                    for pattern in include_patterns
                )
                if not included:
                    logger.debug(f"Not including bootstrap file: {file_name}")
                    continue
            
            filtered.append(file)
        
        return filtered
    
    return filter_transform


def create_bootstrap_file_content_modifier(
    file_name: str,
    content_modifier: callable,
) -> callable:
    """
    Create a bootstrap file content modifier transformation.
    
    Args:
        file_name: Name of file to modify
        content_modifier: Function to modify content (str -> str)
        
    Returns:
        Content modifier transformation function
    """
    async def modifier_transform(files: list[Any], workspace_dir: Path) -> list[Any]:
        modified = []
        
        for file in files:
            if getattr(file, "name", "") == file_name:
                # Modify this file's content
                try:
                    old_content = getattr(file, "content", "")
                    new_content = content_modifier(old_content)
                    
                    # Create modified file object
                    # Note: This assumes the file object is mutable
                    # If not, we'd need to create a new object
                    if hasattr(file, "content"):
                        file.content = new_content
                    
                    logger.info(f"Modified bootstrap file content: {file_name}")
                except Exception as e:
                    logger.warning(f"Failed to modify {file_name}: {e}")
            
            modified.append(file)
        
        return modified
    
    return modifier_transform
