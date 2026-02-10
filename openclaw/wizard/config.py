"""Configuration wizards."""

from __future__ import annotations

from typing import Optional


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


def configure_telegram_enhanced() -> dict:
    """Configure Telegram with DM policy and environment variable support"""
    import os
    
    # Check environment variable
    env_token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    token = None
    if env_token:
        use_env = input("Use TELEGRAM_BOT_TOKEN from environment? [Y/n]: ").strip().lower()
        if use_env != "n":
            token = env_token
            print("✓ Using token from environment")
    
    if not token:
        print("\nGet your bot token from @BotFather on Telegram:")
        print("  1. Open Telegram and search for @BotFather")
        print("  2. Send /newbot and follow instructions")
        print("  3. Copy the bot token\n")
        token = input("Telegram bot token: ").strip()
    
    if not token:
        return {}
    
    # DM policy
    print("\nDM Policy (who can message your bot):")
    print("  1. Open - Allow all users")
    print("  2. Pairing - Require approval (recommended)")
    print("  3. Allowlist - Specific users only")
    
    policy_choice = input("Choose DM policy [2]: ").strip()
    if policy_choice == "1":
        dm_policy = "open"
    elif policy_choice == "3":
        dm_policy = "allowlist"
    else:
        dm_policy = "pairing"
    
    config = {
        "enabled": True,
        "bot_token": token,
        "dm_policy": dm_policy,
    }
    
    # Allowlist
    if dm_policy == "allowlist":
        print("\nEnter allowed Telegram user IDs (comma-separated)")
        print("Find your ID by messaging the bot and checking logs")
        allow_from = input("Allowed user IDs: ").strip()
        if allow_from:
            config["allow_from"] = [x.strip() for x in allow_from.split(",")]
    
    return config


def configure_discord_enhanced() -> dict:
    """Configure Discord with enhanced options"""
    import os
    
    # Check environment variable
    env_token = os.getenv("DISCORD_BOT_TOKEN")
    
    token = None
    if env_token:
        use_env = input("Use DISCORD_BOT_TOKEN from environment? [Y/n]: ").strip().lower()
        if use_env != "n":
            token = env_token
            print("✓ Using token from environment")
    
    if not token:
        print("\nGet your bot token from Discord Developer Portal:")
        print("  1. Go to https://discord.com/developers/applications")
        print("  2. Create a new application or select existing")
        print("  3. Go to Bot section and copy the token\n")
        token = input("Discord bot token: ").strip()
    
    if not token:
        return {}
    
    # DM policy
    print("\nDM Policy:")
    print("  1. Open - Allow all users")
    print("  2. Pairing - Require approval (recommended)")
    
    policy_choice = input("Choose DM policy [2]: ").strip()
    dm_policy = "open" if policy_choice == "1" else "pairing"
    
    return {
        "enabled": True,
        "bot_token": token,
        "dm_policy": dm_policy,
    }


async def configure_channels() -> dict:
    """Configure chat channels.
    
    Returns:
        Channel configuration
    """
    print("\n" + "=" * 60)
    print("Channel Configuration")
    print("=" * 60)
    print("\nWhich messaging channels would you like to configure?")
    print("(You can add more later with: openclaw channels add)\n")
    
    channels = {}
    
    # Telegram
    setup_telegram = input("Configure Telegram? [Y/n]: ").strip().lower()
    if setup_telegram != "n":
        tg_config = configure_telegram_enhanced()
        if tg_config:
            channels["telegram"] = tg_config
            print("✓ Telegram configured\n")
    
    # Discord
    setup_discord = input("Configure Discord? [y/N]: ").strip().lower()
    if setup_discord == "y":
        dc_config = configure_discord_enhanced()
        if dc_config:
            channels["discord"] = dc_config
            print("✓ Discord configured\n")
    
    # Slack
    setup_slack = input("Configure Slack? [y/N]: ").strip().lower()
    if setup_slack == "y":
        env_token = os.getenv("SLACK_BOT_TOKEN")
        token = env_token if env_token else input("Slack bot token: ").strip()
        if token:
            channels["slack"] = {
                "enabled": True,
                "bot_token": token,
                "dm_policy": "pairing",
            }
            print("✓ Slack configured\n")
    
    return channels
