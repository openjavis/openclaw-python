# OpenClaw Tools

Elegant tool system aligned with pi-mono architecture, providing consistent interfaces across different LLM providers.

## Architecture

```
┌─────────────────────────────────────────┐
│         Core Utilities                  │
│  truncate.py, path_utils.py            │
└─────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│      Operations Interfaces              │
│  BashOps, ReadOps, WriteOps, EditOps   │
└─────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│        Tool Implementations             │
│  bash.py, read.py, write.py, edit.py   │
└─────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│          Tool Registry                  │
│         registry.py                     │
└─────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────┐
│         Agent Runtime                   │
│         runtime.py                      │
└─────────────────────────────────────────┘
```

## Features

### 1. Output Truncation

All tools implement consistent output truncation to prevent context overflow:

- **Default Limits**: 50KB or 2000 lines (whichever is hit first)
- **Head Truncation**: For file reading (shows beginning)
- **Tail Truncation**: For bash output (shows end)
- **UTF-8 Safe**: Properly handles multibyte characters

```python
from openclaw.agents.tools import truncate_tail, DEFAULT_MAX_BYTES

result = truncate_tail(large_output)
if result.truncated:
    print(f"Showing last {result.output_lines} lines")
    print(f"Full output saved to: {temp_file_path}")
```

### 2. Pluggable Operations

Tools support pluggable operations for remote execution and testing:

```python
from openclaw.agents.tools import create_bash_tool
from openclaw.agents.tools.operations import BashOperations

class SSHBashOperations(BashOperations):
    async def exec(self, command, cwd, on_data, signal, timeout, env):
        # Execute command via SSH
        pass

# Create tool with custom operations
tool = create_bash_tool("/remote/path", operations=SSHBashOperations())
```

### 3. Streaming Updates

Long-running tools can send progress updates:

```python
async def handle_update(result: AgentToolResult):
    print(f"Progress: {result.content[0].text}")

result = await bash_tool.execute(
    tool_call_id="id",
    params={"command": "long_running_command"},
    signal=None,
    on_update=handle_update,  # Receives streaming updates
)
```

### 4. Cancellation Support

All tools support graceful cancellation:

```python
import asyncio

signal = asyncio.Event()

# Start long operation
task = asyncio.create_task(
    tool.execute("id", params, signal=signal, on_update=None)
)

# Cancel it
signal.set()
```

### 5. macOS Path Compatibility

Read tool handles macOS filename quirks automatically:

