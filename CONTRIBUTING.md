# Contributing to ClawdBot Python

Thank you for your interest in contributing to ClawdBot Python! This document provides comprehensive guidelines for contributing to the project.

## Project Status

**Version**: 0.4.1 (Beta)  
**Status**: Production MVP (90-95% complete)  
**Stage**: Ready for beta testing and production deployments

## Quick Start for Contributors

### Prerequisites

- **Python 3.11+** (3.12 recommended)
- **uv** package manager (we migrated from Poetry in v0.4.0)
- **Git**

### Setup Development Environment

```bash
# 1. Fork the repository on GitHub

# 2. Clone your fork
git clone https://github.com/YOUR-USERNAME/clawdbot-python.git
cd clawdbot-python

# 3. Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 4. Install dependencies
uv sync

# 5. Copy environment template
cp .env.example .env
# Edit .env with your API keys (at least one LLM provider)

# 6. Run tests to verify setup
uv run pytest

# 7. Check code quality
uv run black --check clawdbot/ tests/
uv run ruff check clawdbot/
```

---

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

### 2. Make Your Changes

- Follow existing code style and patterns
- Add tests for new functionality
- Update documentation as needed
- Keep commits focused and atomic

### 3. Run Tests

```bash
# Quick test
uv run pytest

# With coverage
uv run pytest --cov=clawdbot --cov-report=html

# Specific test file
uv run pytest tests/test_runtime.py -v

# Integration tests
uv run pytest tests/integration/ -v

# Using Makefile (recommended)
make test           # All tests
make test-cov       # With coverage report
make test-fast      # Parallel execution
```

### 4. Check Code Quality

```bash
# Format code
uv run black clawdbot/ tests/ examples/

# Lint
uv run ruff check clawdbot/ tests/

# Type check
uv run mypy clawdbot/ --ignore-missing-imports

# Using Makefile
make format         # Auto-format
make format-check   # Check only
make lint           # All linters
```

### 5. Commit Changes

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```bash
git commit -m "feat: add Gemini provider support"
git commit -m "fix: resolve authentication bug in API keys"
git commit -m "docs: update multi-provider guide"
git commit -m "test: add integration tests for channels"
```

**Commit Types**:
- `feat:` - New feature (minor version bump)
- `fix:` - Bug fix (patch version bump)
- `docs:` - Documentation changes
- `test:` - Test additions/updates
- `refactor:` - Code refactoring (no behavior change)
- `perf:` - Performance improvements
- `style:` - Code style/formatting
- `chore:` - Maintenance tasks
- `ci:` - CI/CD changes
- `build:` - Build system changes

**Breaking Changes**:
```bash
git commit -m "feat!: change runtime API signature

BREAKING CHANGE: Runtime now requires provider parameter"
```

### 6. Push and Create PR

```bash
# Push to your fork
git push origin feature/your-feature-name

# Go to GitHub and create Pull Request
```

