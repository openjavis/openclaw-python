# New Features Quick Start Guide

## Overview

This guide shows how to use the newly implemented features in openclaw-python.

---

## 1. Using the New Agent System

### Basic Agent Usage

```python
from openclaw.agents.agent import Agent
from openclaw.agents.providers import GeminiProvider
from openclaw.agents.tools.bash import BashTool

# Create provider
provider = GeminiProvider("gemini-3-pro-preview")

# Create agent with tools
agent = Agent(
    provider=provider,
    tools=[BashTool()],
    model="google/gemini-3-pro-preview"
)

# Subscribe to events
def handle_text(event):
    print(event.payload["delta"], end="", flush=True)

agent.on("text_delta", handle_text)

# Run agent
messages = await agent.prompt("List files in current directory")
```

### With Event Streaming

```python
# Subscribe to all events
agent.on("turn_start", lambda e: print(f"\n🔄 Turn {e.payload['turn_number']} started"))
agent.on("tool_execution_start", lambda e: print(f"\n🔧 Executing {e.payload['tool_name']}"))
agent.on("turn_end", lambda e: print("\n✅ Turn completed"))

# Run agent
await agent.prompt("Complex task here")
```

### Steering and Follow-up

```python
# Start long-running task
task = asyncio.create_task(agent.prompt("Long task"))

# Interrupt with steering message
agent.steer("STOP! Change direction")

# Queue follow-up
agent.follow_up("After this, do something else")
```

---

## 2. Using the Cron System

### Creating Scheduled Jobs

```python
from openclaw.cron import CronService
from openclaw.cron.types import (
    EverySchedule,
    CronSchedule,
    AtSchedule,
    AgentTurnPayload,
    SystemEventPayload,
    CronDelivery
)
from pathlib import Path

# Initialize cron service
cron_dir = Path.home() / ".openclaw" / "cron"
cron = CronService(
    store_path=cron_dir / "jobs.json",
    log_dir=cron_dir / "runs"
)
cron.start()

# Add interval-based job (every 24 hours)
job1 = cron.add(
    name="Daily Report",
    schedule=EverySchedule(interval_ms=86400000),  # 24 hours
    payload=AgentTurnPayload(
        prompt="Generate a daily summary report",
        model="google/gemini-3-pro-preview"
    ),
    session_target="isolated",
    delivery=CronDelivery(
        channel="telegram",
        target="123456789",  # Chat ID
        best_effort=True
    )
)

# Add cron expression job
job2 = cron.add(
    name="Morning Briefing",
    schedule=CronSchedule(
        expression="0 9 * * *",  # Daily at 9 AM
        timezone="UTC"
    ),
    payload=AgentTurnPayload(prompt="Good morning briefing")
)

# Add one-time job
job3 = cron.add(
    name="Reminder",
    schedule=AtSchedule(timestamp="2026-02-11T15:00:00Z"),
    payload=SystemEventPayload(text="Meeting reminder!"),
    session_target="main",
    delete_after_run=True
)
```

### Managing Jobs

```python
# List all jobs
jobs = cron.list()
for job in jobs:
    print(f"{job.name}: Next run at {job.state.next_run_ms}")

# Run job immediately
await cron.run_now("job-id-here")

# Update job
cron.update("job-id", enabled=False)

# Remove job
cron.remove("job-id")

# Get service status
status = cron.get_status()
print(f"Running: {status['running']}, Jobs: {status['job_count']}")
```

---

## 3. Using the Pairing System

### In Channel Implementation

```python
from openclaw.pairing import (
    upsert_channel_pairing_request,
    approve_channel_pairing_code,
    read_channel_allow_from_store
)
from openclaw.pairing.messages import (
    format_pairing_request_message,
    format_approval_notification
)

# In your channel's message handler
async def handle_message(channel_id: str, sender_id: str, message: str):
    # Check if sender is authorized
    allowlist = read_channel_allow_from_store(channel_id)
    
    if sender_id not in allowlist:
        # Create pairing request
        result = upsert_channel_pairing_request(channel_id, sender_id)
        
        # Send pairing message to user
        pairing_msg = format_pairing_request_message(
            code=result["code"],
            channel=channel_id,
            id_label="user ID"
        )
        await send_message(sender_id, pairing_msg)
        return  # Don't process message
    
    # User is authorized, process message
    await process_authorized_message(message)
```

### CLI Commands for Approval

```bash
# List pending pairing requests
openclaw pairing list telegram

# Approve a pairing code
openclaw pairing approve telegram ABC12345 --notify

# View allowlist
openclaw pairing allowlist telegram
```

### Programmatic Approval

```python
# Approve pairing code
result = approve_channel_pairing_code("telegram", "ABC12345")

if result:
    print(f"Approved user: {result['id']}")
    
    # Optionally notify user
    notification = format_approval_notification(
        sender_id=result['id'],
        channel="telegram"
    )
    await send_message(result['id'], notification)
```

---

## 4. Session Tree with Branching

### Using Session Trees

```python
from openclaw.agents.session_tree import SessionTree
from pathlib import Path

# Create session tree
session_path = Path.home() / ".openclaw" / "sessions" / "my-session.jsonl"
tree = SessionTree(session_path)

# Append messages
msg1 = tree.append_message(
    role="user",
    content="Hello",
    parent_id=None  # Root message
)

msg2 = tree.append_message(
    role="assistant",
    content="Hi there!",
    parent_id=msg1.id
)

# Fork conversation
fork_id = tree.fork(from_entry_id=msg1.id, label="alternative")

# Continue on fork
msg3 = tree.append_message(
    role="assistant",
    content="Different response",
    parent_id=fork_id
)

# Get branch
branch = tree.get_branch(msg3.id)
print(f"Branch has {len(branch)} messages")

# Export messages
messages = tree.export_messages(msg3.id)
```

