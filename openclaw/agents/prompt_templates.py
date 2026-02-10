"""Prompt templates system matching TypeScript pi-mono/packages/coding-agent/src/core/prompt-templates.ts

Loads prompt templates from multiple sources and provides variable expansion.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PromptTemplate:
    """Represents a prompt template loaded from a markdown file"""
    
    name: str
    description: str
    content: str
    source: str  # "global", "project", "path"
    file_path: Path


def parse_command_args(args_string: str) -> list[str]:
    """
    Parse command arguments respecting quoted strings (bash-style)
    
    Args:
        args_string: String containing arguments
        
    Returns:
        List of parsed arguments
        
    Examples:
        >>> parse_command_args('arg1 "arg 2" arg3')
        ['arg1', 'arg 2', 'arg3']
        >>> parse_command_args("'single quotes' and \"double quotes\"")
        ['single quotes', 'and', 'double quotes']
    """
    args: list[str] = []
    current = ""
    in_quote: str | None = None
    
    for char in args_string:
        if in_quote:
            if char == in_quote:
                in_quote = None
            else:
                current += char
        elif char in ('"', "'"):
            in_quote = char
        elif char in (' ', '\t'):
            if current:
                args.append(current)
                current = ""
        else:
            current += char
    
    if current:
        args.append(current)
    
    return args


def substitute_args(content: str, args: list[str]) -> str:
    """
    Substitute argument placeholders in template content
    
    Supports:
    - $1, $2, ... for positional args
    - $@ and $ARGUMENTS for all args
    - ${@:N} for args from Nth onwards (bash-style slicing)
    - ${@:N:L} for L args starting from Nth
    
    Note: Replacement happens on the template string only. Argument values
    containing patterns like $1, $@, or $ARGUMENTS are NOT recursively substituted.
    
    Args:
        content: Template content with placeholders
        args: List of argument values
        
    Returns:
        Content with placeholders replaced
        
    Examples:
        >>> substitute_args("Hello $1!", ["World"])
        'Hello World!'
        >>> substitute_args("$@ together", ["All", "args"])
        'All args together'
        >>> substitute_args("${@:2}", ["a", "b", "c"])
        'b c'
    """
    result = content
    
    # Replace $1, $2, etc. with positional args FIRST (before wildcards)
    # This prevents wildcard replacement values containing $<digit> patterns from being re-substituted
    result = re.sub(
        r'\$(\d+)',
        lambda m: args[int(m.group(1)) - 1] if int(m.group(1)) - 1 < len(args) else "",
        result
    )
    
    # Replace ${@:start} or ${@:start:length} with sliced args (bash-style)
    # Process BEFORE simple $@ to avoid conflicts
    def replace_slice(match: re.Match) -> str:
        start_str = match.group(1)
        length_str = match.group(2)
        
        start = int(start_str) - 1  # Convert to 0-indexed (user provides 1-indexed)
        # Treat 0 as 1 (bash convention: args start at 1)
        if start < 0:
            start = 0
        
        if length_str:
            length = int(length_str)
            return " ".join(args[start:start + length])
        return " ".join(args[start:])
    
    result = re.sub(r'\$\{@:(\d+)(?::(\d+))?\}', replace_slice, result)
    
    # Pre-compute all args joined (optimization)
    all_args = " ".join(args)
    
    # Replace $ARGUMENTS with all args joined (new syntax, aligns with Claude, Codex, OpenCode)
    result = result.replace("$ARGUMENTS", all_args)
    
    # Replace $@ with all args joined (existing syntax)
    result = result.replace("$@", all_args)
    
    return result


def _load_template_from_file(
    file_path: Path,
    source: str,
    source_label: str
) -> PromptTemplate | None:
    """
    Load a single template from a markdown file
    
    Args:
        file_path: Path to the .md file
        source: Source identifier ("global", "project", "path")
        source_label: Human-readable source label
        
    Returns:
        PromptTemplate if successful, None otherwise
    """
    try:
        raw_content = file_path.read_text(encoding="utf-8")
        
        # Parse frontmatter if present
        from ..utils.frontmatter import parse_frontmatter
        
        frontmatter, body = parse_frontmatter(raw_content)
        
        name = file_path.stem  # filename without extension
        
        # Get description from frontmatter or first non-empty line
        description = frontmatter.get("description", "")
        if not description:
            first_line = next((line for line in body.split("\n") if line.strip()), None)
            if first_line:
                # Truncate if too long
                description = first_line[:60]
                if len(first_line) > 60:
                    description += "..."
        
        # Append source to description
        description = f"{description} {source_label}" if description else source_label
        
        return PromptTemplate(
            name=name,
            description=description,
            content=body,
            source=source,
            file_path=file_path,
        )
    except Exception as e:
        logger.debug(f"Failed to load template from {file_path}: {e}")
        return None


def load_templates_from_dir(
    dir_path: Path,
    source: str,
    source_label: str
) -> list[PromptTemplate]:
    """
    Scan a directory for .md files (non-recursive) and load them as prompt templates
    
    Args:
        dir_path: Directory to scan
        source: Source identifier
        source_label: Human-readable source label
        
    Returns:
        List of loaded templates
    """
    templates: list[PromptTemplate] = []
    
    if not dir_path.exists():
        return templates
    
    try:
        for entry in dir_path.iterdir():
            if entry.is_file() and entry.suffix == ".md":
                template = _load_template_from_file(entry, source, source_label)
                if template:
                    templates.append(template)
    except Exception as e:
        logger.warning(f"Error scanning directory {dir_path}: {e}")
    
    return templates


def load_prompt_templates(
    workspace_dir: Path | None = None,
    extra_paths: list[Path] | None = None,
    agent_dir: Path | None = None,
) -> list[PromptTemplate]:
    """
    Load prompt templates from multiple sources
    
    Sources (in priority order):
    1. Extra paths (if provided)
    2. Project templates: workspace/.pi/prompts/
    3. Global templates: agent_dir/prompts/
    
    Args:
        workspace_dir: Workspace directory (for project templates)
        extra_paths: Additional directories to load templates from
        agent_dir: Agent directory (for global templates)
        
    Returns:
        List of all loaded templates
    """
    templates: list[PromptTemplate] = []
    
    # Load from extra paths first (highest priority)
    if extra_paths:
        for path in extra_paths:
            if path.is_dir():
                templates.extend(
                    load_templates_from_dir(path, "path", f"(from {path.name})")
                )
            elif path.is_file() and path.suffix == ".md":
                template = _load_template_from_file(path, "path", f"(from {path.parent.name})")
                if template:
                    templates.append(template)
    
    # Load from project templates (workspace/.pi/prompts/)
    if workspace_dir:
        project_prompts_dir = workspace_dir / ".pi" / "prompts"
        templates.extend(
            load_templates_from_dir(project_prompts_dir, "project", "(project)")
        )
    
    # Load from global templates (agent_dir/prompts/)
    if agent_dir:
        global_prompts_dir = agent_dir / "prompts"
        templates.extend(
            load_templates_from_dir(global_prompts_dir, "global", "(global)")
        )
    
    logger.info(f"Loaded {len(templates)} prompt templates")
    
    return templates


def expand_prompt_template(template: PromptTemplate, args: list[str]) -> str:
    """
    Expand a template by substituting argument placeholders
    
    Args:
        template: Template to expand
        args: Arguments to substitute
        
    Returns:
        Expanded template content
    """
    return substitute_args(template.content, args)


def find_template_by_name(
    templates: list[PromptTemplate],
    name: str
) -> PromptTemplate | None:
    """
    Find a template by name
    
    Args:
        templates: List of templates to search
        name: Template name to find
        
    Returns:
        Matching template or None
    """
    for template in templates:
        if template.name == name:
            return template
    return None


def list_template_names(templates: list[PromptTemplate]) -> list[str]:
    """
    Get list of template names
    
    Args:
        templates: List of templates
        
    Returns:
        List of template names
    """
    return [t.name for t in templates]
