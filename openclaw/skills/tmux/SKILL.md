---
name: tmux
description: "Control tmux sessions, windows, and panes"
user-invocable: true
metadata:
  openclaw:
    emoji: "🖥️"
    homepage: "https://github.com/tmux/tmux"
    requires:
      bins: ["tmux"]
    install:
      - kind: brew
        formula: tmux
        os: ["darwin", "linux"]
---

# tmux Control Skill

Control tmux sessions, windows, and panes. This skill helps you manage terminal multiplexing.

## Prerequisites

- `tmux` must be installed
- At least one tmux session should be running

## Session Management

```bash
# List sessions
tmux list-sessions

# Create new session
tmux new-session -s <name>

# Attach to session
tmux attach-session -t <name>

# Kill session
tmux kill-session -t <name>

# Rename session
tmux rename-session -t <old> <new>
```

## Window Management

```bash
# List windows
tmux list-windows -t <session>

# Create new window
tmux new-window -t <session>: -n <name>

# Select window
tmux select-window -t <session>:<window>

# Kill window
tmux kill-window -t <session>:<window>
```

## Pane Management

```bash
# List panes
tmux list-panes -t <session>:<window>

# Split window horizontally
tmux split-window -h -t <session>:<window>

# Split window vertically
tmux split-window -v -t <session>:<window>

# Select pane
tmux select-pane -t <session>:<window>.<pane>

# Kill pane
tmux kill-pane -t <session>:<window>.<pane>
```

## Sending Commands

**MOST IMPORTANT: Use `send-keys` to execute commands in tmux panes**

```bash
# Send command to pane (with Enter)
tmux send-keys -t <session>:<window>.<pane> "command" Enter

# Send keys without Enter
tmux send-keys -t <session>:<window>.<pane> "text"

# Send literal keys
tmux send-keys -t <session>:<window>.<pane> -l "text with spaces"
```

### Examples

```bash
# Run a command in session 0, window 0, pane 0
tmux send-keys -t 0:0.0 "ls -la" Enter

# Start a long-running process
tmux send-keys -t myserver:0.0 "npm run dev" Enter

# Type text without executing
tmux send-keys -t editor:0.0 "// TODO: implement this"

# Clear the pane
tmux send-keys -t 0:0.0 C-c  # Send Ctrl-C
tmux send-keys -t 0:0.0 "clear" Enter
```

## Capture Pane Output

```bash
# Capture pane content
tmux capture-pane -t <session>:<window>.<pane> -p

# Capture last N lines
tmux capture-pane -t <session>:<window>.<pane> -p -S -<N>

# Capture to file
tmux capture-pane -t <session>:<window>.<pane> -p > output.txt
```

## Display Message

```bash
# Show message to user
tmux display-message -t <session> "Message text"
```

## Tips

- Target format: `<session>:<window>.<pane>` (e.g., `0:0.0`, `myapp:1.2`)
- Session names can be numeric IDs or names
- Use `-t` flag to specify targets
- `send-keys` is the primary way to interact with running processes
- Always append `Enter` to execute commands
- Use `C-c` to send Ctrl-C (interrupt)

## Common Use Cases

### Running Development Servers

```bash
# Start dev server in tmux
tmux send-keys -t dev:0.0 "cd ~/project && npm start" Enter
```

### Monitoring Logs

```bash
# Tail logs in tmux pane
tmux send-keys -t logs:0.0 "tail -f /var/log/app.log" Enter
```

### Interactive Applications

```bash
# Start interactive app
tmux send-keys -t app:0.0 "python interactive.py" Enter

# Send input to app
tmux send-keys -t app:0.0 "user input" Enter
```

## Error Handling

- Check if session exists: `tmux has-session -t <name>`
- List all sessions: `tmux list-sessions`
- If command fails, verify tmux is running and session exists
