# Advanced Features Guide

This guide covers advanced features that enhance ClawdBot's capabilities and reliability.

## Table of Contents

1. [Thinking Mode](#thinking-mode)
2. [Auth Profile Rotation](#auth-profile-rotation)
3. [Model Fallback Chains](#model-fallback-chains)
4. [Session Queuing](#session-queuing)
5. [Advanced Context Compaction](#advanced-context-compaction)
6. [Tool Result Formatting](#tool-result-formatting)

---

## Thinking Mode

Extract and display AI reasoning process for better transparency and debugging.

### Modes

- **OFF**: Default, no thinking extraction
- **ON**: Extract thinking, include in final response
- **STREAM**: Stream thinking separately in real-time

### Usage

```python
from clawdbot.agents.runtime import AgentRuntime
from clawdbot.agents.thinking import ThinkingMode

runtime = AgentRuntime(
    model="anthropic/claude-opus-4-5",
    thinking_mode=ThinkingMode.STREAM
)

async for event in runtime.run_turn(session, "Complex question"):
    if event.type == "thinking":
        # Thinking content streamed separately
        print(f"[THINKING]: {event.data['delta']['text']}")
    elif event.type == "assistant":
        # Regular response
        print(event.data['delta']['text'])
```

### Benefits

- See how AI reasons through problems
- Better debugging of unexpected behavior
- Transparency for users
- Improved trust

---

## Auth Profile Rotation

Manage multiple API keys with automatic failover and cooldown tracking.

### Features

- Multiple profiles per provider
- Automatic rotation on failure
- Cooldown period after failures
- Rate limit handling
- Usage tracking

### Usage

```python
from clawdbot.agents.auth import AuthProfile
from clawdbot.agents.runtime import AgentRuntime

profiles = [
    AuthProfile(
        id="anthropic-main",
        provider="anthropic",
        api_key="$ANTHROPIC_API_KEY"  # Use env var
    ),
    AuthProfile(
        id="anthropic-backup",
        provider="anthropic",
        api_key="$ANTHROPIC_API_KEY_2"
    )
]

runtime = AgentRuntime(
    model="anthropic/claude-opus-4-5",
    auth_profiles=profiles
)

# Runtime automatically rotates through profiles on failures
```

### Configuration

```yaml
# config.yaml
agent:
  auth_profiles:
    - id: main-key
      provider: anthropic
      api_key_env: ANTHROPIC_API_KEY
    - id: backup-key
      provider: anthropic
      api_key_env: ANTHROPIC_API_KEY_2
```

### Benefits

- **Resilience**: Continue working if one key fails
- **Rate Limits**: Distribute load across multiple keys
- **Cost Management**: Use different billing accounts
- **Automatic Failover**: No manual intervention needed

---

## Model Fallback Chains

Automatically try backup models when primary model fails.

### Features

- Define fallback sequence
- Automatic switching on errors
- Smart error classification
- Track attempts per model

### Usage

```python
from clawdbot.agents.runtime import AgentRuntime

runtime = AgentRuntime(
    model="anthropic/claude-opus-4-5",
    fallback_models=[
        "anthropic/claude-sonnet-4-5",  # Try if Opus fails
        "openai/gpt-4",                  # Try if Sonnet fails
        "gemini/gemini-pro"              # Last resort
    ]
)

# Runtime automatically tries fallbacks on:
# - Auth errors
# - Rate limits
# - Server errors
# - Model unavailable
```

### Failover Events

```python
async for event in runtime.run_turn(session, message):
    if event.type == "failover":
        print(f"Switched from {event.data['from']} to {event.data['to']}")
        print(f"Reason: {event.data['reason']}")
```

### Benefits

- **High Availability**: Continue working through outages
- **Cost Optimization**: Fall back to cheaper models
- **Provider Diversity**: Don't depend on single provider
- **Better UX**: Users don't see errors

---

## Session Queuing

Prevent concurrent access to the same session and manage global concurrency.

### Features

- Per-session sequential execution
- Global concurrency limiting
- Automatic queue management
- Zero configuration

### Usage

```python
from clawdbot.agents.runtime import AgentRuntime

runtime = AgentRuntime(
    model="anthropic/claude-opus-4-5",
    enable_queuing=True
)

# All requests for the same session are automatically serialized
# Multiple sessions can run concurrently (up to global limit)
```

### Benefits

- **No Race Conditions**: Session state stays consistent
- **Resource Management**: Limit total concurrent requests
- **Automatic**: No manual queue management
- **Per-Session Isolation**: Sessions don't block each other

---

## Advanced Context Compaction

Intelligent message pruning when context window is full.

### Strategies

1. **KEEP_RECENT**: Keep most recent messages
2. **KEEP_IMPORTANT**: Keep system + important messages
3. **SLIDING_WINDOW**: Keep first N + last M messages

### Usage

```python
from clawdbot.agents.compaction import CompactionStrategy
from clawdbot.agents.runtime import AgentRuntime

runtime = AgentRuntime(
    model="anthropic/claude-opus-4-5",
    enable_context_management=True,
    compaction_strategy=CompactionStrategy.KEEP_IMPORTANT
)

# Compaction happens automatically when context is full
```

### Message Importance Scoring

- System messages: 1.0 (always kept)
- Assistant with tools: 0.9 (high priority)
- Assistant text: 0.7
- User messages: 0.6
- Tool results: 0.4 (can be summarized)

### Events

```python
async for event in runtime.run_turn(session, message):
    if event.type == "compaction":
        print(f"Compacted: {event.data['original_tokens']} → {event.data['compacted_tokens']}")
        print(f"Strategy: {event.data['strategy']}")
```

### Benefits

- **Smarter Pruning**: Keep important context
- **Multiple Strategies**: Choose what fits your use case
- **Automatic**: No manual intervention
- **Token-Aware**: Accurate token counting

---

## Tool Result Formatting

Format tool results appropriately for different channels.

### Formats

- **MARKDOWN**: Rich formatting for web/Telegram/Discord
- **PLAIN**: Simple text for SMS/simple channels

### Usage

```python
from clawdbot.agents.formatting import FormatMode
from clawdbot.agents.runtime import AgentRuntime

# For rich channels
runtime_web = AgentRuntime(
    model="anthropic/claude-opus-4-5",
    tool_format=FormatMode.MARKDOWN
)

# For simple channels
runtime_sms = AgentRuntime(
    model="anthropic/claude-opus-4-5",
    tool_format=FormatMode.PLAIN
)
```

### Example Output

**Markdown Format**:
```
### 🔧 Tool: read_file

**Arguments:**
```json
{"path": "config.py"}
```

### ✅ Result: read_file

```python
DEBUG = True
PORT = 8000
```
```

**Plain Format**:
```
[Tool: read_file]
Arguments: {"path": "config.py"}

[SUCCESS] read_file:
DEBUG = True
PORT = 8000
```

### Benefits

- **Channel-Appropriate**: Matches channel capabilities
- **Better UX**: Readable output everywhere
- **Automatic**: Based on tool_format setting
- **Syntax Highlighting**: Code detection in markdown mode

---

## Using Multiple Features Together

Combine features for maximum capability:

```python
from clawdbot.agents.auth import AuthProfile
from clawdbot.agents.compaction import CompactionStrategy
from clawdbot.agents.formatting import FormatMode
from clawdbot.agents.runtime import AgentRuntime
from clawdbot.agents.thinking import ThinkingMode

runtime = AgentRuntime(
    model="anthropic/claude-opus-4-5",
    
    # Enable all features
    thinking_mode=ThinkingMode.STREAM,
    fallback_models=["anthropic/claude-sonnet-4-5", "openai/gpt-4"],
    auth_profiles=[profile1, profile2],
    enable_queuing=True,
    enable_context_management=True,
    compaction_strategy=CompactionStrategy.KEEP_IMPORTANT,
    tool_format=FormatMode.MARKDOWN,
    max_retries=3
)

# All features work together seamlessly!
```

---

## Configuration File

Configure features in `config.yaml`:

```yaml
agent:
  model: anthropic/claude-opus-4-5
  
  # Thinking mode
  thinking_mode: stream
  
  # Fallback chain
  fallback_models:
    - anthropic/claude-sonnet-4-5
    - openai/gpt-4
  
  # Auth profiles
  auth_profiles:
    - id: main
      provider: anthropic
      api_key_env: ANTHROPIC_API_KEY
    - id: backup
      provider: anthropic
      api_key_env: ANTHROPIC_API_KEY_2
  
  # Context management
  context:
    enabled: true
    strategy: keep_important
    max_tokens: 180000
  
  # Queuing
  queuing:
    enabled: true
    max_per_session: 1
    max_global: 10
  
  # Tool formatting
  tool_format: markdown
```

---

## Performance Impact

All features are designed for minimal overhead:

| Feature | Overhead | Notes |
|---------|----------|-------|
| Thinking Mode | <5% | Only when thinking tags present |
| Auth Rotation | <1% | Cached profile lookup |
| Model Fallback | 0% | Only on errors |
| Session Queuing | <2% | Async queue management |
| Context Compaction | <5% | Only when context full |
| Tool Formatting | <3% | Simple string formatting |

**Total Overhead**: <10% in worst case

---

## Testing

All features are thoroughly tested:

```bash
# Run advanced feature tests
uv run pytest tests/test_thinking.py
uv run pytest tests/test_auth_rotation.py
uv run pytest tests/test_failover.py
uv run pytest tests/test_queuing.py
uv run pytest tests/test_compaction.py
uv run pytest tests/test_formatting.py

# Run all tests
uv run pytest tests/
```

---

## Migration Guide

### From Basic Runtime

```python
# Before
runtime = AgentRuntime("anthropic/claude-opus-4-5")

# After (opt-in to features)
runtime = AgentRuntime(
    "anthropic/claude-opus-4-5",
    thinking_mode=ThinkingMode.STREAM,  # Add thinking
    fallback_models=["openai/gpt-4"]     # Add failover
)
```

### Backward Compatibility

All features are **opt-in**. Existing code works without changes:

```python
# This still works exactly as before
runtime = AgentRuntime("anthropic/claude-opus-4-5")
async for event in runtime.run_turn(session, "Hello"):
    print(event.data)
```

---

## Best Practices

### Production Setup

1. **Enable Failover**: Always configure fallback models
2. **Use Auth Rotation**: Have backup API keys
3. **Enable Queuing**: Prevent race conditions
4. **Monitor Thinking**: Use STREAM mode in development
5. **Choose Strategy**: Use KEEP_IMPORTANT for long conversations

### Development Setup

```python
runtime = AgentRuntime(
    model="anthropic/claude-sonnet-4-5",  # Cheaper for dev
    thinking_mode=ThinkingMode.STREAM,    # See reasoning
    enable_queuing=False                   # Faster for testing
)
```

### Production Setup

```python
runtime = AgentRuntime(
    model="anthropic/claude-opus-4-5",
    thinking_mode=ThinkingMode.OFF,       # Better performance
    fallback_models=[...],                 # High availability
    auth_profiles=[...],                   # Key rotation
    enable_queuing=True,                   # Prevent conflicts
    compaction_strategy=CompactionStrategy.KEEP_IMPORTANT
)
```

---

## Troubleshooting

### Thinking Mode Not Working

- Check model supports thinking tags (Claude, GPT-4)
- Verify thinking_mode is not OFF
- Look for `<thinking>` tags in responses

### Fallover Not Triggering

- Check error message matches patterns
- Verify fallback_models configured
- Review logs for failover events

### Queuing Too Slow

- Increase max_concurrent_global
- Disable queuing for single-user apps
- Check for blocked tasks

---

## API Reference

See individual module documentation:
- `clawdbot.agents.thinking`
- `clawdbot.agents.auth`
- `clawdbot.agents.failover`
- `clawdbot.agents.queuing`
- `clawdbot.agents.compaction`
- `clawdbot.agents.formatting`

---

**For more examples, see** `examples/08_advanced_features.py`
