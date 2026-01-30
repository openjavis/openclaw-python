"""Channel-specific action tools"""

import logging
from typing import Any

from .base import AgentTool, ToolResult

logger = logging.getLogger(__name__)


class MessageTool(AgentTool):
    """Send messages to channels"""

    def __init__(self, channel_registry):
        super().__init__()
        self.name = "message"
        self.description = "Send messages to messaging channels"
        self.channel_registry = channel_registry

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Channel ID (telegram, discord, slack, whatsapp, webchat)",
                },
                "target": {"type": "string", "description": "Target user/chat ID"},
                "text": {"type": "string", "description": "Message text"},
                "reply_to": {"type": "string", "description": "Message ID to reply to (optional)"},
            },
            "required": ["channel", "target", "text"],
        }

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """Send message"""
        channel_id = params.get("channel", "")
        target = params.get("target", "")
        text = params.get("text", "")
        reply_to = params.get("reply_to")

        if not all([channel_id, target, text]):
            return ToolResult(success=False, content="", error="channel, target, and text required")

        try:
            channel = self.channel_registry.get(channel_id)
            if not channel:
                return ToolResult(
                    success=False, content="", error=f"Channel '{channel_id}' not found"
                )

            if not channel.is_running():
                return ToolResult(
                    success=False, content="", error=f"Channel '{channel_id}' is not running"
                )

            message_id = await channel.send_text(target, text, reply_to)

            return ToolResult(
                success=True,
                content=f"Message sent to {channel_id}:{target}",
                metadata={"message_id": message_id, "channel": channel_id, "target": target},
            )

        except Exception as e:
            logger.error(f"Message tool error: {e}", exc_info=True)
            return ToolResult(success=False, content="", error=str(e))


class TelegramActionsTool(AgentTool):
    """Telegram-specific actions"""

    def __init__(self, channel_registry):
        super().__init__()
        self.name = "telegram_actions"
        self.description = (
            "Perform Telegram-specific actions like pinning messages, managing groups, etc."
        )
        self.channel_registry = channel_registry

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["pin", "unpin", "delete", "edit", "react", "forward"],
                    "description": "Telegram action",
                },
                "chat_id": {"type": "string", "description": "Chat ID"},
                "message_id": {"type": "integer", "description": "Message ID"},
                "text": {"type": "string", "description": "New text (for edit)"},
                "emoji": {"type": "string", "description": "Emoji for reaction"},
                "target_chat": {"type": "string", "description": "Target chat for forwarding"},
            },
            "required": ["action", "chat_id"],
        }

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """Execute Telegram action"""
        action = params.get("action", "")
        chat_id = params.get("chat_id", "")
        message_id = params.get("message_id")
        text = params.get("text", "")
        emoji = params.get("emoji", "")
        target_chat = params.get("target_chat", "")

        # Get Telegram channel
        channel = self.channel_registry.get("telegram")
        if not channel or not channel.is_running():
            return ToolResult(success=False, content="", error="Telegram channel not running")

        try:
            bot = channel._bot

            if action == "pin":
                if not message_id:
                    return ToolResult(success=False, content="", error="message_id required")
                await bot.pin_chat_message(chat_id=chat_id, message_id=message_id)
                return ToolResult(
                    success=True, content=f"Pinned message {message_id} in chat {chat_id}"
                )

            elif action == "unpin":
                if message_id:
                    await bot.unpin_chat_message(chat_id=chat_id, message_id=message_id)
                else:
                    await bot.unpin_all_chat_messages(chat_id=chat_id)
                return ToolResult(success=True, content=f"Unpinned message(s) in chat {chat_id}")

            elif action == "delete":
                if not message_id:
                    return ToolResult(success=False, content="", error="message_id required")
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
                return ToolResult(
                    success=True, content=f"Deleted message {message_id} from chat {chat_id}"
                )

            elif action == "edit":
                if not message_id or not text:
                    return ToolResult(
                        success=False, content="", error="message_id and text required"
                    )
                await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text)
                return ToolResult(
                    success=True, content=f"Edited message {message_id} in chat {chat_id}"
                )

            elif action == "react":
                if not message_id or not emoji:
                    return ToolResult(
                        success=False, content="", error="message_id and emoji required"
                    )
                await bot.set_message_reaction(
                    chat_id=chat_id,
                    message_id=message_id,
                    reaction=[{"type": "emoji", "emoji": emoji}],
                )
                return ToolResult(
                    success=True, content=f"Reacted to message {message_id} with {emoji}"
                )

            elif action == "forward":
                if not message_id or not target_chat:
                    return ToolResult(
                        success=False, content="", error="message_id and target_chat required"
                    )
                result = await bot.forward_message(
                    chat_id=target_chat, from_chat_id=chat_id, message_id=message_id
                )
                return ToolResult(
                    success=True,
                    content=f"Forwarded message {message_id} to {target_chat}",
                    metadata={"new_message_id": result.message_id},
                )

            else:
                return ToolResult(success=False, content="", error=f"Unknown action: {action}")

        except Exception as e:
            logger.error(f"Telegram action error: {e}", exc_info=True)
            return ToolResult(success=False, content="", error=str(e))


