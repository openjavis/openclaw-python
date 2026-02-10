"""
Task prompt loader

Loads task-specific prompts from .pi/prompts/ directory.
These are workflow templates for specific tasks like PR review, changelog auditing, etc.

Enhanced with prompt template variable expansion support.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import NamedTuple

import yaml

from .prompt_templates import (
    expand_prompt_template,
    load_prompt_templates,
    parse_command_args,
    PromptTemplate,
    find_template_by_name,
)

logger = logging.getLogger(__name__)


class TaskPrompt(NamedTuple):
    """Task prompt with metadata"""
    name: str
    description: str
    content: str
    frontmatter: dict


def load_task_prompt(prompt_path: Path) -> TaskPrompt | None:
    """
    Load a task prompt from file
    
    Task prompts are markdown files with YAML frontmatter:
    
    ---
    description: Brief description
    ---
    
    # Prompt content here
    
    Args:
        prompt_path: Path to prompt file (.md)
    
    Returns:
        TaskPrompt object or None if failed to load
    """
    if not prompt_path.exists():
        logger.warning(f"Task prompt not found: {prompt_path}")
        return None
    
    try:
        content = prompt_path.read_text(encoding="utf-8")
        
        # Parse frontmatter (YAML between --- markers)
        match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
        
        if not match:
            # No frontmatter - entire file is content
            logger.debug(f"No frontmatter in {prompt_path.name}")
            return TaskPrompt(
                name=prompt_path.stem,
                description="",
                content=content,
                frontmatter={}
            )
        
        frontmatter_text = match.group(1)
        body = match.group(2)
        
        # Parse YAML frontmatter
        try:
            frontmatter = yaml.safe_load(frontmatter_text) or {}
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML frontmatter in {prompt_path.name}: {e}")
            frontmatter = {}
        
        return TaskPrompt(
            name=prompt_path.stem,
            description=frontmatter.get("description", ""),
            content=body,
            frontmatter=frontmatter
        )
    
    except Exception as e:
        logger.error(f"Failed to load task prompt {prompt_path}: {e}", exc_info=True)
        return None


def list_task_prompts(workspace_dir: Path) -> list[TaskPrompt]:
    """
    List all available task prompts
    
    Args:
        workspace_dir: Workspace directory (looks for .pi/prompts/ subdirectory)
    
    Returns:
        List of TaskPrompt objects
    """
    prompts_dir = workspace_dir / ".pi" / "prompts"
    
    if not prompts_dir.exists():
        logger.debug(f"Task prompts directory not found: {prompts_dir}")
        return []
    
    prompts = []
    
    for prompt_file in prompts_dir.glob("*.md"):
        prompt = load_task_prompt(prompt_file)
        if prompt:
            prompts.append(prompt)
    
    logger.debug(f"Loaded {len(prompts)} task prompts from {prompts_dir}")
    return prompts


def get_task_prompt(workspace_dir: Path, prompt_name: str) -> TaskPrompt | None:
    """
    Get a specific task prompt by name
    
    Args:
        workspace_dir: Workspace directory
        prompt_name: Prompt name (without .md extension)
    
    Returns:
        TaskPrompt object or None if not found
    """
    prompts_dir = workspace_dir / ".pi" / "prompts"
    prompt_path = prompts_dir / f"{prompt_name}.md"
    
    return load_task_prompt(prompt_path)


def format_task_prompt_summary(prompts: list[TaskPrompt]) -> str:
    """
    Format a summary of available task prompts
    
    Args:
        prompts: List of TaskPrompt objects
    
    Returns:
        Formatted summary string
    """
    if not prompts:
        return "No task prompts available."
    
    lines = ["Available task prompts:", ""]
    
    for prompt in sorted(prompts, key=lambda p: p.name):
        desc = prompt.description or "No description"
        lines.append(f"- {prompt.name}: {desc}")
    
    return "\n".join(lines)


def load_all_prompt_templates(
    workspace_dir: Path,
    agent_dir: Path | None = None,
) -> list[PromptTemplate]:
    """
    Load all prompt templates from multiple sources
    
    Args:
        workspace_dir: Workspace directory
        agent_dir: Agent directory (for global templates)
        
    Returns:
        List of all prompt templates
    """
    return load_prompt_templates(
        workspace_dir=workspace_dir,
        agent_dir=agent_dir,
    )


def expand_task_prompt_with_args(
    template: PromptTemplate,
    args_string: str
) -> str:
    """
    Expand a task prompt template with arguments
    
    Args:
        template: Prompt template
        args_string: Space-separated arguments (supports quotes)
        
    Returns:
        Expanded prompt content
    """
    args = parse_command_args(args_string)
    return expand_prompt_template(template, args)


def get_task_prompt_by_name(
    workspace_dir: Path,
    name: str,
    agent_dir: Path | None = None,
) -> PromptTemplate | None:
    """
    Get a task prompt by name
    
    Args:
        workspace_dir: Workspace directory
        name: Template name
        agent_dir: Agent directory
        
    Returns:
        Prompt template or None
    """
    templates = load_all_prompt_templates(workspace_dir, agent_dir)
    return find_template_by_name(templates, name)
