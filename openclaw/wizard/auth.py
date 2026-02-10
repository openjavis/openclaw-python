"""
Authentication configuration for onboarding wizard
Handles API key collection, OAuth flows, and auth profile management
"""

import os
from pathlib import Path


def get_provider_help_text(provider: str) -> str | None:
    """Get help text for obtaining API keys for different providers"""
    help_texts = {
        "anthropic": "Get your key from: https://console.anthropic.com/settings/keys",
        "openai": "Get your key from: https://platform.openai.com/api-keys",
        "gemini": "Get your key from: https://makersuite.google.com/app/apikey",
        "google": "Get your key from: https://makersuite.google.com/app/apikey",
        "openrouter": "Get your key from: https://openrouter.ai/keys",
    }
    return help_texts.get(provider.lower())


def prompt_api_key_simple(provider: str) -> str:
    """Prompt for API key with provider-specific help (simple version)"""
    help_text = get_provider_help_text(provider)
    
    if help_text:
        print(f"\n{help_text}\n")
    
    api_key = input(f"Enter your {provider.title()} API key: ").strip()
    
    if not api_key:
        raise ValueError("API key cannot be empty")
    
    return api_key


def check_env_api_key(provider: str) -> str | None:
    """Check if API key exists in environment variables"""
    env_vars = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "gemini": "GOOGLE_API_KEY",
        "google": "GOOGLE_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
    }
    
    env_var = env_vars.get(provider.lower())
    if env_var:
        return os.getenv(env_var)
    
    return None


def save_auth_to_env(provider: str, api_key: str) -> None:
    """Save API key to .env file"""
    env_vars = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "gemini": "GOOGLE_API_KEY",
        "google": "GOOGLE_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
    }
    
    env_var = env_vars.get(provider.lower())
    if not env_var:
        print(f"Warning: Unknown provider {provider}, cannot save to .env")
        return
    
    # Find .env file
    env_path = Path.cwd() / ".env"
    
    # Read existing content
    existing_lines = []
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            existing_lines = f.readlines()
    
    # Check if key already exists
    key_exists = False
    for i, line in enumerate(existing_lines):
        if line.strip().startswith(f"{env_var}="):
            existing_lines[i] = f"{env_var}={api_key}\n"
            key_exists = True
            break
    
    # Add if doesn't exist
    if not key_exists:
        existing_lines.append(f"\n# {provider.title()} API Key\n")
        existing_lines.append(f"{env_var}={api_key}\n")
    
    # Write back
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(existing_lines)
    
    print(f"API key saved to {env_path}")


def configure_auth(provider: str) -> dict:
    """Configure authentication for a provider"""
    
    # Check if API key exists in environment
    env_key = check_env_api_key(provider)
    
    if env_key:
        use_env = input(f"Found {provider.upper()} API key in environment. Use it? [Y/n]: ").strip().lower()
        if use_env != "n":
            return {
                "provider": provider,
                "api_key": env_key,
                "source": "environment",
            }
    
    # Prompt for API key
    api_key = prompt_api_key_simple(provider)
    
    # Ask if user wants to save to .env
    save_to_env = input("Save API key to .env file? [Y/n]: ").strip().lower()
    if save_to_env != "n":
        try:
            save_auth_to_env(provider, api_key)
        except Exception as e:
            print(f"Warning: Could not save to .env: {e}")
    
    return {
        "provider": provider,
        "api_key": api_key,
        "source": "manual",
    }
