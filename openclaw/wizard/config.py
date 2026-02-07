"""Configuration wizards."""

from __future__ import annotations


async def configure_agent() -> dict:
    """Configure agent settings.

    Returns:
        Agent configuration
    """
    print("Agent Configuration")
    print("=" * 60)

    config = {}

    # Think level
    print("\nDefault think level:")
    print("  1. Low (fast, brief)")
    print("  2. Medium (balanced)")
    print("  3. High (thorough, detailed)")

    think_choice = input("Choose think level [2]: ").strip()
    if think_choice == "1":
        config["think_level"] = "low"
    elif think_choice == "3":
        config["think_level"] = "high"
    else:
        config["think_level"] = "medium"

    # Workspace
    workspace = input("\nWorkspace directory [./workspace]: ").strip()
    config["workspace"] = workspace or "./workspace"

    return config


async def configure_channels() -> dict:
    """Configure chat channels.

    Returns:
        Channel configuration
    """
    print("Channel Configuration")
    print("=" * 60)
    print("\nAvailable channels:")
    print("  1. Telegram")
    print("  2. Discord")
    print("  3. Slack")
    print("  4. WhatsApp")

    channels = {}

    # Telegram
    setup_telegram = input("\nSetup Telegram? [y/N]: ").strip().lower()
    if setup_telegram == "y":
        bot_token = input("Telegram bot token: ").strip()
        if bot_token:
            channels["telegram"] = {"bot_token": bot_token}

    # Discord
    setup_discord = input("\nSetup Discord? [y/N]: ").strip().lower()
    if setup_discord == "y":
        bot_token = input("Discord bot token: ").strip()
        if bot_token:
            channels["discord"] = {"bot_token": bot_token}

    return channels