**PR Checklist**:
- [ ] Tests pass locally
- [ ] Code is formatted (black, ruff)
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (for significant changes)
- [ ] PR description explains what/why
- [ ] Related issues linked (#123)

---

## Areas for Contribution

### 🔥 High Priority

1. **Provider Testing & Examples**
   - Test Gemini, Bedrock, Ollama providers
   - Add real-world usage examples
   - Document edge cases and gotchas

2. **Channel Implementations**
   - Complete WhatsApp channel
   - Complete Signal channel
   - Test existing channels (Telegram, Discord, Slack)
   - Add channel-specific error handling

3. **Tool Development**
   - Complete browser tool (Playwright integration)
   - Complete cron tool (APScheduler)
   - Complete memory tool (LanceDB)
   - Complete TTS tool (ElevenLabs)
   - Add sessions management tool

4. **Test Coverage**
   - Increase from 60% to 80%+
   - Add edge case tests
   - Add performance tests
   - Add security tests

5. **Integration Tests**
   - End-to-end agent flows
   - Multi-turn conversations
   - Tool execution chains
   - Channel message handling

### 🎯 Medium Priority

6. **Documentation**
   - Add more examples
   - Improve API documentation
   - Add troubleshooting guide
   - Create video tutorials

7. **Performance Optimization**
   - Context window management
   - Tool execution efficiency
   - Memory usage optimization
   - Response time improvements

8. **Monitoring & Observability**
   - Enhanced metrics
   - Distributed tracing
   - Performance dashboards
   - Alert systems

9. **Bug Fixes**
   - Fix reported issues
   - Improve error handling
   - Add validation checks

### 💡 Nice to Have

10. **New Providers**
    - Azure OpenAI
    - Cohere
    - Hugging Face Inference API
    - Custom self-hosted models

11. **Advanced Features**
    - Multi-agent routing
    - Voice wake detection
    - Live canvas
    - Webhook support

12. **UI/Dashboard**
    - Web interface for monitoring
    - Session management UI
    - Configuration editor

13. **Deployment**
    - Kubernetes manifests
    - Helm charts
    - Terraform modules

---

## Specific Contribution Guides

### Adding a New LLM Provider

See existing implementations in `clawdbot/agents/providers/`:

```python
# 1. Create provider file
# clawdbot/agents/providers/your_provider.py

from .base import LLMProvider, LLMResponse, LLMMessage

class YourProvider(LLMProvider):
    @property
    def provider_name(self) -> str:
        return "your-provider"
    
    def get_client(self):
        # Initialize API client
        pass
    
    async def stream(self, messages, tools=None, max_tokens=4096, **kwargs):
        # Stream responses
        pass
```

```python
# 2. Register in providers/__init__.py
from .your_provider import YourProvider

__all__ = [..., "YourProvider"]
```

```python
# 3. Update runtime.py
elif provider_name == "your-provider":
    return YourProvider(**kwargs)
```

```python
# 4. Add tests
# tests/test_providers.py
def test_your_provider():
    provider = YourProvider("model-name")
    # Test implementation
```

```python
# 5. Add example
# examples/08_your_provider.py
runtime = MultiProviderRuntime("your-provider/model-name")
```

```markdown
# 6. Update documentation
# docs/guides/MULTI_PROVIDER.md
```

### Adding a New Channel

```python
# 1. Create channel file
# clawdbot/channels/your_channel.py

from .base import ChannelPlugin
from .connection import ConnectionManager, HealthChecker

class YourChannel(ChannelPlugin):
    async def connect(self):
        # Setup connection
        pass
    
    async def send_message(self, target, message):
        # Send message
        pass
    
    async def receive_messages(self):
        # Listen for messages
        pass
```

```python
# 2. Use ConnectionManager for reliability
self._connection_manager = ConnectionManager(
    connect_fn=self._do_connect,
    disconnect_fn=self._do_disconnect,
    config=ReconnectConfig(enabled=True, max_attempts=10)
)
```

```python
# 3. Add health checking
self._health_checker = HealthChecker(
    check_fn=self._health_check,
    interval=60.0
)
```

```python
# 4. Register in channels/__init__.py
from .your_channel import YourChannel
```

```python
# 5. Add tests
# tests/test_channels.py
```

### Adding a New Tool

```python
# 1. Create tool file
# clawdbot/agents/tools/your_tool.py

from .base import AgentTool, ToolResult

class YourTool(AgentTool):
    @property
    def name(self) -> str:
        return "your_tool"
    
    @property
    def description(self) -> str:
        return "Description of what your tool does"
    
    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "Parameter description"
                }
            },
            "required": ["param1"]
        }
    
    async def execute(self, arguments: dict) -> ToolResult:
        # Implement tool logic
        result = do_something(arguments["param1"])
        return ToolResult(success=True, output=result)
```

```python
# 2. Register in tools/registry.py
from .your_tool import YourTool

class ToolRegistry:
    def _register_default_tools(self):
        # ... existing tools
        self.register(YourTool())
```

```python
# 3. Add tests
# tests/test_tools.py
```

```python
# 4. Add example
# examples/with_your_tool.py
```

---

## Testing Requirements

### Must Have

All PRs must meet these requirements:

- ✅ **Pass all existing tests**
- ✅ **Add tests for new functionality**
- ✅ **Maintain or increase test coverage**
- ✅ **Pass all linters** (black, ruff, mypy)
- ✅ **Include docstrings** for public APIs

### Test Types

1. **Unit Tests** (`tests/`)
   - Test individual functions/classes
   - Mock external dependencies
   - Fast execution (<1s each)

2. **Integration Tests** (`tests/integration/`)
   - Test component interactions
   - Use real dependencies (where safe)
   - Slower execution (1-10s each)

3. **Example Tests**
   - Ensure examples run without errors
   - Test common use cases

### Running Tests

```bash
# All tests
uv run pytest

# Specific category
uv run pytest tests/test_runtime.py
uv run pytest tests/integration/

# With markers
uv run pytest -m "not slow"
uv run pytest -m integration

# With coverage
uv run pytest --cov=clawdbot --cov-report=html
open htmlcov/index.html

# Parallel execution (faster)
uv run pytest -n auto

# Using Makefile
make test
make test-cov
make test-fast
make test-integration
```

### Writing Good Tests

```python
# Good test example
import pytest
from clawdbot.agents.runtime import MultiProviderRuntime

@pytest.mark.asyncio
async def test_gemini_provider_initialization():
    """Test that Gemini provider initializes correctly"""
    runtime = MultiProviderRuntime("gemini/gemini-pro")
    
    assert runtime.provider_name == "gemini"
    assert runtime.model_name == "gemini-pro"
    assert runtime.provider is not None

@pytest.mark.integration
@pytest.mark.asyncio
async def test_gemini_streaming_response(mock_gemini_api):
    """Test streaming responses from Gemini"""
    runtime = MultiProviderRuntime("gemini/gemini-pro")
    session = Session("test", "./tmp")
    
    response_parts = []
    async for event in runtime.run_turn(session, "Hello"):
        if event.type == "assistant":
            response_parts.append(event.data["delta"]["text"])
    
    response = "".join(response_parts)
    assert len(response) > 0
    assert len(session.messages) >= 2
```

---

## Code Style Guidelines

### Python Style

- **PEP 8** compliant
- **Type hints** for all function signatures
- **Docstrings** for public APIs (Google style)
- **Max line length**: 100 characters
- **Use black** for formatting
- **Use ruff** for linting

### Example

```python
from typing import Optional, AsyncIterator

class ExampleClass:
    """
    Example class demonstrating code style.
    
    This class shows how to properly format code according to
    project standards.
    
    Attributes:
        name: The name of the example
        value: An optional integer value
    """
    
    def __init__(self, name: str, value: Optional[int] = None):
        self.name = name
        self.value = value
    
    async def process(self, input_data: str) -> str:
        """
        Process input data asynchronously.
        
        Args:
            input_data: The data to process
            
        Returns:
            The processed result
            
        Raises:
            ValueError: If input_data is empty
        """
        if not input_data:
            raise ValueError("input_data cannot be empty")
        
        # Process logic here
        result = f"Processed: {input_data}"
        return result
```

### Imports

```python
# Standard library
import os
import sys
from pathlib import Path

# Third party
import httpx
from pydantic import BaseModel

# Local
from .base import BaseClass
from ..utils import helper_function
```

---

## Documentation Guidelines

### README.md

- Keep main README concise
- Link to detailed guides
- Include quick start example
- Show current status

### docs/

- `docs/guides/` - User-facing guides
- `docs/development/` - Developer documentation
- `docs/archive/` - Historical/deprecated docs

### Docstrings

Use Google style:

```python
def function_name(param1: str, param2: int) -> bool:
    """
    Short description of function.
    
    Longer description if needed, explaining what the function does,
    its purpose, and any important details.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When param1 is empty
        TypeError: When param2 is negative
        
    Example:
        >>> function_name("test", 42)
        True
    """
    pass
```

---

## CI/CD and Automation

### GitHub Actions

All PRs trigger automated checks:

1. **Linting** (black, ruff, mypy)
2. **Tests** (Python 3.11, 3.12)
3. **Coverage** reporting
4. **Docker** build test

### Running CI Locally

```bash
# Run same checks as CI
make test lint

# Or manually
uv run pytest --cov=clawdbot
uv run black --check clawdbot/ tests/
uv run ruff check clawdbot/
uv run mypy clawdbot/ --ignore-missing-imports

# Build Docker image
make docker-build
docker run --rm clawdbot-python:latest python -m pytest
```

### Pre-commit Hooks (Optional)

```bash
# Install pre-commit
uv add --dev pre-commit

# Install hooks
uv run pre-commit install

# Run manually
uv run pre-commit run --all-files
```

---

## Review Process

### Automated Checks

All PRs must pass:
- ✅ All tests
- ✅ Code linting
- ✅ Type checking
- ✅ Docker build

### Human Review

1. **At least one maintainer** reviews code
2. **Changes requested** if needed - please address them
3. **Discussion** for architectural decisions
4. **Approval** required before merge

### Review Timeline

- **Simple PRs** (docs, small fixes): 1-2 days
- **Medium PRs** (features, refactors): 3-5 days
- **Complex PRs** (architecture changes): 1-2 weeks

We'll try to review as quickly as possible!

---

## Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):

- `0.x.y` - Pre-1.0 (current phase)
- `x.0.0` - Major (breaking changes)
- `0.x.0` - Minor (new features, backward compatible)
- `0.0.x` - Patch (bug fixes)

### Release Checklist

1. Update `VERSION.txt`
2. Update `CHANGELOG.md`
3. Update `pyproject.toml` version
4. Tag release: `git tag v0.4.1`
5. Push: `git push origin v0.4.1`
6. GitHub Actions auto-builds and publishes

---

## Community Guidelines

### Code of Conduct

- **Be respectful** and inclusive
- **Provide constructive** feedback
- **Help others** when possible
- **No harassment** or discrimination
- **Keep discussions** professional

### Communication

- **GitHub Issues** - Bug reports, feature requests
- **GitHub Discussions** - Questions, ideas
- **Pull Requests** - Code contributions
- **Code Reviews** - Constructive feedback

---

## Recognition

Contributors are recognized through:

- ✨ **CHANGELOG.md** - Listed in release notes
- 🎉 **GitHub Contributors** - Shown on repository page
- 📝 **Release Announcements** - Mentioned in releases
- 🏆 **Special Thanks** - For significant contributions

---

## Getting Help

### Resources

- 📚 **Documentation**: `docs/` folder
- 📝 **Examples**: `examples/` folder
- 🐛 **Issues**: [GitHub Issues](https://github.com/zhaoyuong/clawdbot-python/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/zhaoyuong/clawdbot-python/discussions)

### Ask Questions

- **Before coding**: Open an issue to discuss approach
- **During development**: Ask in PR comments
- **General questions**: Use GitHub Discussions

---

## Useful Links

- [README](README.md) - Project overview
- [PRODUCTION_READY](PRODUCTION_READY.md) - Deployment guide
- [Multi-Provider Guide](docs/guides/MULTI_PROVIDER.md) - Using different LLMs
- [Architecture](docs/development/ARCHITECTURE.md) - System design
- [Project Status](PROJECT_STATUS.md) - Current completion status

---

## Thank You! 🎉

Every contribution, no matter how small, helps make ClawdBot Python better.

We appreciate:
- 💻 **Code contributions**
- 📝 **Documentation improvements**
- 🐛 **Bug reports**
- 💡 **Feature suggestions**
- ⭐ **Stars on GitHub**
- 📢 **Spreading the word**

**Welcome to the ClawdBot Python community!**

---

*Last updated: 2026-01-28 (v0.4.1)*
