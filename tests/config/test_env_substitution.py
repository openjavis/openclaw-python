"""Tests for environment variable substitution in config values."""

import pytest
from openclaw.config.env_substitution import (
    resolve_config_env_vars,
    MissingEnvVarError,
)


def test_simple_substitution():
    """Test basic ${VAR} substitution."""
    env = {'API_KEY': 'secret-123'}
    config = {'apiKey': '${API_KEY}'}
    result = resolve_config_env_vars(config, env)
    assert result == {'apiKey': 'secret-123'}


def test_multiple_vars_in_string():
    """Test multiple ${VAR} in same string."""
    env = {'HOST': 'example.com', 'PORT': '8080'}
    config = {'url': 'http://${HOST}:${PORT}'}
    result = resolve_config_env_vars(config, env)
    assert result == {'url': 'http://example.com:8080'}


def test_nested_substitution():
    """Test substitution in nested objects."""
    env = {'DB_HOST': 'localhost', 'DB_PASS': 'password123'}
    config = {
        'database': {
            'host': '${DB_HOST}',
            'credentials': {
                'password': '${DB_PASS}'
            }
        }
    }
    result = resolve_config_env_vars(config, env)
    assert result == {
        'database': {
            'host': 'localhost',
            'credentials': {
                'password': 'password123'
            }
        }
    }


def test_array_substitution():
    """Test substitution in arrays."""
    env = {'KEY1': 'value1', 'KEY2': 'value2'}
    config = {
        'keys': ['${KEY1}', '${KEY2}', 'static']
    }
    result = resolve_config_env_vars(config, env)
    assert result == {
        'keys': ['value1', 'value2', 'static']
    }


def test_escaped_substitution():
    """Test escaped $${VAR} -> ${VAR}."""
    env = {'API_KEY': 'secret'}
    config = {
        'example': '$${API_KEY}',  # Should not substitute
        'actual': '${API_KEY}'     # Should substitute
    }
    result = resolve_config_env_vars(config, env)
    assert result == {
        'example': '${API_KEY}',
        'actual': 'secret'
    }


def test_missing_env_var_raises():
    """Test that missing env var raises MissingEnvVarError."""
    env = {}
    config = {'apiKey': '${MISSING_VAR}'}
    
    with pytest.raises(MissingEnvVarError) as exc_info:
        resolve_config_env_vars(config, env)
    
    assert exc_info.value.var_name == 'MISSING_VAR'
    assert 'apiKey' in exc_info.value.config_path


def test_empty_env_var_raises():
    """Test that empty env var raises MissingEnvVarError."""
    env = {'EMPTY_VAR': ''}
    config = {'apiKey': '${EMPTY_VAR}'}
    
    with pytest.raises(MissingEnvVarError):
        resolve_config_env_vars(config, env)


def test_invalid_var_name_not_substituted():
    """Test that invalid var names (lowercase, etc.) are not substituted."""
    env = {'lowercase': 'value', 'UPPERCASE': 'value2'}
    config = {
        'invalid1': '${lowercase}',  # lowercase not allowed
        'invalid2': '${123ABC}',      # starts with number
        'valid': '${UPPERCASE}'       # valid
    }
    result = resolve_config_env_vars(config, env)
    assert result['invalid1'] == '${lowercase}'  # Not substituted
    assert result['invalid2'] == '${123ABC}'      # Not substituted
    assert result['valid'] == 'value2'            # Substituted


def test_primitives_pass_through():
    """Test that non-string primitives pass through unchanged."""
    env = {'VAR': 'value'}
    config = {
        'number': 42,
        'float': 3.14,
        'boolean': True,
        'null': None,
        'string': '${VAR}'
    }
    result = resolve_config_env_vars(config, env)
    assert result['number'] == 42
    assert result['float'] == 3.14
    assert result['boolean'] is True
    assert result['null'] is None
    assert result['string'] == 'value'


def test_partial_match_not_substituted():
    """Test that partial matches like $ or ${ without } are not substituted."""
    env = {'VAR': 'value'}
    config = {
        'incomplete1': '${VAR',     # Missing closing }
        'incomplete2': '$VAR',      # Missing {}
        'complete': '${VAR}'        # Complete
    }
    result = resolve_config_env_vars(config, env)
    assert result['incomplete1'] == '${VAR'
    assert result['incomplete2'] == '$VAR'
    assert result['complete'] == 'value'


def test_config_path_in_error():
    """Test that error includes correct config path."""
    env = {}
    config = {
        'level1': {
            'level2': {
                'apiKey': '${MISSING}'
            }
        }
    }
    
    with pytest.raises(MissingEnvVarError) as exc_info:
        resolve_config_env_vars(config, env)
    
    assert 'level1.level2.apiKey' in exc_info.value.config_path


def test_real_world_config():
    """Test realistic config scenario."""
    env = {
        'ANTHROPIC_API_KEY': 'sk-ant-test',
        'TELEGRAM_BOT_TOKEN': '123456:ABC',
        'GATEWAY_PORT': '18789'
    }
    config = {
        'models': {
            'providers': {
                'anthropic': {
                    'apiKey': '${ANTHROPIC_API_KEY}'
                }
            }
        },
        'channels': {
            'telegram': {
                'token': '${TELEGRAM_BOT_TOKEN}'
            }
        },
        'gateway': {
            'port': '${GATEWAY_PORT}'
        }
    }
    
    result = resolve_config_env_vars(config, env)
    
    assert result['models']['providers']['anthropic']['apiKey'] == 'sk-ant-test'
    assert result['channels']['telegram']['token'] == '123456:ABC'
    assert result['gateway']['port'] == '18789'
