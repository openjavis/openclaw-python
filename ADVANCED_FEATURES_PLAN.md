# Advanced Features Implementation Plan

## Overview
This document outlines the implementation plan for advanced features based on TypeScript pi-agent analysis.

## Architecture Design

### 1. File Structure
```
clawdbot/agents/
├── runtime.py (existing - will be extended)
├── auth/
│   ├── __init__.py
│   ├── profile.py          # Auth profile management
│   └── rotation.py         # Profile rotation with cooldown
├── failover/
│   ├── __init__.py
│   ├── chain.py            # Model fallback chains
│   └── errors.py           # Failover error types
├── thinking/
│   ├── __init__.py
│   ├── extractor.py        # Extract thinking tags
│   └── modes.py            # stream/on/off modes
├── queuing/
│   ├── __init__.py
│   ├── lane.py             # Session lane manager
│   └── queue.py            # Async queue implementation
├── compaction/
│   ├── __init__.py
│   ├── strategy.py         # Compaction strategies
│   └── analyzer.py         # Token analysis
└── formatting/
    ├── __init__.py
    └── tool_result.py      # Tool result formatting
```

## Feature Specifications

### Feature 1: Thinking Mode

**Purpose**: Extract and handle AI reasoning process

**Components**:
- `ThinkingExtractor`: Parse `<thinking>`, `<thought>`, `<antthinking>` tags
- `ThinkingMode`: Enum (off, on, stream)
- Integration with runtime streaming

**Implementation**:
```python
class ThinkingMode(Enum):
    OFF = "off"          # Don't extract thinking
    ON = "on"            # Include thinking in final response
    STREAM = "stream"    # Stream thinking separately

class ThinkingExtractor:
    def extract(self, text: str) -> tuple[str, str]:
        """Returns (thinking_content, regular_content)"""
        pass
```

**Benefits**:
- Better transparency of AI reasoning
- Debugging capabilities
- User can see "how" AI thinks

---

### Feature 2: Auth Profile Rotation

**Purpose**: Manage multiple API keys with automatic failover and cooldown

**Components**:
- `AuthProfile`: Single auth profile with metadata
- `ProfileStore`: Manage multiple profiles
- `RotationManager`: Handle rotation logic with cooldown

**Implementation**:
```python
@dataclass
class AuthProfile:
    id: str
    provider: str
    api_key: str
    last_used: datetime | None = None
    failure_count: int = 0
    cooldown_until: datetime | None = None

class RotationManager:
    def get_next_profile(self, provider: str) -> AuthProfile:
        """Get next available profile for provider"""
        pass
    
    def mark_failure(self, profile_id: str):
        """Mark profile as failed, set cooldown"""
        pass
```

**Benefits**:
- Rate limit handling across multiple keys
- Automatic failover on auth errors
- Better reliability for production

---

### Feature 3: Model Fallback Chains

**Purpose**: Automatically try backup models when primary fails

**Components**:
- `FallbackChain`: Define model fallback sequence
- `FallbackError`: Custom error with failover metadata
- Integration with runtime retry logic

**Implementation**:
```python
@dataclass
class FallbackChain:
    primary: str
    fallbacks: list[str]
    
class FallbackManager:
    def get_next_model(self, failed_model: str) -> str | None:
        """Get next model in fallback chain"""
        pass
```

**Example**:
```python
runtime = AgentRuntime(
    model="anthropic/claude-opus-4-5",
    fallback_chain=["anthropic/claude-sonnet-4", "openai/gpt-4"]
)
```

**Benefits**:
- Resilience to provider outages
- Automatic cost optimization
- Seamless user experience

---

### Feature 4: Session Lanes/Queuing

**Purpose**: Manage concurrent requests with per-session and global queues

**Components**:
- `Lane`: Queue abstraction for session/global
- `QueueManager`: Coordinate multiple lanes
- Integration with runtime execution

**Implementation**:
```python
class Lane:
    def __init__(self, name: str, max_concurrent: int = 1):
        self.name = name
        self.queue: asyncio.Queue = asyncio.Queue()
        self.active = 0
        
    async def enqueue(self, task):
        """Add task to lane"""
        pass

class QueueManager:
    def get_session_lane(self, session_id: str) -> Lane:
        """Get or create lane for session"""
        pass
    
    def get_global_lane(self) -> Lane:
        """Get global lane"""
        pass
```

**Benefits**:
- Prevent concurrent writes to same session
- Global rate limiting
- Better resource management

---

### Feature 5: Advanced Context Compaction

**Purpose**: Intelligent message pruning when context is full

**Components**:
- `CompactionStrategy`: Different strategies (keep_system, keep_recent, importance_based)
- `TokenAnalyzer`: Accurate token counting
- `CompactionManager`: Execute compaction

**Implementation**:
```python
class CompactionStrategy(Enum):
    KEEP_RECENT = "recent"           # Keep last N messages
    KEEP_IMPORTANT = "important"     # Keep system + important
    SUMMARIZE = "summarize"          # Summarize old messages

class CompactionManager:
    def compact(
        self, 
        messages: list[Message], 
        target_tokens: int,
        strategy: CompactionStrategy
    ) -> list[Message]:
        """Compact messages to fit token budget"""
        pass
```

**Benefits**:
- Better context utilization
- Preserve important context
- Automatic handling of long conversations

---

### Feature 6: Tool Result Formatting

