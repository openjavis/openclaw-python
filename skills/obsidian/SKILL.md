---
name: obsidian
description: Obsidian vault integration for markdown notes
version: 1.0.0
author: ClawdBot
tags: [obsidian, notes, markdown, knowledge]
requires_bins: []
requires_env: []
requires_config: []
---

# Obsidian Integration

Manage Obsidian vault notes using file operations.

## Obsidian Vault Structure

Typical vault location:
- macOS: `~/Documents/Obsidian Vault/`
- Linux: `~/Documents/Obsidian Vault/`
- Windows: `C:\Users\{user}\Documents\Obsidian Vault\`

## Available Tools

- **read_file**: Read note content
- **write_file**: Create or update notes
- **edit_file**: Modify existing notes
- **bash**: Search notes with grep/ripgrep
- **web_fetch**: Access Obsidian API (if REST API plugin installed)

## Common Operations

### Search Notes
```bash
rg "search term" ~/Documents/ObsidianVault/
```

### Create Note
```python
# Write to: ~/Documents/ObsidianVault/NewNote.md
content = """---
tags: [tag1, tag2]
created: 2026-01-27
---

# Note Title

Note content here...
"""
write_file(path="~/Documents/ObsidianVault/NewNote.md", content=content)
```

### Update Note
Use edit_file to modify existing notes.

### Link Notes
Obsidian uses `[[Note Name]]` for internal links.

## Frontmatter

Obsidian notes support YAML frontmatter:
```yaml
---
tags: [personal, work]
created: 2026-01-27
updated: 2026-01-27
---
```

## Usage Examples

User: "Create a note about the meeting"
1. Ask for note details
2. Format with frontmatter
3. Write to vault using write_file

User: "Search my notes for Python"
1. Use bash with rg/grep
2. Parse results
3. Present formatted list

User: "Update my daily note"
1. Read current daily note
2. Append new content
3. Write back

## Configuration

Set vault path in your queries or config:
```python
VAULT_PATH = "~/Documents/ObsidianVault/"
```
