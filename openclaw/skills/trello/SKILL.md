---
name: trello
description: "Trello board, list, and card management"
user-invocable: true
metadata:
  openclaw:
    emoji: "📋"
    homepage: "https://trello.com"
    requires:
      env: ["TRELLO_KEY", "TRELLO_TOKEN"]
---

# Trello Management Skill

Manage Trello boards, lists, and cards using the Trello API.

## Prerequisites

- Trello API Key (`TRELLO_KEY`)
- Trello Token (`TRELLO_TOKEN`)
- Get credentials: https://trello.com/app-key

## Common Operations

### Get Boards

```bash
curl "https://api.trello.com/1/members/me/boards?key=$TRELLO_KEY&token=$TRELLO_TOKEN"
```

### Get Lists on Board

```bash
curl "https://api.trello.com/1/boards/{board_id}/lists?key=$TRELLO_KEY&token=$TRELLO_TOKEN"
```

### Create Card

```bash
curl -X POST "https://api.trello.com/1/cards" \
  -d "key=$TRELLO_KEY" \
  -d "token=$TRELLO_TOKEN" \
  -d "idList={list_id}" \
  -d "name=Card Title" \
  -d "desc=Card Description"
```

### Get Cards on List

```bash
curl "https://api.trello.com/1/lists/{list_id}/cards?key=$TRELLO_KEY&token=$TRELLO_TOKEN"
```

### Update Card

```bash
curl -X PUT "https://api.trello.com/1/cards/{card_id}" \
  -d "key=$TRELLO_KEY" \
  -d "token=$TRELLO_TOKEN" \
  -d "name=Updated Title"
```

### Move Card

```bash
curl -X PUT "https://api.trello.com/1/cards/{card_id}" \
  -d "key=$TRELLO_KEY" \
  -d "token=$TRELLO_TOKEN" \
  -d "idList={new_list_id}"
```

### Add Comment

```bash
curl -X POST "https://api.trello.com/1/cards/{card_id}/actions/comments" \
  -d "key=$TRELLO_KEY" \
  -d "token=$TRELLO_TOKEN" \
  -d "text=Comment text"
```

## Tips

- Board/list/card IDs are in URLs
- Use labels for organization
- Checklists: `/cards/{id}/checklists`
- Attachments: `/cards/{id}/attachments`
- Members: `/cards/{id}/members`

## Workflows

### Create Task Workflow

1. Get board ID
2. Get list ID for "To Do" list
3. Create card in list
4. Add checklist if needed
5. Assign members

### Move Task Through Pipeline

1. Get card ID
2. Get target list ID
3. Update card's `idList`
4. Add comment about move

## Error Handling

- Check API key and token are valid
- Verify IDs exist
- Rate limit: 100 requests per 10 seconds
