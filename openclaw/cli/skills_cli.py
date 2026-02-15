"""
Skills CLI commands.

Provides CLI commands for managing skills.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Any

from openclaw.agents.skills import (
    load_skill_entries,
    get_default_bundled_skills_dir,
    get_default_managed_skills_dir,
    build_eligibility_context,
    should_include_skill,
)
from openclaw.agents.skills.installer import install_skill_dependencies


def skills_list_command(config: dict | None = None, workspace_dir: Path | None = None) -> int:
    """
    List all available skills.
    
    Returns:
        Exit code
    """
    bundled_dir = get_default_bundled_skills_dir()
    managed_dir = get_default_managed_skills_dir()
    
    skill_entries = load_skill_entries(
        workspace_dir=workspace_dir,
        config=config,
        managed_skills_dir=managed_dir,
        bundled_skills_dir=bundled_dir
    )
    
    if not skill_entries:
        print("No skills found.")
        return 0
    
    print(f"Found {len(skill_entries)} skills:\n")
    
    for entry in sorted(skill_entries, key=lambda e: e.skill.name):
        skill = entry.skill
        emoji = skill.metadata.emoji if skill.metadata else "📦"
        source_tag = f"[{entry.source}]"
        
        print(f"{emoji} {skill.name:<20} {source_tag:<12} {skill.description}")
    
    print()
    return 0


def skills_info_command(skill_name: str, config: dict | None = None, workspace_dir: Path | None = None) -> int:
    """
    Show detailed information about a skill.
    
    Args:
        skill_name: Name of skill to show info for
        config: Configuration
        workspace_dir: Workspace directory
        
    Returns:
        Exit code
    """
    bundled_dir = get_default_bundled_skills_dir()
    managed_dir = get_default_managed_skills_dir()
    
    skill_entries = load_skill_entries(
        workspace_dir=workspace_dir,
        config=config,
        managed_skills_dir=managed_dir,
        bundled_skills_dir=bundled_dir
    )
    
    # Find skill
    entry = next((e for e in skill_entries if e.skill.name == skill_name), None)
    
    if not entry:
        print(f"Skill not found: {skill_name}")
        return 1
    
    skill = entry.skill
    
    print(f"Skill: {skill.name}")
    print(f"Description: {skill.description}")
    print(f"Source: {entry.source}")
    print(f"Location: {skill.file_path}")
    
    if skill.metadata:
        metadata = skill.metadata
        print()
        print("Metadata:")
        
        if metadata.emoji:
            print(f"  Emoji: {metadata.emoji}")
        
        if metadata.homepage:
            print(f"  Homepage: {metadata.homepage}")
        
        if metadata.os:
            print(f"  OS: {', '.join(metadata.os)}")
        
        if metadata.requires:
            print()
            print("Requirements:")
            
            if metadata.requires.bins:
                print(f"  Binaries: {', '.join(metadata.requires.bins)}")
            
            if metadata.requires.any_bins:
                print(f"  Any Binaries: {', '.join(metadata.requires.any_bins)}")
            
            if metadata.requires.env:
                print(f"  Environment: {', '.join(metadata.requires.env)}")
            
            if metadata.requires.config:
                print(f"  Config: {', '.join(metadata.requires.config)}")
        
        if metadata.install:
            print()
            print("Installation:")
            for spec in metadata.install:
                print(f"  - {spec.kind}: {spec.formula or spec.package or spec.module or spec.url}")
    
    print()
    return 0


def skills_check_command(skill_name: str, config: dict | None = None, workspace_dir: Path | None = None) -> int:
    """
    Check if a skill's requirements are met.
    
    Args:
        skill_name: Name of skill to check
        config: Configuration
        workspace_dir: Workspace directory
        
    Returns:
        Exit code (0 if eligible, 1 if not)
    """
    bundled_dir = get_default_bundled_skills_dir()
    managed_dir = get_default_managed_skills_dir()
    
    # Load all skills (including ineligible)
    from openclaw.agents.skills.loader import _load_skills_to_map
    
    all_skills = {}
    if bundled_dir:
        _load_skills_to_map(bundled_dir, "bundled", all_skills, include_root=False)
    if managed_dir:
        _load_skills_to_map(managed_dir, "managed", all_skills, include_root=False)
    if workspace_dir:
        ws_skills = workspace_dir / ".openclaw" / "skills"
        if ws_skills.exists():
            _load_skills_to_map(ws_skills, "workspace", all_skills, include_root=True)
    
    # Find skill
    entry = all_skills.get(skill_name)
    
    if not entry:
        print(f"Skill not found: {skill_name}")
        return 1
    
    # Build eligibility context
    eligibility = build_eligibility_context()
    
    # Check eligibility
    eligible = should_include_skill(entry, config, eligibility)
    
    print(f"Skill: {skill_name}")
    print(f"Eligible: {'✓ Yes' if eligible else '✗ No'}")
    print()
    
    if entry.skill.metadata and entry.skill.metadata.requires:
        requires = entry.skill.metadata.requires
        
        if requires.bins:
            print("Required binaries:")
            for bin_name in requires.bins:
                found = bin_name in eligibility.available_bins
                status = "✓" if found else "✗"
                print(f"  {status} {bin_name}")
        
        if requires.any_bins:
            print("Required binaries (any):")
            any_found = any(b in eligibility.available_bins for b in requires.any_bins)
            for bin_name in requires.any_bins:
                found = bin_name in eligibility.available_bins
                status = "✓" if found else "✗"
                print(f"  {status} {bin_name}")
            if any_found:
                print("  (at least one found)")
        
        if requires.env:
            print("Required environment variables:")
            for env_var in requires.env:
                found = env_var in eligibility.env_vars
                status = "✓" if found else "✗"
                print(f"  {status} {env_var}")
    
    return 0 if eligible else 1


def skills_install_command(skill_name: str, config: dict | None = None, workspace_dir: Path | None = None) -> int:
    """
    Install skill dependencies.
    
    Args:
        skill_name: Name of skill to install
        config: Configuration
        workspace_dir: Workspace directory
        
    Returns:
        Exit code
    """
    bundled_dir = get_default_bundled_skills_dir()
    managed_dir = get_default_managed_skills_dir()
    
    # Load all skills
    from openclaw.agents.skills.loader import _load_skills_to_map
    
    all_skills = {}
    if bundled_dir:
        _load_skills_to_map(bundled_dir, "bundled", all_skills, include_root=False)
    if managed_dir:
        _load_skills_to_map(managed_dir, "managed", all_skills, include_root=False)
    if workspace_dir:
        ws_skills = workspace_dir / ".openclaw" / "skills"
        if ws_skills.exists():
            _load_skills_to_map(ws_skills, "workspace", all_skills, include_root=True)
    
    # Find skill
    entry = all_skills.get(skill_name)
    
    if not entry:
        print(f"Skill not found: {skill_name}")
        return 1
    
    skill = entry.skill
    
    if not skill.metadata or not skill.metadata.install:
        print(f"Skill {skill_name} has no installation specifications.")
        return 0
    
    print(f"Installing dependencies for skill: {skill_name}")
    print()
    
    # Run installation
    success, errors = asyncio.run(install_skill_dependencies(skill))
    
    if success:
        print()
        print(f"✓ Successfully installed dependencies for {skill_name}")
        return 0
    else:
        print()
        print(f"✗ Failed to install some dependencies for {skill_name}:")
        for error in errors:
            print(f"  - {error}")
        return 1


__all__ = [
    "skills_list_command",
    "skills_info_command",
    "skills_check_command",
    "skills_install_command",
]
