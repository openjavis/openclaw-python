"""Frontmatter parsing utilities

Parses YAML frontmatter from markdown files.
"""
from __future__ import annotations

import re
from typing import Any, TypeVar

import yaml

T = TypeVar('T')


def parse_frontmatter(content: str, default: dict[str, Any] | None = None) -> tuple[dict[str, Any], str]:
    """
    Parse YAML frontmatter from markdown content
    
    Args:
        content: Full markdown content
        default: Default frontmatter dict if parsing fails
        
    Returns:
        Tuple of (frontmatter dict, body content)
        
    Examples:
        >>> content = '''---
        ... title: Example
        ... ---
        ... Body content
        ... '''
        >>> fm, body = parse_frontmatter(content)
        >>> fm['title']
        'Example'
        >>> 'Body content' in body
        True
    """
    if default is None:
        default = {}
    
    # Check if content starts with frontmatter delimiter
    if not content.startswith("---"):
        return default, content
    
    # Find end of frontmatter
    match = re.search(r'^---\s*$', content[3:], re.MULTILINE)
    if not match:
        return default, content
    
    # Extract frontmatter and body
    end_index = match.end() + 3  # +3 for initial "---"
    frontmatter_text = content[3:match.start() + 3].strip()
    body = content[end_index:].strip()
    
    # Parse YAML
    try:
        frontmatter = yaml.safe_load(frontmatter_text) or default
    except yaml.YAMLError:
        frontmatter = default
    
    return frontmatter, body
