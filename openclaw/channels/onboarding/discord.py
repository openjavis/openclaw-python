"""
Discord channel onboarding adapter (aligned with TypeScript discord.ts)
"""
from __future__ import annotations

import logging
from typing import Any

from .types import ChannelOnboardingAdapter, ChannelOnboardingStatus, DmPolicy

logger = logging.getLogger(__name__)


class DiscordOnboardingAdapter(ChannelOnboardingAdapter):
    """Onboarding adapter for Discord channel"""
    
    def __init__(self):
        super().__init__("discord")
    
    async def get_status(self, config: dict[str, Any]) -> ChannelOnboardingStatus:
        """Check Discord configuration status"""
        channels = config.get("channels", {})
        discord_config = channels.get("discord", {})
        
        has_token = bool(discord_config.get("token") or discord_config.get("botToken"))
        enabled = discord_config.get("enabled", False)
        dm_policy = discord_config.get("dmPolicy", "off")
        allow_from = discord_config.get("allowFrom", [])
        
        # Check for issues
        issues = []
        if enabled and not has_token:
            issues.append("Discord bot token missing")
        
        if dm_policy == "allowlist" and not allow_from:
            issues.append("Allowlist is empty")
        
        return ChannelOnboardingStatus(
            configured=has_token,
            enabled=enabled,
            has_token=has_token,
            dm_policy=dm_policy,
            issues=issues if issues else None,
        )
    
    async def configure(
        self,
        config: dict[str, Any],
        prompter: Any,
    ) -> dict[str, Any]:
        """Interactive Discord configuration"""
        
        # Show help
        await self._show_token_help(prompter)
        
        # Prompt for bot token
        token = await prompter.text(
            message="Enter Discord bot token",
            placeholder="MTA...",
            validate=lambda v: None if v and len(v) > 50 else "Token required"
        )
        
        # Update config
        channels = config.get("channels", {})
        discord_config = channels.get("discord", {})
        
        discord_config["enabled"] = True
        discord_config["token"] = token
        discord_config["dmPolicy"] = "off"  # Start with off
        
        channels["discord"] = discord_config
        config["channels"] = channels
        
        logger.info("Discord configured with bot token")
        
        return config
    
    async def configure_dm_policy(
        self,
        config: dict[str, Any],
        prompter: Any,
        account_id: str | None = None,
    ) -> dict[str, Any]:
        """Configure Discord DM policy"""
        
        # Show help
        await self._show_user_id_help(prompter)
        
        # Prompt for DM policy
        policy_choice = await prompter.select(
            message="Discord DM policy",
            choices=[
                {"value": "off", "label": "Off - no DMs allowed"},
                {"value": "allowlist", "label": "Allowlist - specific users only"},
                {"value": "open", "label": "Open - anyone can DM (careful!)"},
            ]
        )
        
        dm_policy: DmPolicy = policy_choice["value"]  # type: ignore
        
        # Update config
        channels = config.get("channels", {})
        discord_config = channels.get("discord", {})
        
        discord_config["dmPolicy"] = dm_policy
        
        # If allowlist, prompt for user IDs
        if dm_policy == "allowlist":
            user_ids = await prompter.text(
                message="Discord user IDs (comma-separated)",
                placeholder="123456789012345678, 987654321098765432",
                validate=lambda v: None if v and v.strip() else "At least one user ID required"
            )
            
            # Parse user IDs
            parsed_ids = [
                uid.strip()
                for uid in str(user_ids).split(",")
                if uid.strip()
            ]
            
            discord_config["allowFrom"] = parsed_ids
        elif dm_policy == "open":
            discord_config["allowFrom"] = ["*"]
        else:
            discord_config.pop("allowFrom", None)
        
        channels["discord"] = discord_config
        config["channels"] = channels
        
        logger.info(f"Discord DM policy set to: {dm_policy}")
        
        return config
    
    async def validate_token(self, token: str) -> bool:
        """Validate Discord bot token format"""
        # Discord tokens are typically 70+ characters
        # Format: base64.timestamp.hmac
        
        if not token or len(token) < 50:
            return False
        
        # Discord tokens often start with certain patterns
        # but format can change, so just check length
        return True
    
    async def _show_token_help(self, prompter: Any) -> None:
        """Show help for obtaining Discord bot token"""
        help_text = """
        Discord Bot Token Setup:
        
        1. Go to https://discord.com/developers/applications
        2. Click "New Application"
        3. Go to "Bot" section in sidebar
        4. Click "Reset Token" and copy the token
        5. Enable "Message Content Intent" under Privileged Gateway Intents
        6. Invite bot to your server using OAuth2 URL generator
        
        Required permissions:
        - Read Messages/View Channels
        - Send Messages
        - Read Message History
        
        Tip: You can also set DISCORD_BOT_TOKEN environment variable
        
        Docs: https://docs.openclaw.ai/channels/discord
        """
        
        await prompter.note(help_text.strip(), "Discord Setup")
    
    async def _show_user_id_help(self, prompter: Any) -> None:
        """Show help for finding Discord user IDs"""
        help_text = """
        Finding Discord User IDs:
        
        1. Enable Developer Mode in Discord:
           User Settings > App Settings > Advanced > Developer Mode
        
        2. Right-click on any user and select "Copy ID"
        
        3. Or check bot logs when users message:
           openclaw logs --follow
        
        User IDs are 18-digit numbers (e.g., 123456789012345678)
        """
        
        await prompter.note(help_text.strip(), "Discord User IDs")
    
    def get_help_text(self) -> str:
        """Get help text for Discord setup"""
        return """
        Discord Channel Setup:
        
        1. Create a bot application at discord.com/developers
        2. Get the bot token from the Bot section
        3. Enable Message Content Intent
        4. Invite bot to your server
        5. Configure DM policy (off/allowlist/open)
        
        See: https://docs.openclaw.ai/channels/discord
        """
