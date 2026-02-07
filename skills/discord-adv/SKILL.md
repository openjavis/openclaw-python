---
name: discord-adv
description: Advanced Discord server and channel management
version: 1.0.0
author: ClawdBot
tags: [discord, community, gaming]
requires_bins: []
requires_env: [DISCORD_BOT_TOKEN]
requires_config: []
---

# Discord Advanced Operations

Advanced Discord operations including server management, roles, channels, and moderation.

## Available Tools

- **message**: Send messages to Discord channels
- **discord_actions**: Discord-specific operations
- **web_fetch**: Access Discord API

## Discord API

Base URL: `https://discord.com/api/v10/`

### Common Operations

#### Send Message
```
POST https://discord.com/api/v10/channels/{channel_id}/messages
Headers:
  Authorization: Bot {DISCORD_BOT_TOKEN}
Body: {
  "content": "Message text",
  "embeds": [...]
}
```

#### Create Channel
```
POST https://discord.com/api/v10/guilds/{guild_id}/channels
Body: {
  "name": "channel-name",
  "type": 0
}
```

#### Add Role
```
PUT https://discord.com/api/v10/guilds/{guild_id}/members/{user_id}/roles/{role_id}
```

#### Create Embed
```python
embed = {
    "title": "Embed Title",
    "description": "Embed description",
    "color": 3447003,  # Blue
    "fields": [
        {"name": "Field 1", "value": "Value 1", "inline": True}
    ],
    "footer": {"text": "Footer text"},
    "timestamp": "2026-01-27T00:00:00Z"
}
```

## Usage Examples

User: "Send an embed to #announcements"
1. Build embed structure
2. POST to channels/{channel_id}/messages

User: "Create a new voice channel"
1. Get guild ID
2. POST to guilds/{guild_id}/channels with type=2

User: "Add moderator role to user"
1. Find role ID
2. PUT to add role

## Environment Setup

```bash
export DISCORD_BOT_TOKEN="Bot ..."
```

Get token from: https://discord.com/developers/applications

## Permissions

Bot needs appropriate permissions:
- Manage Channels
- Manage Roles
- Send Messages
- Embed Links
- Attach Files