---

## 5. Complete Integration Example

### Full Gateway Setup

```python
import asyncio
from pathlib import Path
from openclaw.agents.agent import Agent
from openclaw.agents.providers import GeminiProvider
from openclaw.agents.tools.registry import ToolRegistry
from openclaw.cron import CronService
from openclaw.gateway.cron_integration import setup_cron_callbacks

async def main():
    # Setup provider
    provider = GeminiProvider("gemini-3-pro-preview")
    
    # Setup tools
    tool_registry = ToolRegistry(auto_register=True)
    tools = tool_registry.list_tools()
    
    # Setup cron
    cron_dir = Path.home() / ".openclaw" / "cron"
    cron = CronService(
        store_path=cron_dir / "jobs.json",
        log_dir=cron_dir / "runs"
    )
    
    # Wire up callbacks
    setup_cron_callbacks(
        cron_service=cron,
        provider=provider,
        tools=tools,
        session_manager=None,  # Add your session manager
        channel_registry=None   # Add your channel registry
    )
    
    # Start cron
    cron.start()
    
    # Create agent
    agent = Agent(provider=provider, tools=tools)
    
    # Use agent
    result = await agent.prompt("Create a scheduled daily report")
    
    print("System ready!")
    
    # Keep running
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 6. Configuration Examples

### Cron Job Config (jobs.json)

```json
{
  "version": 1,
  "jobs": [
    {
      "id": "daily-report",
      "name": "Daily Report",
      "enabled": true,
      "schedule": {
        "type": "cron",
        "expression": "0 9 * * *",
        "timezone": "UTC"
      },
      "session_target": "isolated",
      "wake_mode": "now",
      "payload": {
        "kind": "agentTurn",
        "prompt": "Generate daily report",
        "model": "google/gemini-3-pro-preview"
      },
      "delivery": {
        "channel": "telegram",
        "target": "123456789",
        "best_effort": true
      }
    }
  ]
}
```

### Pairing AllowFrom (telegram-allowFrom.json)

```json
{
  "version": 1,
  "entries": [
    "user123",
    "user456",
    "@username"
  ]
}
```

---

## 7. Event System Reference

### Available Events

```python
from openclaw.agents.events import AgentEventType

# Agent lifecycle
AgentEventType.AGENT_START       # Agent started
AgentEventType.AGENT_END         # Agent finished

# Turn lifecycle
AgentEventType.TURN_START        # Turn started
AgentEventType.TURN_END          # Turn ended

# Message lifecycle
AgentEventType.MESSAGE_START     # Message started
AgentEventType.MESSAGE_UPDATE    # Message updated (streaming)
AgentEventType.MESSAGE_END       # Message ended

# Tool execution
AgentEventType.TOOL_EXECUTION_START    # Tool started
AgentEventType.TOOL_EXECUTION_UPDATE   # Tool progress
AgentEventType.TOOL_EXECUTION_END      # Tool finished

# Thinking/reasoning
AgentEventType.THINKING_START    # Thinking started
AgentEventType.THINKING_DELTA    # Thinking delta
AgentEventType.THINKING_END      # Thinking ended

# Streaming
AgentEventType.TEXT_DELTA        # Text delta
AgentEventType.TOOLCALL_START    # Tool call started
AgentEventType.TOOLCALL_DELTA    # Tool call argument delta
AgentEventType.TOOLCALL_END      # Tool call ended
```

### Event Handlers

```python
# Sync handler
def on_text(event):
    print(event.payload["delta"])

agent.on("text_delta", on_text)

# Async handler
async def on_tool(event):
    await do_something_async()

agent.on("tool_execution_start", on_tool)

# One-time handler
agent.once("agent_end", lambda e: print("Done!"))
```

---

## 8. Error Handling

### Agent Errors

```python
try:
    messages = await agent.prompt("Task")
except Exception as e:
    print(f"Agent error: {e}")
```

### Cron Errors

```python
# Jobs track errors automatically
job = cron.get("job-id")
if job.state.last_status == "error":
    print(f"Last error: {job.state.last_error}")
```

### Pairing Errors

```python
from openclaw.pairing import approve_channel_pairing_code

result = approve_channel_pairing_code("telegram", "INVALID")
if result is None:
    print("Code not found or expired")
```

---

## 9. Debugging

### Enable Debug Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("openclaw")
logger.setLevel(logging.DEBUG)
```

### Check Cron Status

```python
status = cron.get_status()
print(f"Timer running: {status['timer_status']}")
print(f"Next fire: {status['timer_status']['next_fire_ms']}")
```

### Inspect Session Tree

```python
tree_structure = tree.get_tree_structure()
print(f"Total entries: {tree_structure['total_entries']}")
print(f"Roots: {len(tree_structure['roots'])}")
print(f"Labels: {tree_structure['labels']}")
```

---

## 10. Production Checklist

### Before Deployment

- [ ] Configure all channel tokens
- [ ] Set up cron jobs in `~/.openclaw/cron/jobs.json`
- [ ] Configure pairing allowlists
- [ ] Set secure file permissions (0o600 for sensitive files)
- [ ] Enable logging
- [ ] Test agent with your tools
- [ ] Test cron job execution
- [ ] Test pairing workflow
- [ ] Configure backup strategy for session trees

### Monitoring

- Monitor cron run logs: `~/.openclaw/cron/runs/*.jsonl`
- Check agent event streams
- Review session tree growth
- Monitor pairing requests

---

## Support

For issues or questions:
1. Check `IMPLEMENTATION_SUMMARY.md` for architecture details
2. Review plan file for design decisions
3. Check logs in `~/.openclaw/logs/`

---

**Last Updated:** February 10, 2026
