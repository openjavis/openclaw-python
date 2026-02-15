---
name: slack
description: "Slack workspace operations and messaging"
user-invocable: true
metadata:
  openclaw:
    emoji: "💬"
    homepage: "https://api.slack.com"
    requires:
      env: ["SLACK_BOT_TOKEN"]
---

# Slack Operations Skill

Interact with Slack workspaces using the Slack API. This skill requires a Slack Bot Token.

## Prerequisites

- Slack Bot Token (`SLACK_BOT_TOKEN` environment variable)
- Bot must be added to channels where it will operate
- Required scopes: `chat:write`, `channels:read`, `users:read`

## Common Operations

### Send Message

```bash
curl -X POST "https://slack.com/api/chat.postMessage" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "C1234567890",
    "text": "Hello, World!"
  }'
```

### List Channels

```bash
curl "https://slack.com/api/conversations.list" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN"
```

### Get Channel Info

```bash
curl "https://slack.com/api/conversations.info?channel=C1234567890" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN"
```

### Send File

```bash
curl -X POST "https://slack.com/api/files.upload" \
  -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
  -F "channels=C1234567890" \
  -F "file=@document.pdf" \
  -F "title=Document"
```

## Tips

- Use channel IDs, not names
- Check API response for errors
- Rate limit: ~1 request per second
- Use blocks for rich formatting
- Test with `/api/auth.test` endpoint

## Error Handling

Common errors:
- `not_authed`: Invalid token
- `channel_not_found`: Invalid channel ID
- `not_in_channel`: Bot not in channel
