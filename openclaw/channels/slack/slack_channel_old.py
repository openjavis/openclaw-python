"""Slack channel implementation"""

import asyncio
import logging
from typing import Any

from .base import ChannelPlugin, InboundMessage

logger = logging.getLogger(__name__)


class SlackChannel(ChannelPlugin):
    """
    Slack channel plugin.
    
    Provides Slack bot integration using slack_sdk library.
    """
    
    def __init__(self):
        super().__init__()
        self._client = None
        self._socket_client = None
        self._running = False
    
    @property
    def channel_id(self) -> str:
        return "slack"
    
    async def start(self, config: dict[str, Any]) -> None:
        """
        Start Slack bot.
        
        Config:
            token: Slack bot token (from env: SLACK_BOT_TOKEN)
            app_token: Slack app-level token (from env: SLACK_APP_TOKEN)
            allow_from: List of allowed user IDs
        """
        try:
            from slack_sdk import WebClient
            from slack_sdk.socket_mode import SocketModeClient
            from slack_sdk.socket_mode.response import SocketModeResponse
            from slack_sdk.socket_mode.request import SocketModeRequest
        except ImportError:
            logger.error("slack_sdk not installed. Install with: pip install slack_sdk")
            raise
        
        bot_token = config.get("token") or self._get_env_var("SLACK_BOT_TOKEN")
        app_token = config.get("app_token") or self._get_env_var("SLACK_APP_TOKEN")
        
        if not bot_token:
            raise ValueError("Slack bot token not found (set SLACK_BOT_TOKEN)")
        if not app_token:
            raise ValueError("Slack app token not found (set SLACK_APP_TOKEN)")
        
        allow_from = config.get("allow_from", [])
        
        self._client = WebClient(token=bot_token)
        self._socket_client = SocketModeClient(
            app_token=app_token,
            web_client=self._client,
        )
        
        # Handle events
        async def process(client: SocketModeClient, req: SocketModeRequest):
            if req.type == "events_api":
                # Acknowledge the request
                response = SocketModeResponse(envelope_id=req.envelope_id)
                await client.send_socket_mode_response(response)
                
                # Process event
                event = req.payload.get("event", {})
                event_type = event.get("type")
                
                if event_type == "message" and event.get("subtype") is None:
                    # Regular message (not bot message, not edited, etc.)
                    user_id = event.get("user")
                    text = event.get("text", "")
                    channel = event.get("channel")
                    ts = event.get("ts")  # Timestamp serves as message ID
                    
                    # Check allow list
                    if allow_from and user_id not in allow_from:
                        logger.debug(f"Ignoring message from unauthorized user: {user_id}")
                        return
                    
                    # Create inbound message
                    inbound = InboundMessage(
                        message_id=ts,
                        channel_id="slack",
                        sender_id=user_id,
                        text=text,
                        metadata={
                            "channel": channel,
                            "thread_ts": event.get("thread_ts"),
                        },
                    )
                    
                    # Handle message through callback
                    if self.message_callback:
                        await self.message_callback(inbound)
        
        self._socket_client.socket_mode_request_listeners.append(process)
        
        # Start socket mode
        await self._socket_client.connect()
        self._running = True
        
        logger.info("Slack channel started")
    
    async def stop(self) -> None:
        """Stop Slack bot"""
        if self._socket_client:
            await self._socket_client.close()
            self._running = False
        logger.info("Slack channel stopped")
    
    async def send_text(
        self, target: str, text: str, reply_to: str | None = None
    ) -> str:
        """
        Send text message to Slack channel.
        
        Args:
            target: Channel ID (e.g., "C1234567890")
            text: Message text
            reply_to: Thread timestamp to reply in thread
        
        Returns:
            Message timestamp (serves as ID)
        """
        if not self._client:
            raise RuntimeError("Slack channel not started")
        
        # Send message
        kwargs = {
            "channel": target,
            "text": text,
        }
        
        if reply_to:
            kwargs["thread_ts"] = reply_to
        
        response = await asyncio.to_thread(
            self._client.chat_postMessage,
            **kwargs
        )
        
        return response["ts"]
    
    async def send_media(
        self, target: str, media_url: str, media_type: str, caption: str | None = None
    ) -> str:
        """
        Send media (file) to Slack.
        
        Args:
            target: Channel ID
            media_url: URL or path to file
            media_type: Type (photo/video/document)
            caption: Optional caption (initial comment)
        
        Returns:
            File ID
        """
        if not self._client:
            raise RuntimeError("Slack channel not started")
        
        # Upload file
        if media_url.startswith("http"):
            # URL - download first
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(media_url)
                file_content = response.content
        else:
            # Local file
            with open(media_url, "rb") as f:
                file_content = f.read()
        
        # Upload to Slack
        response = await asyncio.to_thread(
            self._client.files_upload_v2,
            channel=target,
            content=file_content,
            filename=media_url.split("/")[-1],
            initial_comment=caption,
        )
        
        return response["file"]["id"]
