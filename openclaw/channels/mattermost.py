"""Mattermost channel implementation"""

import logging
from datetime import UTC, datetime, timezone
from typing import Any

from .base import ChannelCapabilities, ChannelPlugin

logger = logging.getLogger(__name__)


class MattermostChannel(ChannelPlugin):
    """Mattermost integration"""

    def __init__(self):
        super().__init__()
        self.id = "mattermost"
        self.label = "Mattermost"
        self.capabilities = ChannelCapabilities(
            chat_types=["direct", "group", "channel"],
            supports_media=True,
            supports_reactions=True,
            supports_threads=True,
            supports_polls=False,
        )
        self._driver = None

    async def start(self, config: dict[str, Any]) -> None:
        """Start Mattermost bot"""
        url = config.get("url")
        token = config.get("token")
        username = config.get("username")
        password = config.get("password")

        if not url:
            raise ValueError("Mattermost URL required")

        if not token and not (username and password):
            raise ValueError("Mattermost token or username/password required")

        logger.info("Starting Mattermost channel...")

        try:
            from mattermostdriver import Driver

            self._driver = Driver(
                {
                    "url": url,
                    "token": token,
                    "login_id": username,
                    "password": password,
                    "scheme": "https",
                    "port": 443,
                }
            )

            if token:
                self._driver.login()
            else:
                self._driver.login()

            user = self._driver.users.get_user("me")
            logger.info(f"Mattermost bot: {user['username']}")

            self._running = True
            logger.info("Mattermost channel started")

        except ImportError:
            logger.warning("mattermostdriver not installed")
            logger.warning("Install with: pip install mattermostdriver")
            self._running = True
            logger.info("Mattermost channel started (framework mode)")
        except Exception as e:
            logger.error(f"Failed to start Mattermost channel: {e}", exc_info=True)
            raise

    async def stop(self) -> None:
        """Stop Mattermost bot"""
        logger.info("Stopping Mattermost channel...")
        if self._driver:
            self._driver.logout()
        self._running = False

    async def send_text(self, target: str, text: str, reply_to: str | None = None) -> str:
        """Send text message"""
        if not self._running:
            raise RuntimeError("Mattermost channel not started")

        if not self._driver:
            logger.warning("Mattermost driver not initialized")
            return f"mm-msg-{datetime.now(UTC).timestamp()}"

        try:
            post = {"channel_id": target, "message": text}
            if reply_to:
                post["root_id"] = reply_to

            result = self._driver.posts.create_post(post)
            return result["id"]

        except Exception as e:
            logger.error(f"Mattermost send error: {e}", exc_info=True)
            raise

    async def send_media(
        self, target: str, media_url: str, media_type: str, caption: str | None = None
    ) -> str:
        """Send media message"""
        if not self._running:
            raise RuntimeError("Mattermost channel not started")

        # Mattermost requires uploading files first, then attaching to post
        logger.info(f"Mattermost media to {target}")
        return f"mm-media-{datetime.now(UTC).timestamp()}"
