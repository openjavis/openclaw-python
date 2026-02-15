"""
Path resolution utilities matching pi-mono's path-utils.ts

This module provides path resolution with macOS compatibility:
- Expand ~ and environment variables
- Resolve relative to cwd
- Handle macOS filename quirks (NFD, special quotes, AM/PM spaces)

Matches pi-mono/packages/coding-agent/src/core/tools/path-utils.ts
"""
from __future__ import annotations

import os
import unicodedata
from pathlib import Path


def expand_path(path: str) -> str:
    """
    Expand ~ and environment variables in path.
    
    Args:
        path: Path to expand
        
    Returns:
        Expanded path
    """
    # Expand ~ to home directory
    path = os.path.expanduser(path)
    
    # Expand environment variables
    path = os.path.expandvars(path)
    
    return path


def resolve_to_cwd(file_path: str, cwd: str) -> str:
    """
    Resolve file path relative to cwd.
    
    If path is absolute, returns as-is.
    If path is relative, resolves relative to cwd.
    
    Args:
        file_path: File path (relative or absolute)
        cwd: Current working directory
        
    Returns:
        Absolute path
    """
    expanded = expand_path(file_path)
    
    if os.path.isabs(expanded):
        return expanded
    
    return os.path.join(cwd, expanded)


def resolve_read_path(file_path: str, cwd: str) -> str:
    """
    Resolve file path for reading with macOS compatibility.
    
    Tries multiple variants:
    1. Standard resolution
    2. NFD normalization (macOS stores filenames in NFD form)
    3. Curly quote variant (macOS uses U+2019 in screenshot names)
    4. AM/PM space variant (macOS uses U+202F narrow no-break space)
    5. Combined NFD + curly quote (for French macOS screenshots)
    
    Args:
        file_path: File path to resolve
        cwd: Current working directory
        
    Returns:
        Absolute path (using first variant that exists)
    """
    resolved = resolve_to_cwd(file_path, cwd)
    
    # Try standard path first
    if os.path.exists(resolved):
        return resolved
    
    # Try macOS AM/PM variant (narrow no-break space before AM/PM)
    am_pm_variant = try_macos_screenshot_path(resolved)
    if am_pm_variant != resolved and os.path.exists(am_pm_variant):
        return am_pm_variant
    
    # Try NFD variant (macOS stores filenames in NFD form)
    nfd_variant = try_nfd_variant(resolved)
    if nfd_variant != resolved and os.path.exists(nfd_variant):
        return nfd_variant
    
    # Try curly quote variant (macOS uses U+2019 in screenshot names)
    curly_variant = try_curly_quote_variant(resolved)
    if curly_variant != resolved and os.path.exists(curly_variant):
        return curly_variant
    
    # Try combined NFD + curly quote (for French macOS screenshots like "Capture d'écran")
    nfd_curly_variant = try_curly_quote_variant(nfd_variant)
    if nfd_curly_variant != resolved and os.path.exists(nfd_curly_variant):
        return nfd_curly_variant
    
    # Return original if none exist
    return resolved


def try_nfd_variant(path: str) -> str:
    """
    Try NFD normalization for macOS compatibility.
    
    macOS stores filenames in NFD (decomposed) form.
    For example, "é" becomes "e" + combining acute accent.
    
    Args:
        path: Path to normalize
        
    Returns:
        NFD-normalized path
    """
    try:
        return unicodedata.normalize('NFD', path)
    except Exception:
        return path


def try_curly_quote_variant(path: str) -> str:
    """
    Try replacing straight quotes with curly quotes.
    
    macOS screenshot names use U+2019 (RIGHT SINGLE QUOTATION MARK)
    instead of U+0027 (APOSTROPHE).
    
    For example:
    - "Screenshot 2024-01-01 at 12:00:00 PM.png" (user types)
    - "Screenshot 2024-01-01 at 12:00:00 PM.png" (macOS filename, with U+2019)
    
    Args:
        path: Path to convert
        
    Returns:
        Path with curly quotes
    """
    # Replace straight apostrophe with right single quotation mark
    return path.replace("'", "\u2019")


def try_macos_screenshot_path(path: str) -> str:
    """
    Try replacing space before AM/PM with narrow no-break space.
    
    macOS screenshot names use U+202F (NARROW NO-BREAK SPACE)
    before AM/PM instead of regular space.
    
    For example:
    - "Screenshot 2024-01-01 at 12:00:00 PM.png" (user types)
    - "Screenshot 2024-01-01 at 12:00:00 PM.png" (macOS filename, with U+202F)
    
    Args:
        path: Path to convert
        
    Returns:
        Path with narrow no-break space before AM/PM
    """
    # Replace space before AM/PM with narrow no-break space
    path = path.replace(" AM", "\u202F" + "AM")
    path = path.replace(" PM", "\u202F" + "PM")
    return path


__all__ = [
    "expand_path",
    "resolve_to_cwd",
    "resolve_read_path",
    "try_nfd_variant",
    "try_curly_quote_variant",
    "try_macos_screenshot_path",
]