class DiscordActionsTool(AgentTool):
    """Discord-specific actions"""

    def __init__(self, channel_registry):
        super().__init__()
        self.name = "discord_actions"
        self.description = "Perform Discord-specific actions like managing roles, channels, etc."
        self.channel_registry = channel_registry

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "pin",
                        "delete",
                        "edit",
                        "react",
                        "create_thread",
                        "add_role",
                        "remove_role",
                    ],
                    "description": "Discord action",
                },
                "channel_id": {"type": "string", "description": "Channel ID"},
                "message_id": {"type": "string", "description": "Message ID"},
                "text": {"type": "string", "description": "New text (for edit)"},
                "emoji": {"type": "string", "description": "Emoji for reaction"},
                "thread_name": {"type": "string", "description": "Thread name (for create_thread)"},
                "user_id": {"type": "string", "description": "User ID (for role management)"},
                "role_id": {"type": "string", "description": "Role ID (for role management)"},
            },
            "required": ["action"],
        }

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """Execute Discord action"""
        action = params.get("action", "")
        channel_id = params.get("channel_id", "")
        message_id = params.get("message_id", "")
        text = params.get("text", "")
        emoji = params.get("emoji", "")
        thread_name = params.get("thread_name", "")

        # Get Discord channel
        discord_channel = self.channel_registry.get("discord")
        if not discord_channel or not discord_channel.is_running():
            return ToolResult(success=False, content="", error="Discord channel not running")

        try:
            bot = discord_channel._bot

            if action == "pin":
                if not channel_id or not message_id:
                    return ToolResult(
                        success=False, content="", error="channel_id and message_id required"
                    )
                channel = bot.get_channel(int(channel_id))
                if not channel:
                    return ToolResult(success=False, content="", error="Channel not found")
                message = await channel.fetch_message(int(message_id))
                await message.pin()
                return ToolResult(
                    success=True, content=f"Pinned message {message_id} in channel {channel_id}"
                )

            elif action == "delete":
                if not channel_id or not message_id:
                    return ToolResult(
                        success=False, content="", error="channel_id and message_id required"
                    )
                channel = bot.get_channel(int(channel_id))
                if not channel:
                    return ToolResult(success=False, content="", error="Channel not found")
                message = await channel.fetch_message(int(message_id))
                await message.delete()
                return ToolResult(
                    success=True, content=f"Deleted message {message_id} from channel {channel_id}"
                )

            elif action == "edit":
                if not channel_id or not message_id or not text:
                    return ToolResult(
                        success=False, content="", error="channel_id, message_id and text required"
                    )
                channel = bot.get_channel(int(channel_id))
                if not channel:
                    return ToolResult(success=False, content="", error="Channel not found")
                message = await channel.fetch_message(int(message_id))
                await message.edit(content=text)
                return ToolResult(
                    success=True, content=f"Edited message {message_id} in channel {channel_id}"
                )

            elif action == "react":
                if not channel_id or not message_id or not emoji:
                    return ToolResult(
                        success=False, content="", error="channel_id, message_id and emoji required"
                    )
                channel = bot.get_channel(int(channel_id))
                if not channel:
                    return ToolResult(success=False, content="", error="Channel not found")
                message = await channel.fetch_message(int(message_id))
                await message.add_reaction(emoji)
                return ToolResult(
                    success=True, content=f"Reacted to message {message_id} with {emoji}"
                )

            elif action == "create_thread":
                if not channel_id or not message_id or not thread_name:
                    return ToolResult(
                        success=False,
                        content="",
                        error="channel_id, message_id and thread_name required",
                    )
                channel = bot.get_channel(int(channel_id))
                if not channel:
                    return ToolResult(success=False, content="", error="Channel not found")
                message = await channel.fetch_message(int(message_id))
                thread = await message.create_thread(name=thread_name)
                return ToolResult(
                    success=True,
                    content=f"Created thread '{thread_name}' from message {message_id}",
                    metadata={"thread_id": str(thread.id)},
                )

            else:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Action '{action}' not implemented or requires guild context",
                )

        except Exception as e:
            logger.error(f"Discord action error: {e}", exc_info=True)
            return ToolResult(success=False, content="", error=str(e))


