---
name: apple-notes
description: Apple Notes integration for macOS/iOS
version: 1.0.0
author: ClawdBot
tags: [apple, notes, macos, ios]
requires_bins: [osascript]
requires_env: []
requires_config: []
os: [darwin]
---

# Apple Notes Integration

Integrate with Apple Notes on macOS using AppleScript.

## Available Tools

- **bash**: Execute osascript commands

## AppleScript Commands

### Create Note
```applescript
osascript -e 'tell application "Notes"
    make new note at folder "Notes" with properties {name:"Title", body:"Content"}
end tell'
```

### List Notes
```applescript
osascript -e 'tell application "Notes"
    name of every note
end tell'
```

### Read Note
```applescript
osascript -e 'tell application "Notes"
    get body of note "Note Title"
end tell'
```

### Search Notes
```applescript
osascript -e 'tell application "Notes"
    name of notes whose body contains "search term"
end tell'
```

## Usage Examples

User: "Create a note about the meeting"
1. Format note title and content
2. Execute osascript with bash tool
3. Confirm creation

User: "Show my recent notes"
1. List notes with osascript
2. Parse output
3. Present formatted list

User: "Find notes containing 'project'"
1. Search with osascript
2. Parse matching notes
3. Present results

## Platform

**macOS only** - requires osascript (built-in on macOS)

## Limitations

- Requires Notes.app to be installed
- Cannot access password-protected notes
- Formatting may be limited
