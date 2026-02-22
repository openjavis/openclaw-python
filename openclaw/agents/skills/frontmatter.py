"""
Frontmatter parsing for SKILL.md files

Matches TypeScript src/agents/skills/frontmatter.ts
"""
from __future__ import annotations

import logging
import re
from typing import Any

import yaml

from .types import (
    OpenClawSkillMetadata,
    SkillInstallSpec,
    SkillInvocationPolicy,
)

logger = logging.getLogger(__name__)


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """
    Parse YAML frontmatter from markdown (matches TS parseFrontmatterBlock).
    
    Format:
    ---
    name: skill-name
    description: Description
    openclaw:
      always: true
    ---
    
    # Skill Content
    
    Args:
        content: Full markdown content
    
    Returns:
        (frontmatter_dict, body_content)
    """
    # Match ---\n...\n---
    pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
    match = re.match(pattern, content, re.DOTALL)
    
    if not match:
        return {}, content
    
    yaml_content = match.group(1)
    body = match.group(2)
    
    try:
        frontmatter = yaml.safe_load(yaml_content) or {}
        if not isinstance(frontmatter, dict):
            logger.warning(f"Frontmatter is not a dict: {type(frontmatter)}")
            return {}, content
    except yaml.YAMLError as e:
        logger.warning(f"Failed to parse YAML frontmatter: {e}")
        return {}, content
    
    return frontmatter, body


def parse_openclaw_metadata(frontmatter: dict[str, Any]) -> OpenClawSkillMetadata | None:
    """
    Extract OpenClaw metadata from frontmatter (matches TS resolveOpenClawMetadata).
    
    Args:
        frontmatter: Parsed frontmatter dictionary
    
    Returns:
        OpenClawSkillMetadata or None
    """
    openclaw = frontmatter.get("openclaw", {})
    
    if not openclaw or not isinstance(openclaw, dict):
        return None
    
    # Parse requires section
    requires_raw = openclaw.get("requires", {})
    requires = {}
    if isinstance(requires_raw, dict):
        for key in ["bins", "anyBins", "env", "config"]:
            value = requires_raw.get(key, [])
            if value:
                requires[key] = normalize_string_list(value)
    
    # Parse install specs
    install_raw = openclaw.get("install", [])
    install = []
    if isinstance(install_raw, list):
        for spec in install_raw:
            parsed = parse_install_spec(spec)
            if parsed:
                install.append(parsed)
    
    return OpenClawSkillMetadata(
        always=openclaw.get("always", False),
        skill_key=openclaw.get("skillKey"),
        primary_env=openclaw.get("primaryEnv"),
        emoji=openclaw.get("emoji"),
        homepage=openclaw.get("homepage"),
        os=normalize_string_list(openclaw.get("os", [])),
        requires=requires,
        install=install
    )


def parse_install_spec(spec: Any) -> SkillInstallSpec | None:
    """
    Parse installation spec (matches TS parseInstallSpec).
    
    Args:
        spec: Raw install spec from YAML
    
    Returns:
        SkillInstallSpec or None
    """
    if not spec or not isinstance(spec, dict):
        return None
    
    # Get kind
    kind_raw = spec.get("kind", spec.get("type", ""))
    if not isinstance(kind_raw, str):
        return None
    
    kind = kind_raw.strip().lower()
    if kind not in ("brew", "node", "go", "uv", "download"):
        return None
    
    return SkillInstallSpec(
        kind=kind,
        id=spec.get("id"),
        label=spec.get("label"),
        bins=normalize_string_list(spec.get("bins", [])),
        os=normalize_string_list(spec.get("os", [])),
        formula=spec.get("formula"),
        package=spec.get("package"),
        module=spec.get("module"),
        url=spec.get("url"),
        archive=spec.get("archive"),
        extract=spec.get("extract", False),
        strip_components=spec.get("stripComponents", 0),
        target_dir=spec.get("targetDir"),
    )


def parse_invocation_policy(frontmatter: dict[str, Any]) -> SkillInvocationPolicy:
    """
    Extract invocation policy from frontmatter (matches TS resolveSkillInvocationPolicy).
    
    Args:
        frontmatter: Parsed frontmatter dictionary
    
    Returns:
        SkillInvocationPolicy
    """
    openclaw = frontmatter.get("openclaw", {})
    
    if not isinstance(openclaw, dict):
        return SkillInvocationPolicy()
    
    user_invocable = openclaw.get("userInvocable", True)
    disable_model = openclaw.get("disableModelInvocation", False)
    
    return SkillInvocationPolicy(
        user_invocable=user_invocable,
        disable_model_invocation=disable_model
    )


def normalize_string_list(value: Any) -> list[str]:
    """
    Normalize value to string list (matches TS normalizeStringList).
    
    Args:
        value: Raw value (string, list, or other)
    
    Returns:
        List of strings
    """
    if not value:
        return []
    
    if isinstance(value, list):
        return [str(item).strip() for item in value if item]
    
    if isinstance(value, str):
        # Split by comma
        return [item.strip() for item in value.split(",") if item.strip()]
    
    return []


def extract_description_from_body(body: str, max_length: int = 200) -> str:
    """
    Extract description from markdown body.
    
    Takes the first paragraph as description.
    
    Args:
        body: Markdown body content
        max_length: Maximum description length
    
    Returns:
        Description string
    """
    if not body:
        return ""
    
    # Get first paragraph
    paragraphs = body.strip().split("\n\n")
    if not paragraphs:
        return ""
    
    # Remove markdown headers
    first_para = paragraphs[0].strip()
    first_para = re.sub(r'^#+\s*', '', first_para)
    
    # Limit length
    if len(first_para) > max_length:
        first_para = first_para[:max_length] + "..."
    
    return first_para


def parse_skill_frontmatter(content: str, path: str) -> "Any | None":
    """
    Parse a SKILL.md file into a Skill object.

    Convenience wrapper that combines parse_frontmatter + Skill construction.

    Args:
        content: Full SKILL.md file content.
        path: File path (used as the skill's ``location``).

    Returns:
        Skill object, or None if parsing fails.
    """
    from .types import Skill

    frontmatter, body = parse_frontmatter(content)
    if not frontmatter:
        return None

    name = frontmatter.get("name") or ""
    description = frontmatter.get("description") or extract_description_from_body(body)
    if not name:
        return None

    skill = Skill(name=name, description=description, location=path)
    # Attach the full body so tests can inspect it
    skill.content = body  # type: ignore[attr-defined]
    return skill