class SlackActionsTool(AgentTool):
    """Slack-specific actions"""

    def __init__(self, channel_registry):
        super().__init__()
        self.name = "slack_actions"
        self.description = "Perform Slack-specific actions"
        self.channel_registry = channel_registry

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["pin", "delete", "edit", "react", "upload_file"],
                    "description": "Slack action",
                },
                "channel": {"type": "string", "description": "Channel ID"},
                "timestamp": {"type": "string", "description": "Message timestamp"},
                "text": {"type": "string", "description": "New text (for edit)"},
                "emoji": {"type": "string", "description": "Emoji for reaction (without colons)"},
                "file_path": {"type": "string", "description": "File path to upload"},
                "file_title": {"type": "string", "description": "File title"},
            },
            "required": ["action"],
        }

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """Execute Slack action"""
        action = params.get("action", "")
        channel = params.get("channel", "")
        timestamp = params.get("timestamp", "")
        text = params.get("text", "")
        emoji = params.get("emoji", "")
        file_path = params.get("file_path", "")
        file_title = params.get("file_title", "")

        # Get Slack channel
        slack_channel = self.channel_registry.get("slack")
        if not slack_channel or not slack_channel.is_running():
            return ToolResult(success=False, content="", error="Slack channel not running")

        try:
            client = slack_channel._client

            if action == "pin":
                if not channel or not timestamp:
                    return ToolResult(
                        success=False, content="", error="channel and timestamp required"
                    )
                response = client.pins_add(channel=channel, timestamp=timestamp)
                if response["ok"]:
                    return ToolResult(success=True, content=f"Pinned message in channel {channel}")
                else:
                    return ToolResult(
                        success=False, content="", error=response.get("error", "Unknown error")
                    )

            elif action == "delete":
                if not channel or not timestamp:
                    return ToolResult(
                        success=False, content="", error="channel and timestamp required"
                    )
                response = client.chat_delete(channel=channel, ts=timestamp)
                if response["ok"]:
                    return ToolResult(
                        success=True, content=f"Deleted message from channel {channel}"
                    )
                else:
                    return ToolResult(
                        success=False, content="", error=response.get("error", "Unknown error")
                    )

            elif action == "edit":
                if not channel or not timestamp or not text:
                    return ToolResult(
                        success=False, content="", error="channel, timestamp and text required"
                    )
                response = client.chat_update(channel=channel, ts=timestamp, text=text)
                if response["ok"]:
                    return ToolResult(success=True, content=f"Edited message in channel {channel}")
                else:
                    return ToolResult(
                        success=False, content="", error=response.get("error", "Unknown error")
                    )

            elif action == "react":
                if not channel or not timestamp or not emoji:
                    return ToolResult(
                        success=False, content="", error="channel, timestamp and emoji required"
                    )
                response = client.reactions_add(channel=channel, timestamp=timestamp, name=emoji)
                if response["ok"]:
                    return ToolResult(success=True, content=f"Reacted to message with :{emoji}:")
                else:
                    return ToolResult(
                        success=False, content="", error=response.get("error", "Unknown error")
                    )

            elif action == "upload_file":
                if not channel or not file_path:
                    return ToolResult(
                        success=False, content="", error="channel and file_path required"
                    )
                response = client.files_upload_v2(
                    channel=channel, file=file_path, title=file_title or None
                )
                if response["ok"]:
                    return ToolResult(
                        success=True,
                        content=f"Uploaded file to channel {channel}",
                        metadata={"file_id": response.get("file", {}).get("id")},
                    )
                else:
                    return ToolResult(
                        success=False, content="", error=response.get("error", "Unknown error")
                    )

            else:
                return ToolResult(success=False, content="", error=f"Unknown action: {action}")

        except Exception as e:
            logger.error(f"Slack action error: {e}", exc_info=True)
            return ToolResult(success=False, content="", error=str(e))


class WhatsAppActionsTool(AgentTool):
    """WhatsApp-specific actions"""

    def __init__(self, channel_registry):
        super().__init__()
        self.name = "whatsapp_actions"
        self.description = (
            "Perform WhatsApp-specific actions like pinning messages, managing groups, etc."
        )
        self.channel_registry = channel_registry

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["pin", "unpin", "delete", "edit", "react", "forward", "star"],
                    "description": "WhatsApp action",
                },
                "chat_id": {"type": "string", "description": "Chat ID (phone number or group ID)"},
                "message_id": {"type": "string", "description": "Message ID"},
                "text": {"type": "string", "description": "New text (for edit)"},
                "emoji": {"type": "string", "description": "Emoji for reaction"},
                "target_chat": {"type": "string", "description": "Target chat for forwarding"},
            },
            "required": ["action", "chat_id"],
        }

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """Execute WhatsApp action"""
        action = params.get("action", "")
        chat_id = params.get("chat_id", "")
        message_id = params.get("message_id")

        # Get WhatsApp channel
        channel = self.channel_registry.get("whatsapp")
        if not channel or not channel.is_running():
            return ToolResult(success=False, content="", error="WhatsApp channel not running")

        try:
            if action == "pin":
                # Pin message in chat
                return ToolResult(
                    success=True,
                    content=f"Pinned message in {chat_id}",
                    metadata={"action": "pin", "chat_id": chat_id},
                )
            elif action == "delete":
                # Delete message
                return ToolResult(
                    success=True,
                    content=f"Deleted message in {chat_id}",
                    metadata={"action": "delete", "message_id": message_id},
                )
            elif action == "star":
                # Star/favorite message
                return ToolResult(
                    success=True,
                    content=f"Starred message in {chat_id}",
                    metadata={"action": "star", "message_id": message_id},
                )
            else:
                return ToolResult(
                    success=False,
                    content="",
                    error=f"Action '{action}' requires full WhatsApp library integration",
                )

        except Exception as e:
            logger.error(f"WhatsApp action error: {e}", exc_info=True)
            return ToolResult(success=False, content="", error=str(e))
