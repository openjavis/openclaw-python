"""
Slack channel onboarding adapter (aligned with TypeScript slack.ts)
"""
from __future__ import annotations

import logging
from typing import Any

from .types import ChannelOnboardingAdapter, ChannelOnboardingStatus, DmPolicy

logger = logging.getLogger(__name__)


class SlackOnboardingAdapter(ChannelOnboardingAdapter):
    """Onboarding adapter for Slack channel"""
    
    def __init__(self):
        super().__init__("slack")
    
    async def get_status(self, config: dict[str, Any]) -> ChannelOnboardingStatus:
        """Check Slack configuration status"""
        channels = config.get("channels", {})
        slack_config = channels.get("slack", {})
        
        has_token = bool(slack_config.get("token") or slack_config.get("botToken"))
        enabled = slack_config.get("enabled", False)
        dm_policy = slack_config.get("dmPolicy", "off")
        allow_from = slack_config.get("allowFrom", [])
        
        # Check for issues
        issues = []
        if enabled and not has_token:
            issues.append("Slack bot token missing")
        
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
        """Interactive Slack configuration"""
        
        # Show help
        await self._show_token_help(prompter)
        
        # Prompt for bot token
        token = await prompter.text(
            message="Enter Slack bot token",
            placeholder="xoxb-...",
            validate=lambda v: None if v and v.startswith("xoxb-") else "Token must start with xoxb-"
        )
        
        # Update config
        channels = config.get("channels", {})
        slack_config = channels.get("slack", {})
        
        slack_config["enabled"] = True
        slack_config["token"] = token
        slack_config["dmPolicy"] = "off"  # Start with off
        
        channels["slack"] = slack_config
        config["channels"] = channels
        
        logger.info("Slack configured with bot token")
        
        return config
    
    async def configure_dm_policy(
        self,
        config: dict[str, Any],
        prompter: Any,
        account_id: str | None = None,
    ) -> dict[str, Any]:
        """Configure Slack DM policy"""
        
        # Show help
        await self._show_user_id_help(prompter)
        
        # Prompt for DM policy
        policy_choice = await prompter.select(
            message="Slack DM policy",
            choices=[
                {"value": "off", "label": "Off - no DMs allowed"},
                {"value": "allowlist", "label": "Allowlist - specific users only"},
                {"value": "open", "label": "Open - anyone can DM (careful!)"},
            ]
        )
        
        dm_policy: DmPolicy = policy_choice["value"]  # type: ignore
        
        # Update config
        channels = config.get("channels", {})
        slack_config = channels.get("slack", {})
        
        slack_config["dmPolicy"] = dm_policy
        
        # If allowlist, prompt for user IDs
        if dm_policy == "allowlist":
            user_ids = await prompter.text(
                message="Slack user IDs (comma-separated)",
                placeholder="U01234ABCDE, U98765FGHIJ",
                validate=lambda v: None if v and v.strip() else "At least one user ID required"
            )
            
            # Parse user IDs
            parsed_ids = [
                uid.strip()
                for uid in str(user_ids).split(",")
                if uid.strip()
            ]
            
            slack_config["allowFrom"] = parsed_ids
        elif dm_policy == "open":
            slack_config["allowFrom"] = ["*"]
        else:
            slack_config.pop("allowFrom", None)
        
        channels["slack"] = slack_config
        config["channels"] = channels
        
        logger.info(f"Slack DM policy set to: {dm_policy}")
        
        return config
    
    async def validate_token(self, token: str) -> bool:
        """Validate Slack bot token format"""
        # Slack bot tokens start with "xoxb-"
        # App tokens start with "xapp-"
        # User tokens start with "xoxp-"
        
        if not token:
            return False
        
        return token.startswith(("xoxb-", "xapp-"))
    
    async def _show_token_help(self, prompter: Any) -> None:
        """Show help for obtaining Slack bot token"""
        help_text = """
        Slack Bot Token Setup:
        
        1. Go to https://api.slack.com/apps
        2. Click "Create New App" > "From scratch"
        3. Give your app a name and select workspace
        4. Go to "OAuth & Permissions" in sidebar
        5. Add Bot Token Scopes:
           - chat:write
           - channels:history
           - groups:history
           - im:history
           - mpim:history
        6. Click "Install to Workspace"
        7. Copy the "Bot User OAuth Token" (starts with xoxb-)
        
        Tip: You can also set SLACK_BOT_TOKEN environment variable
        
        Docs: https://docs.openclaw.ai/channels/slack
        """
        
        await prompter.note(help_text.strip(), "Slack Setup")
    
    async def _show_user_id_help(self, prompter: Any) -> None:
        """Show help for finding Slack user IDs"""
        help_text = """
        Finding Slack User IDs:
        
        1. Check bot logs when users message:
           openclaw logs --follow
           Look for user IDs in message events
        
        2. Click on a user's profile in Slack
           Click "..." > "Copy member ID"
        
        3. Use Slack API:
           https://api.slack.com/methods/users.list
        
        User IDs look like: U01234ABCDE (starts with U)
        """
        
        await prompter.note(help_text.strip(), "Slack User IDs")
    
    def get_help_text(self) -> str:
        """Get help text for Slack setup"""
        return """
        Slack Channel Setup:
        
        1. Create a Slack app at api.slack.com/apps
        2. Add required bot token scopes
        3. Install app to your workspace
        4. Get the Bot User OAuth Token (xoxb-)
        5. Configure DM policy (off/allowlist/open)
        
        See: https://docs.openclaw.ai/channels/slack
        """
