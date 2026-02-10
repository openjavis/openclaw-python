"""
Environment variable substitution for config values.

Supports `${VAR_NAME}` syntax in string values, substituted at config load time.
- Only uppercase env vars are matched: `[A-Z_][A-Z0-9_]*`
- Escape with `$${}`  to output literal `${}`
- Missing env vars throw `MissingEnvVarError` with context

Example:
    >>> config = {
    ...     "models": {
    ...         "providers": {
    ...             "anthropic": {
    ...                 "apiKey": "${ANTHROPIC_API_KEY}"
    ...             }
    ...         }
    ...     }
    ... }
    >>> resolved = resolve_config_env_vars(config)
"""

import os
import re
from typing import Any, Dict


ENV_VAR_NAME_PATTERN = re.compile(r'^[A-Z_][A-Z0-9_]*$')


class MissingEnvVarError(Exception):
    """Raised when a referenced environment variable is not set or empty."""
    
    def __init__(self, var_name: str, config_path: str):
        self.var_name = var_name
        self.config_path = config_path
        super().__init__(
            f'Missing env var "{var_name}" referenced at config path: {config_path}'
        )


def _is_plain_object(value: Any) -> bool:
    """Check if value is a plain dictionary (not a custom class)."""
    return isinstance(value, dict) and type(value) is dict


def _substitute_string(value: str, env: Dict[str, str], config_path: str) -> str:
    """
    Substitute ${VAR} environment variable references in a string.
    
    Args:
        value: String value to substitute
        env: Environment variables dictionary
        config_path: Config path for error messages
        
    Returns:
        String with env vars substituted
        
    Raises:
        MissingEnvVarError: If a referenced env var is not set or empty
    """
    if '$' not in value:
        return value
    
    chunks: list[str] = []
    i = 0
    
    while i < len(value):
        char = value[i]
        
        if char != '$':
            chunks.append(char)
            i += 1
            continue
        
        # Check for patterns
        next_char = value[i + 1] if i + 1 < len(value) else None
        after_next = value[i + 2] if i + 2 < len(value) else None
        
        # Escaped: $${VAR} -> ${VAR}
        if next_char == '$' and after_next == '{':
            start = i + 3
            try:
                end = value.index('}', start)
                name = value[start:end]
                if ENV_VAR_NAME_PATTERN.match(name):
                    chunks.append(f'${{{name}}}')
                    i = end + 1
                    continue
            except ValueError:
                pass
        
        # Substitution: ${VAR} -> value
        if next_char == '{':
            start = i + 2
            try:
                end = value.index('}', start)
                name = value[start:end]
                if ENV_VAR_NAME_PATTERN.match(name):
                    env_value = env.get(name)
                    if env_value is None or env_value == '':
                        raise MissingEnvVarError(name, config_path)
                    chunks.append(env_value)
                    i = end + 1
                    continue
            except ValueError:
                pass
        
        # Leave untouched if not a recognized pattern
        chunks.append(char)
        i += 1
    
    return ''.join(chunks)


def _substitute_any(value: Any, env: Dict[str, str], path: str) -> Any:
    """
    Recursively substitute env vars in any value type.
    
    Args:
        value: Value to substitute (string, dict, list, or primitive)
        env: Environment variables dictionary
        path: Current config path for error messages
        
    Returns:
        Value with env vars substituted
    """
    if isinstance(value, str):
        return _substitute_string(value, env, path)
    
    if isinstance(value, list):
        return [
            _substitute_any(item, env, f'{path}[{index}]')
            for index, item in enumerate(value)
        ]
    
    if _is_plain_object(value):
        result: Dict[str, Any] = {}
        for key, val in value.items():
            child_path = f'{path}.{key}' if path else key
            result[key] = _substitute_any(val, env, child_path)
        return result
    
    # Primitives (int, float, bool, None) pass through unchanged
    return value


def resolve_config_env_vars(
    obj: Any,
    env: Dict[str, str] | None = None
) -> Any:
    """
    Resolve ${VAR_NAME} environment variable references in config values.
    
    This function walks through the config object and replaces all ${VAR_NAME}
    patterns with the corresponding environment variable values.
    
    Args:
        obj: The parsed config object (after JSON/JSON5 parse and includes)
        env: Environment variables to use for substitution (defaults to os.environ)
        
    Returns:
        The config object with env vars substituted
        
    Raises:
        MissingEnvVarError: If a referenced env var is not set or empty
        
    Example:
        >>> config = {"apiKey": "${API_KEY}"}
        >>> os.environ['API_KEY'] = 'secret-key'
        >>> resolve_config_env_vars(config)
        {'apiKey': 'secret-key'}
    """
    if env is None:
        env = dict(os.environ)
    
    return _substitute_any(obj, env, '')
