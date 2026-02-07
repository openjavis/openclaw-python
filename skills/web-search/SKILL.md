---
name: web-search
description: Search the web for information
version: 1.0.0
author: ClawdBot
tags: [web, search, information]
requires_bins: []
requires_env: []
---

# Web Search

Search the web for information and fetch content from URLs.

## Tools Available

- **web_search**: Search for information (if available)
- **web_fetch**: Fetch content from specific URLs

## Search Strategies

1. **Direct URL fetch**: If user provides a URL, use web_fetch directly
2. **Search query**: Use web_search to find relevant pages
3. **Multiple sources**: Fetch multiple URLs for comprehensive info

## Best Practices

- Verify information from multiple sources
- Cite sources in your response
- Summarize content clearly
- Extract key information relevant to the query

## Example Queries

- "Search for Python asyncio tutorial"
- "What's on the Python homepage?"
- "Find documentation for FastAPI"
- "Get the latest news about AI"
