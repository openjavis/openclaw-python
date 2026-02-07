---
name: summarize
description: Summarize text, articles, and conversations
version: 1.0.0
author: ClawdBot
tags: [summarization, text-processing]
requires_bins: []
requires_env: []
requires_config: []
---

# Text Summarization

Summarize long texts, articles, web pages, and conversations.

## Available Tools

- **web_fetch**: Fetch article content
- **read_file**: Read local files
- **sessions_history**: Get conversation history

## Summarization Strategies

### 1. Extract Key Points
- Identify main ideas
- Bullet point format
- Focus on actionable items

### 2. Executive Summary
- 2-3 paragraph overview
- Include context and conclusions
- Professional tone

### 3. TL;DR
- Single paragraph
- Casual tone
- Essential information only

## Usage Examples

User: "Summarize this article: {URL}"
1. Fetch article with web_fetch
2. Extract main content
3. Generate summary with key points

User: "Give me a TL;DR of our conversation"
1. Get conversation history with sessions_history
2. Identify key topics and decisions
3. Create concise summary

User: "Summarize this document"
1. Read file content
2. Identify structure (sections, headings)
3. Summarize each section
4. Provide overall summary

## Best Practices

- Ask user for preferred format (bullets, paragraph, TL;DR)
- Include word count if requested
- Preserve critical details (names, dates, numbers)
- Maintain original tone for technical content
- Highlight action items in meeting summaries

## Output Formats

### Bullet Points
```
Key Points:
- Point 1
- Point 2
- Point 3
```

### Executive Summary
```
Summary:
{2-3 paragraphs covering main themes}

Key Takeaways:
- Takeaway 1
- Takeaway 2
```

### Meeting Summary
```
Meeting Summary
Date: {date}
Participants: {names}

Discussion:
- Topic 1
- Topic 2

Decisions:
- Decision 1
- Decision 2

Action Items:
- [ ] Task 1 - Owner
- [ ] Task 2 - Owner
```
