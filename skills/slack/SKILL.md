---
name: slack
description: Advanced Slack workspace operations
version: 1.0.0
author: ClawdBot
tags: [slack, communication, workplace]
requires_bins: []
requires_env: [SLACK_BOT_TOKEN]
requires_config: []
---

# Slack Advanced Operations

Advanced Slack operations beyond basic messaging.

## Available Tools

- **message**: Send messages to Slack channels
- **slack_actions**: Slack-specific operations
- **web_fetch**: Access Slack Web API

## Slack Web API

Base URL: `https://slack.com/api/`

### Common Operations

#### Post Message
```
POST https://slack.com/api/chat.postMessage
Headers:
  Authorization: Bearer {SLACK_BOT_TOKEN}
Body: {
  "channel": "C1234567890",
  "text": "Message text",
  "blocks": [...]
}
```

#### Upload File
```
POST https://slack.com/api/files.upload
Body: {
  "channels": "C1234567890",
  "content": "file content",
  "filename": "file.txt"
}
```

#### List Channels
```
GET https://slack.com/api/conversations.list
```

#### Get Channel History
```
GET https://slack.com/api/conversations.history?channel={channel_id}
```

#### Add Reaction
```
POST https://slack.com/api/reactions.add
Body: {
  "channel": "C1234567890",
  "timestamp": "1234567890.123456",
  "name": "thumbsup"
}
```

## Block Kit

Slack supports rich message formatting with Block Kit:

```python
blocks = [
    {
        "type": "section",
        "text": {"type": "mrkdwn", "text": "*Bold text*"}
    },
    {
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {"type": "plain_text", "text": "Click Me"},
                "action_id": "button_click"
            }
        ]
    }
]
```

## Usage Examples

User: "Send a formatted message to #general"
1. Build blocks with Block Kit
2. POST to chat.postMessage

User: "Upload this file to Slack"
1. Read file content
2. POST to files.upload

User: "List all channels in workspace"
1. GET conversations.list
2. Format and present

## Environment Setup

```bash
export SLACK_BOT_TOKEN="xoxb-..."
```

Get token from: https://api.slack.com/apps

## Required Scopes

- `chat:write` - Send messages
- `files:write` - Upload files
- `channels:read` - List channels
- `reactions:write` - Add reactions
