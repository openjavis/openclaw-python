---
name: notion
description: Notion workspace integration for notes, databases, and pages
version: 1.0.0
author: ClawdBot
tags: [notion, notes, productivity]
requires_bins: []
requires_env: [NOTION_API_KEY]
requires_config: []
---

# Notion Integration

Integrate with Notion workspace for managing notes, databases, and pages.

## Available Tools

- **web_fetch**: Access Notion API
- **write_file**: Save content locally
- **read_file**: Read local content

## Notion API Endpoints

Base URL: `https://api.notion.com/v1/`

### Common Operations

#### Search Pages
```
POST https://api.notion.com/v1/search
Headers:
  Authorization: Bearer {NOTION_API_KEY}
  Notion-Version: 2022-06-28
Body: {"query": "search term"}
```

#### Get Page
```
GET https://api.notion.com/v1/pages/{page_id}
```

#### Create Page
```
POST https://api.notion.com/v1/pages
Body: {
  "parent": {"database_id": "..."},
  "properties": {...}
}
```

#### Query Database
```
POST https://api.notion.com/v1/databases/{database_id}/query
```

## Usage Examples

User: "Search my Notion for project notes"
1. Use web_fetch to POST to /v1/search
2. Parse results
3. Present formatted list

User: "Create a new page in my Notion"
1. Ask for page title and content
2. Use web_fetch to POST to /v1/pages
3. Confirm creation

## Environment Setup

Set NOTION_API_KEY:
```bash
export NOTION_API_KEY="secret_xxx..."
```

Get your API key from: https://www.notion.so/my-integrations