- NFD normalization (decomposed Unicode)
- Curly quotes (U+2019 instead of ')
- Narrow no-break space before AM/PM

```python
# These all work on macOS:
read_tool.execute("id", {"path": "Screenshot 2024-01-01 at 12:00 PM.png"})
# Automatically tries variants:
# - Screenshot 2024-01-01 at 12:00 PM.png (U+202F before PM)
# - Screenshot 2024-01-01 at 12:00 PM.png (NFD normalization)
```

## Tool Interface

All tools implement the `AgentToolBase` interface:

```python
class AgentToolBase(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Tool identifier (e.g., "bash", "read")"""
        pass
    
    @property
    @abstractmethod
    def label(self) -> str:
        """Human-readable name (e.g., "Bash", "Read File")"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description for LLM"""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """JSON Schema for parameters"""
        pass
    
    @abstractmethod
    async def execute(
        self,
        tool_call_id: str,
        params: dict,
        signal: asyncio.Event | None = None,
        on_update: Callable[[AgentToolResult], None] | None = None,
    ) -> AgentToolResult:
        """Execute tool with streaming and cancellation support"""
        pass
```

## Tool Results

All tools return `AgentToolResult`:

```python
@dataclass
class AgentToolResult:
    content: list[Content]  # TextContent, ImageContent, etc.
    details: dict[str, Any] | None  # Metadata (truncation, diff, etc.)
```

## Model Compatibility

### Gemini

- **Requirement**: Strict `function_call → function_response → model_response` sequence
- **Handled By**: Runtime ensures correct message ordering
- **No Extra Work**: Tools just return `AgentToolResult`

### Claude

- **Requirement**: Standard tool_use/tool_result cycle
- **Handled By**: Compatible with `AgentToolResult` format
- **Supports**: Full streaming and image content

### OpenAI

- **Requirement**: Standard function calling
- **Handled By**: Compatible with `AgentToolResult` format
- **Supports**: Full feature set

### All Models

- **Unified Output**: All tools return `AgentToolResult` in same format
- **Consistent Schema**: JSON Schema format works across all providers
- **No Model-Specific Code**: Tools don't need to know which model is being used

## Usage Examples

### Basic Usage

```python
from openclaw.agents.tools import create_bash_tool, create_read_tool

# Create tools
bash = create_bash_tool("/workspace")
read = create_read_tool("/workspace")

# Execute bash command
result = await bash.execute(
    tool_call_id="1",
    params={"command": "ls -la"},
    signal=None,
    on_update=None,
)

print(result.content[0].text)  # Command output

# Read file
result = await read.execute(
    tool_call_id="2",
    params={"path": "README.md"},
    signal=None,
    on_update=None,
)

print(result.content[0].text)  # File contents
```

### With Registry

```python
from openclaw.agents.tools import ToolRegistry

registry = ToolRegistry(workspace_dir="/workspace")

# Tools are auto-registered
bash_tool = registry.get("bash")
read_tool = registry.get("read")
```

### Remote Execution

```python
from openclaw.agents.tools import create_bash_tool
from openclaw.agents.tools.operations import BashOperations

class DockerBashOperations(BashOperations):
    def __init__(self, container_id):
        self.container_id = container_id
    
    async def exec(self, command, cwd, on_data, signal, timeout, env):
        # Execute in Docker container
        docker_command = f"docker exec {self.container_id} bash -c 'cd {cwd} && {command}'"
        # ... execute and stream output via on_data
        return {"exit_code": 0}

# Create tool for Docker container
ops = DockerBashOperations("my-container")
bash = create_bash_tool("/app", operations=ops)
```

### Testing with Mocks

```python
from openclaw.agents.tools.operations import BashOperations

class MockBashOperations(BashOperations):
    async def exec(self, command, cwd, on_data, signal, timeout, env):
        # Mock execution for testing
        output = b"mocked output\n"
        on_data(output)
        return {"exit_code": 0}

# Test tool with mock
tool = create_bash_tool("/test", operations=MockBashOperations())
result = await tool.execute("id", {"command": "test"}, None, None)
assert "mocked output" in result.content[0].text
```

## Migration from Legacy Tools

Old tools using `LegacyAgentTool` are automatically supported via compatibility layer:

```python
# Old interface (still works)
class OldTool(LegacyAgentTool):
    async def _execute_impl(self, params):
        return ToolResult(success=True, content="output")

# Runtime automatically converts to new interface
```

New tools should use `AgentToolBase`:

```python
# New interface (recommended)
class NewTool(AgentToolBase):
    async def execute(self, tool_call_id, params, signal, on_update):
        return AgentToolResult(content=[TextContent(text="output")])
```

## Best Practices

1. **Always use factory functions**: `create_bash_tool()`, not `BashTool()`
2. **Check cancellation**: Periodically check `signal.is_set()` in long operations
3. **Send updates**: Use `on_update` for operations > 5 seconds
4. **Trust truncation**: Don't try to truncate manually, tools handle it
5. **Provide context**: When truncation occurs, tools provide helpful continuation hints
6. **Test with mocks**: Use pluggable operations for unit tests
7. **Support remote**: Design operations interfaces for SSH/Docker if needed

## Related Files

- `truncate.py`: Output truncation utilities
- `path_utils.py`: Path resolution with macOS compatibility
- `operations.py`: Abstract operations interfaces
- `default_operations.py`: Local filesystem implementations
- `bash.py`, `read.py`, `write.py`, `edit.py`: Core tool implementations
- `base.py`: Tool interface definitions
- `registry.py`: Tool registration and discovery
- `runtime.py`: Tool execution in agent context
