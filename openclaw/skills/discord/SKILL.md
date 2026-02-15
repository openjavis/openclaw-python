---
name: discord
description: "Discord server and channel operations"
user-invocable: true
metadata:
  openclaw:
    emoji: "🎮"
    homepage: "https://discord.com/developers"
    requires:
      env: ["DISCORD_BOT_TOKEN"]
---

# Discord Operations Skill

Interact with Discord servers using the Discord API. This skill requires a Discord Bot Token.

## Prerequisites

- Discord Bot Token (`DISCORD_BOT_TOKEN` environment variable)
- Bot must be invited to servers
- Required intents: `GUILD_MESSAGES`, `MESSAGE_CONTENT`

## Common Operations

### Send Message

```bash
curl -X POST "https://discord.com/api/v10/channels/{channel_id}/messages" \
  -H "Authorization: Bot $DISCORD_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Hello, World!"
  }'
```

### Get Channel

```bash
curl "https://discord.com/api/v10/channels/{channel_id}" \
  -H "Authorization: Bot $DISCORD_BOT_TOKEN"
```

### List Guild Channels

```bash
curl "https://discord.com/api/v10/guilds/{guild_id}/channels" \
  -H "Authorization: Bot $DISCORD_BOT_TOKEN"
```

### Create Channel

```bash
curl -X POST "https://discord.com/api/v10/guilds/{guild_id}/channels" \
  -H "Authorization: Bot $DISCORD_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "new-channel",
    "type": 0
  }'
```

## Channel Types

- `0`: Text channel
- `2`: Voice channel
- `4`: Category
- `5`: Announcement channel
- `13`: Stage channel

## Tips

- Use snowflake IDs for all resources
- Rate limit: varies by endpoint
- Use embeds for rich content
- WebSocket gateway for real-time events

## Error Handling

Common errors:
- `401 Unauthorized`: Invalid token
- `403 Forbidden`: Missing permissions
- `404 Not Found`: Invalid ID
- `429 Too Many Requests`: Rate limited
