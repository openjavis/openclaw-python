"""
A2UI Protocol (v0.8) definitions.

Agent-to-UI declarative rendering protocol.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Any


# Supported action keys
A2UI_ACTION_KEYS = [
    "beginRendering",
    "surfaceUpdate",
    "dataModelUpdate",
    "deleteSurface",
    "createSurface"
]


@dataclass
class Component:
    """UI component"""
    type: str
    props: dict[str, Any] | None = None
    children: list[Component] | None = None


@dataclass
class SurfaceUpdate:
    """v0.8 surfaceUpdate action"""
    action: Literal["surfaceUpdate"] = "surfaceUpdate"
    surface_id: str | None = None
    components: list[Component] | None = None


@dataclass
class BeginRendering:
    """v0.8 beginRendering action"""
    action: Literal["beginRendering"] = "beginRendering"
    surface_id: str | None = None
    root: str | None = None


@dataclass
class CreateSurface:
    """v0.9 createSurface action (NOT supported - reject)"""
    action: Literal["createSurface"] = "createSurface"


@dataclass
class DeleteSurface:
    """deleteSurface action"""
    action: Literal["deleteSurface"] = "deleteSurface"
    surface_id: str | None = None


@dataclass
class DataModelUpdate:
    """dataModelUpdate action"""
    action: Literal["dataModelUpdate"] = "dataModelUpdate"
    updates: dict[str, Any] | None = None


def validate_a2ui_jsonl(jsonl: str) -> tuple[bool, list[str]]:
    """
    Validate A2UI JSONL.
    
    Rules:
    - Only v0.8 supported
    - v0.9 createSurface rejected
    - Each line must be valid JSON
    - Each action must have valid key
    
    Args:
        jsonl: JSONL string to validate
        
    Returns:
        Tuple of (is_valid, errors)
    """
    import json
    
    errors = []
    lines = jsonl.strip().split('\n')
    
    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        
        try:
            action = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append(f"Line {i}: Invalid JSON - {e}")
            continue
        
        if not isinstance(action, dict):
            errors.append(f"Line {i}: Action must be an object")
            continue
        
        action_type = action.get('action')
        if not action_type:
            errors.append(f"Line {i}: Missing 'action' field")
            continue
        
        if action_type not in A2UI_ACTION_KEYS:
            errors.append(f"Line {i}: Unknown action '{action_type}'")
            continue
        
        # Reject v0.9 createSurface
        if action_type == "createSurface":
            errors.append(f"Line {i}: createSurface (v0.9) not supported, use v0.8")
            continue
    
    return (len(errors) == 0, errors)


__all__ = [
    "A2UI_ACTION_KEYS",
    "Component",
    "SurfaceUpdate",
    "BeginRendering",
    "CreateSurface",
    "DeleteSurface",
    "DataModelUpdate",
    "validate_a2ui_jsonl",
]
