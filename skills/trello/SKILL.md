---
name: trello
description: Trello board and card management
version: 1.0.0
author: ClawdBot
tags: [trello, productivity, project-management]
requires_bins: []
requires_env: [TRELLO_API_KEY, TRELLO_TOKEN]
requires_config: []
---

# Trello Integration

Manage Trello boards, lists, and cards.

## Available Tools

- **web_fetch**: Access Trello REST API

## Trello API

Base URL: `https://api.trello.com/1/`

Authentication: `?key={API_KEY}&token={TOKEN}`

### Common Operations

#### Get My Boards
```
GET https://api.trello.com/1/members/me/boards?key={API_KEY}&token={TOKEN}
```

#### Get Board Lists
```
GET https://api.trello.com/1/boards/{board_id}/lists
```

#### Get Cards in List
```
GET https://api.trello.com/1/lists/{list_id}/cards
```

#### Create Card
```
POST https://api.trello.com/1/cards
Body: {
  "name": "Card title",
  "desc": "Card description",
  "idList": "list_id"
}
```

#### Update Card
```
PUT https://api.trello.com/1/cards/{card_id}
Body: {"name": "New title", "desc": "New description"}
```

#### Move Card
```
PUT https://api.trello.com/1/cards/{card_id}
Body: {"idList": "new_list_id"}
```

## Usage Examples

User: "Show my Trello boards"
1. Fetch from /1/members/me/boards
2. Parse and format board list

User: "Add a card to my TODO list"
1. Search for board and list
2. Create card with POST /1/cards

User: "Move card X to Done"
1. Find card by name
2. Find "Done" list
3. Update card's idList

## Environment Setup

```bash
export TRELLO_API_KEY="your_api_key"
export TRELLO_TOKEN="your_token"
```

Get credentials from: https://trello.com/power-ups/admin

## Tips

- Board IDs can be found in board URLs
- List IDs require API call to get
- Cards support markdown in descriptions
- Labels, due dates, and attachments available
