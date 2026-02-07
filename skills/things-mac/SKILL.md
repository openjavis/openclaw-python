---
name: things-mac
description: Things 3 task manager integration for macOS
version: 1.0.0
author: ClawdBot
tags: [things, tasks, productivity, macos]
requires_bins: [osascript]
requires_env: []
requires_config: []
os: [darwin]
---

# Things 3 Integration

Integrate with Things 3 task manager on macOS.

## Available Tools

- **bash**: Execute AppleScript commands
- **web_fetch**: Use Things URL scheme

## Things URL Scheme

Things supports URL commands: `things:///`

### Add Task
```
things:///add?title=Task%20Title&notes=Task%20notes&when=today
```

### Add to List
```
things:///add?title=Task&list=Work
```

### Show Project
```
things:///show?id={project_id}
```

## AppleScript Commands

### Create Task
```applescript
osascript -e 'tell application "Things3"
    make new to do with properties {name:"Task Title", notes:"Notes"}
end tell'
```

### List Today's Tasks
```applescript
osascript -e 'tell application "Things3"
    name of to dos of list "Today"
end tell'
```

## Usage Examples

User: "Add task to buy groceries"
1. Open Things URL with things:///add
2. Or use AppleScript

User: "Show my tasks for today"
1. Use AppleScript to query Today list
2. Parse and format results

User: "Create project for new client"
1. Use AppleScript to create project
2. Add tasks if specified

## Environment

**macOS only** - requires Things 3 app installed

## Tips

- Use URL scheme for simple additions
- Use AppleScript for complex queries
- Things uses natural language dates ("today", "tomorrow", "next week")
