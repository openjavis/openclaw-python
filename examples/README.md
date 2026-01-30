# ClawdBot Examples

Complete examples demonstrating ClawdBot features.

## Prerequisites

```bash
# Install dependencies
poetry install

# Set API key
export ANTHROPIC_API_KEY='your-key-here'
# or
export OPENAI_API_KEY='your-key-here'
```

## Examples

### 1. Basic Agent (`01_basic_agent.py`)

Learn how to:
- Create an AgentRuntime
- Create a Session
- Send messages and process responses

```bash
poetry run python examples/01_basic_agent.py
```

### 2. Agent with Tools (`02_with_tools.py`)

Learn how to:
- Load and configure tools
- Set tool permissions
- Handle tool calls
- View metrics

```bash
poetry run python examples/02_with_tools.py
```

### 3. Monitoring (`03_monitoring.py`)

Learn how to:
- Setup health checks
- Collect metrics
- Export to Prometheus format

```bash
poetry run python examples/03_monitoring.py
```

### 4. API Server (`04_api_server.py`)

Learn how to:
- Start REST API server
- Use health endpoints
- Use agent chat API

```bash
poetry run python examples/04_api_server.py

# Then in another terminal:
curl http://localhost:8000/health
curl http://localhost:8000/docs
```

### 5. Telegram Bot (`05_telegram_bot.py`)

Learn how to:
- Setup Telegram channel
- Connect agent to Telegram
- Handle automatic reconnection

```bash
export TELEGRAM_BOT_TOKEN='your-bot-token'
poetry run python examples/05_telegram_bot.py
```

## Quick Reference

### Creating an Agent

```python
from openclaw.agents.runtime import AgentRuntime
from openclaw.agents.session import Session

runtime = AgentRuntime(model="anthropic/claude-sonnet-4-20250514")
session = Session("my-session", Path("./workspace"))

async for event in runtime.run_turn(session, "Hello!"):
    if event.type == "assistant":
        print(event.data.get("delta", {}).get("text", ""))
```

### Using Tools

```python
from openclaw.agents.tools.bash import BashTool
from openclaw.agents.tools.base import ToolConfig, ToolPermission

tool = BashTool()
tool.configure(ToolConfig(
    timeout_seconds=30.0,
    allowed_permissions={ToolPermission.EXECUTE}
))

async for event in runtime.run_turn(session, "List files", tools=[tool]):
    ...
```

### Starting API Server

```python
from openclaw.api import run_api_server

await run_api_server(host="0.0.0.0", port=8000)
```

## Troubleshooting

### API Key Error

Make sure your API key is set:
```bash
echo $ANTHROPIC_API_KEY  # Should not be empty
```

### Import Error

Make sure you're in the project directory and dependencies are installed:
```bash
cd openclaw-python
poetry install
```

### Telegram Bot Not Connecting

1. Verify bot token is correct
2. Check network connectivity
3. Look at log output for errors

## More Information

- [Main README](../README.md)
- [API Documentation](http://localhost:8000/docs) (when server running)
- [Contributing](../CONTRIBUTING.md)