**Purpose**: Format tool results as markdown or plain text based on channel

**Components**:
- `ToolFormatter`: Format tool results
- `FormatMode`: Enum (markdown, plain)
- Channel-aware formatting

**Implementation**:
```python
class FormatMode(Enum):
    MARKDOWN = "markdown"
    PLAIN = "plain"

class ToolFormatter:
    def format_result(
        self, 
        result: ToolResult, 
        mode: FormatMode
    ) -> str:
        """Format tool result for display"""
        pass
```

**Example**:
```python
# Markdown (for web/telegram)
"""
### File Read: config.py
```python
DEBUG = True
```
"""

# Plain (for SMS/simple channels)
"""
File: config.py
Content: DEBUG = True
"""
```

**Benefits**:
- Better readability per channel
- Consistent formatting
- Channel-appropriate output

---

## Implementation Order

### Phase 1: Foundation (Day 1-2)
1. ✅ Create directory structure
2. ✅ Define base classes and enums
3. ✅ Write unit tests for each component

### Phase 2: Core Features (Day 3-5)
4. Implement Thinking Mode
5. Implement Tool Result Formatting
6. Implement Auth Profile Rotation

### Phase 3: Advanced Features (Day 6-8)
7. Implement Model Fallback Chains
8. Implement Session Queuing
9. Implement Advanced Compaction

### Phase 4: Integration (Day 9-10)
10. Integrate all features into runtime.py
11. Update API and CLI
12. Write integration tests
13. Update documentation

---

## Testing Strategy

### Unit Tests
- Each component isolated
- Mock external dependencies
- Cover edge cases

### Integration Tests
- Full runtime with all features
- Real-world scenarios
- Performance tests

### Example Test Cases
```python
# Test thinking mode
def test_thinking_extraction():
    text = "Here's my thought: <thinking>analyze problem</thinking>The answer is 42"
    thinking, content = extractor.extract(text)
    assert thinking == "analyze problem"
    assert content == "The answer is 42"

# Test auth rotation
def test_profile_rotation_on_failure():
    manager.mark_failure("profile-1")
    next_profile = manager.get_next_profile("anthropic")
    assert next_profile.id != "profile-1"
    assert next_profile.cooldown_until is None

# Test model fallback
def test_fallback_chain():
    runtime = AgentRuntime(
        model="provider-a/model-1",
        fallback_chain=["provider-b/model-2"]
    )
    # Simulate provider-a failure
    # Should automatically try provider-b
```

---

## Configuration

### Example Config (config.yaml)
```yaml
agent:
  model: anthropic/claude-opus-4-5
  thinking_mode: stream
  
  # Fallback chain
  fallback_models:
    - anthropic/claude-sonnet-4
    - openai/gpt-4
  
  # Auth profiles
  auth_profiles:
    - id: anthropic-main
      provider: anthropic
      api_key_env: ANTHROPIC_API_KEY
    - id: anthropic-backup
      provider: anthropic
      api_key_env: ANTHROPIC_API_KEY_2
  
  # Context management
  context:
    max_tokens: 180000
    compaction_strategy: keep_important
    compaction_threshold: 0.8
  
  # Queuing
  queuing:
    enabled: true
    max_concurrent_per_session: 1
    max_concurrent_global: 10
  
  # Tool formatting
  tool_format: markdown  # or 'plain'
```

---

## API Changes

### Enhanced Runtime Initialization
```python
runtime = AgentRuntime(
    model="anthropic/claude-opus-4-5",
    
    # New parameters
    thinking_mode=ThinkingMode.STREAM,
    fallback_models=["anthropic/claude-sonnet-4", "openai/gpt-4"],
    auth_profiles=[profile1, profile2],
    enable_queuing=True,
    tool_format=FormatMode.MARKDOWN,
    compaction_strategy=CompactionStrategy.KEEP_IMPORTANT
)
```

### New Events
```python
# Thinking events
AgentEvent("thinking", {"content": "...", "mode": "stream"})

# Failover events
AgentEvent("failover", {"from": "model-a", "to": "model-b", "reason": "rate_limit"})

# Queue events
AgentEvent("queue", {"position": 3, "lane": "session-123"})
```

---

## Migration Guide

### For Existing Code
All existing code will continue to work. New features are opt-in:

```python
# Before (still works)
runtime = AgentRuntime("anthropic/claude-opus-4-5")

# After (with new features)
runtime = AgentRuntime(
    "anthropic/claude-opus-4-5",
    thinking_mode=ThinkingMode.STREAM,
    fallback_models=["openai/gpt-4"]
)
```

---

## Success Metrics

1. **Feature Coverage**: 100% of planned features implemented
2. **Test Coverage**: >80% for new code
3. **Performance**: <10% overhead for new features
4. **Compatibility**: 100% backward compatible
5. **Documentation**: Complete guides for all features

---

## Timeline

- **Week 1**: Foundation + Core Features (Thinking, Formatting, Auth)
- **Week 2**: Advanced Features (Fallback, Queuing, Compaction)
- **Week 3**: Integration, Testing, Documentation

**Total Estimated Time**: 3 weeks for complete implementation

---

## Next Steps

1. Review and approve this plan
2. Set up development branch
3. Begin Phase 1 implementation
4. Iterative review and testing

---

*Last Updated*: 2026-01-29
*Status*: Planning Phase
*Assigned*: AI Agent
