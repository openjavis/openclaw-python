"""Workspace templates system

Loads templates from docs/reference/templates directory.
Matches TypeScript workspace-templates.ts
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from .prompt_templates import PromptTemplate, load_templates_from_dir

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceTemplate:
    """Workspace template metadata"""
    
    name: str
    category: str
    description: str
    content: str
    file_path: Path


def load_workspace_templates(
    workspace_dir: Path | None = None,
    docs_dir: Path | None = None,
) -> list[WorkspaceTemplate]:
    """
    Load workspace templates from docs/reference/templates
    
    Args:
        workspace_dir: Workspace directory
        docs_dir: Documentation directory (defaults to workspace/docs)
        
    Returns:
        List of workspace templates
    """
    templates: list[WorkspaceTemplate] = []
    
    # Determine templates directory
    if docs_dir:
        templates_dir = docs_dir / "reference" / "templates"
    elif workspace_dir:
        templates_dir = workspace_dir / "docs" / "reference" / "templates"
    else:
        return templates
    
    if not templates_dir.exists():
        logger.debug(f"Workspace templates directory not found: {templates_dir}")
        return templates
    
    # Load templates using prompt_templates loader
    prompt_templates = load_templates_from_dir(
        templates_dir,
        "workspace",
        "(workspace)"
    )
    
    # Convert to WorkspaceTemplate format
    for pt in prompt_templates:
        # Extract category from path if in subdirectory
        relative_path = pt.file_path.relative_to(templates_dir)
        category = relative_path.parent.name if len(relative_path.parents) > 1 else "general"
        
        templates.append(WorkspaceTemplate(
            name=pt.name,
            category=category,
            description=pt.description,
            content=pt.content,
            file_path=pt.file_path,
        ))
    
    logger.info(f"Loaded {len(templates)} workspace templates")
    
    return templates


def find_workspace_template_by_name(
    templates: list[WorkspaceTemplate],
    name: str
) -> WorkspaceTemplate | None:
    """
    Find a workspace template by name
    
    Args:
        templates: List of templates to search
        name: Template name
        
    Returns:
        Matching template or None
    """
    for template in templates:
        if template.name == name:
            return template
    return None


def group_templates_by_category(
    templates: list[WorkspaceTemplate]
) -> dict[str, list[WorkspaceTemplate]]:
    """
    Group templates by category
    
    Args:
        templates: List of templates
        
    Returns:
        Dict mapping category to list of templates
    """
    grouped: dict[str, list[WorkspaceTemplate]] = {}
    
    for template in templates:
        category = template.category
        if category not in grouped:
            grouped[category] = []
        grouped[category].append(template)
    
    return grouped
