"""Onboarding wizard."""

from __future__ import annotations

from pathlib import Path


async def run_onboarding(workspace_dir: Path | None = None) -> dict:
    """Run onboarding wizard.

    Guides user through initial setup.

    Args:
        workspace_dir: Workspace directory

    Returns:
        Configuration dictionary
    """
    print("Welcome to OpenClaw!")
    print("=" * 60)
    print("Let's set up your AI agent.\n")

    config = {}

    # Agent name
    agent_name = input("What should we call your agent? [OpenClaw]: ").strip()
    if not agent_name:
        agent_name = "OpenClaw"
    config["agent_name"] = agent_name

    # Provider
    print("\nAvailable AI providers:")
    print("  1. Anthropic (Claude)")
    print("  2. OpenAI (GPT)")
    print("  3. Google (Gemini)")

    provider_choice = input("Choose provider [1]: ").strip()
    if provider_choice == "2":
        config["provider"] = "openai"
        config["model"] = "gpt-4o"
    elif provider_choice == "3":
        config["provider"] = "google"
        config["model"] = "gemini-2.0-flash-exp"
    else:
        config["provider"] = "anthropic"
        config["model"] = "claude-3-5-sonnet-20241022"

    # API key
    print(f"\nYou'll need an API key for {config['provider']}.")
    api_key = input(f"Enter your {config['provider']} API key: ").strip()
    config["api_key"] = api_key

    # Workspace
    if workspace_dir:
        config["workspace"] = str(workspace_dir)
    else:
        workspace = input("\nWorkspace directory [./workspace]: ").strip()
        config["workspace"] = workspace or "./workspace"

    print("\n" + "=" * 60)
    print("Setup complete!")
    print(f"Agent: {config['agent_name']}")
    print(f"Provider: {config['provider']}")
    print(f"Model: {config['model']}")
    print(f"Workspace: {config['workspace']}")
    print("=" * 60)

    return config
