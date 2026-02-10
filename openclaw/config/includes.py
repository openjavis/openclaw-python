"""Config include directive resolution (matches TypeScript includes.ts)"""

import os
from pathlib import Path
from typing import Any, Callable


class CircularIncludeError(Exception):
    """Raised when a circular include is detected"""
    pass


class ConfigIncludeError(Exception):
    """Raised when an include directive fails"""
    pass


def resolve_config_includes(
    obj: Any,
    config_path: str,
    read_file: Callable[[str], str],
    parse_json: Callable[[str], Any],
    visited: set[str] | None = None,
) -> Any:
    """
    Resolve @include directives in config object.
    
    Supports:
    - "@include": "path/to/file.json" - include entire file
    - "@include": ["file1.json", "file2.json"] - merge multiple files
    
    Args:
        obj: Config object (dict, list, or primitive)
        config_path: Path to current config file (for relative resolution)
        read_file: Function to read file content
        parse_json: Function to parse JSON/JSON5
        visited: Set of visited paths (for circular detection)
    
    Returns:
        Config object with includes resolved
    
    Raises:
        CircularIncludeError: If circular include detected
        ConfigIncludeError: If include fails
    """
    if visited is None:
        visited = set()
    
    config_dir = os.path.dirname(os.path.abspath(config_path))
    
    # Handle dict with @include directive
    if isinstance(obj, dict):
        if "@include" in obj:
            include_value = obj["@include"]
            
            # Single include
            if isinstance(include_value, str):
                include_paths = [include_value]
            # Multiple includes
            elif isinstance(include_value, list):
                include_paths = include_value
            else:
                raise ConfigIncludeError(
                    f"@include must be string or array, got {type(include_value).__name__}"
                )
            
            # Merge all included files
            merged = {}
            for include_path in include_paths:
                # Resolve relative path
                if not os.path.isabs(include_path):
                    include_path = os.path.join(config_dir, include_path)
                
                include_path = os.path.abspath(include_path)
                
                # Check for circular includes
                if include_path in visited:
                    raise CircularIncludeError(
                        f"Circular include detected: {include_path}"
                    )
                
                # Mark as visited
                new_visited = visited | {include_path}
                
                # Read and parse included file
                try:
                    content = read_file(include_path)
                    included = parse_json(content)
                except FileNotFoundError as e:
                    raise ConfigIncludeError(
                        f"Include file not found: {include_path}"
                    ) from e
                except Exception as e:
                    raise ConfigIncludeError(
                        f"Failed to parse include {include_path}: {e}"
                    ) from e
                
                # Recursively resolve includes in the included file
                included = resolve_config_includes(
                    included,
                    include_path,
                    read_file,
                    parse_json,
                    new_visited,
                )
                
                # Merge into result
                if isinstance(included, dict):
                    merged.update(included)
                else:
                    # If included file is not a dict, replace entire config
                    return included
            
            # Merge remaining keys from current object (excluding @include)
            for key, value in obj.items():
                if key != "@include":
                    if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                        # Deep merge dicts
                        merged[key] = {**merged[key], **value}
                    else:
                        # Override
                        merged[key] = value
            
            return merged
        
        # No @include directive, recursively process nested values
        result = {}
        for key, value in obj.items():
            result[key] = resolve_config_includes(
                value,
                config_path,
                read_file,
                parse_json,
                visited,
            )
        return result
    
    # Handle list
    if isinstance(obj, list):
        return [
            resolve_config_includes(item, config_path, read_file, parse_json, visited)
            for item in obj
        ]
    
    # Primitives pass through
    return obj
