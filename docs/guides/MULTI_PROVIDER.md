# Multi-Provider Support

ClawdBot Python now supports multiple LLM providers, allowing you to use different AI models based on your needs.

## Supported Providers

| Provider | Models | API Key Required | Notes |
|----------|--------|------------------|-------|
| **Anthropic** | Claude (Opus, Sonnet, Haiku) | ✅ Yes | Best for coding, reasoning |
| **OpenAI** | GPT-4, GPT-3.5, o1 | ✅ Yes | General purpose, widely used |
| **Google Gemini** | Gemini Pro, Flash, Ultra | ✅ Yes | Multimodal, fast |
| **AWS Bedrock** | Claude, Llama, Titan, etc. | ✅ AWS Creds | Enterprise-grade |
| **Ollama** | Llama, Mistral, Codellama, etc. | ❌ No | Local, private, free |
| **Custom** | Any OpenAI-compatible API | Varies | LM Studio, etc. |

---

## Quick Start

### Format

Model format: `provider/model-name`

```python
from clawdbot.agents.runtime import MultiProviderRuntime

# Anthropic Claude
runtime = MultiProviderRuntime("anthropic/claude-opus-4-5")

# OpenAI GPT
runtime = MultiProviderRuntime("openai/gpt-4")

# Google Gemini
runtime = MultiProviderRuntime("gemini/gemini-pro")

# AWS Bedrock
runtime = MultiProviderRuntime("bedrock/anthropic.claude-3-sonnet")

# Ollama (local)
runtime = MultiProviderRuntime("ollama/llama3")
```

---

## 1. Anthropic Claude

### Models
- `claude-opus-4-5` - Most capable, best for complex tasks
- `claude-sonnet-4-5` - Balanced performance/cost
- `claude-3-5-sonnet` - Fast, efficient
- `claude-haiku-3-5` - Fastest, cheapest

### Setup
```bash
export ANTHROPIC_API_KEY=sk-ant-xxx
```

### Example
```python
runtime = MultiProviderRuntime(
    "anthropic/claude-opus-4-5",
    api_key="sk-ant-xxx"  # or use env var
)
```

### Get API Key
https://console.anthropic.com/

---

## 2. OpenAI GPT

### Models
- `gpt-4` - Most capable GPT model
- `gpt-4-turbo` - Faster, cheaper GPT-4
- `gpt-3.5-turbo` - Fast, affordable
- `o1`, `o1-mini` - Reasoning models

### Setup
```bash
export OPENAI_API_KEY=sk-xxx
```

### Example
```python
runtime = MultiProviderRuntime(
    "openai/gpt-4",
    api_key="sk-xxx"
)
```

### Get API Key
https://platform.openai.com/api-keys

---

## 3. Google Gemini

### Models
- `gemini-pro` - General purpose
- `gemini-pro-vision` - Multimodal (text + images)
- `gemini-3-pro-preview` - Latest preview
- `gemini-3-flash-preview` - Fastest

### Setup
```bash
export GOOGLE_API_KEY=xxx
```

### Example
```python
runtime = MultiProviderRuntime(
    "gemini/gemini-pro",
    api_key="xxx"
)
```

### Get API Key
https://makersuite.google.com/app/apikey

### Features
- ✅ Fast responses
- ✅ Large context window
- ✅ Multimodal support (vision)
- ✅ Free tier available

---

## 4. AWS Bedrock

### Models
- `anthropic.claude-3-sonnet-20240229-v1:0` - Claude on Bedrock
- `anthropic.claude-3-haiku-20240307-v1:0` - Fast Claude
- `meta.llama3-70b-instruct-v1:0` - Meta Llama 3
- `amazon.titan-text-express-v1` - Amazon Titan
- `cohere.command-r-plus-v1:0` - Cohere Command

### Setup
```bash
export AWS_ACCESS_KEY_ID=xxx
export AWS_SECRET_ACCESS_KEY=xxx
export AWS_REGION=us-east-1
```

### Example
```python
runtime = MultiProviderRuntime(
    "bedrock/anthropic.claude-3-sonnet-20240229-v1:0",
    region="us-east-1"
)
```

### Features
- ✅ Enterprise-grade
- ✅ Multiple models
- ✅ AWS infrastructure
- ✅ Compliance & security

---

## 5. Ollama (Local)

### Popular Models
- `llama3` - Meta's Llama 3 (8B, 70B)
- `mistral` - Mistral 7B
- `mixtral` - Mixtral 8x7B
- `codellama` - Code-specialized
- `phi` - Microsoft Phi
- `gemma` - Google Gemma
- `qwen` - Alibaba Qwen
- `deepseek-coder` - Code-specialized

### Setup
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama
ollama serve

# Pull a model
ollama pull llama3
```

### Example
```python
runtime = MultiProviderRuntime(
    "ollama/llama3",
    base_url="http://localhost:11434"  # default
)
```

### Features
- ✅ Runs locally (private)
- ✅ No API costs
- ✅ No internet required
- ✅ Many open-source models
- ❌ Requires local compute

---

## 6. Custom (OpenAI-Compatible)

Many tools provide OpenAI-compatible APIs:
- LM Studio
- LocalAI
- FastChat
- vLLM
- Text Generation WebUI

### Example: LM Studio
```python
runtime = MultiProviderRuntime(
    "lmstudio/local-model",
    base_url="http://localhost:1234/v1",
    api_key="not-needed"
)
```

---

## Comparison

### By Use Case

**Best for Coding:**
1. Claude Opus 4-5 (Anthropic)
2. GPT-4 (OpenAI)
3. Codellama (Ollama)

**Best for Speed:**
1. Gemini Flash (Google)
2. Claude Haiku (Anthropic)
3. GPT-3.5 Turbo (OpenAI)

**Best for Cost:**
1. Ollama (Free, local)
2. Gemini (Free tier)
3. GPT-3.5 Turbo

**Best for Privacy:**
1. Ollama (fully local)
2. Self-hosted OpenAI-compatible

**Best for Enterprise:**
1. AWS Bedrock
2. Azure OpenAI (via OpenAI provider)

### By Cost (per 1M tokens)

| Provider | Input | Output |
|----------|-------|--------|
| GPT-3.5 Turbo | $0.50 | $1.50 |
| Gemini Pro | $0.50 | $1.50 |
| Claude Haiku | $0.25 | $1.25 |
| Claude Sonnet | $3.00 | $15.00 |
| Claude Opus | $15.00 | $75.00 |
| GPT-4 | $30.00 | $60.00 |
| **Ollama** | **$0** | **$0** |

---

## Advanced Usage

### Switching Providers Mid-Session

```python
# Start with Gemini (fast)
runtime_gemini = MultiProviderRuntime("gemini/gemini-pro")
session = Session("demo", "./workspace")

async for event in runtime_gemini.run_turn(session, "Quick question?"):
    pass

# Switch to Claude for complex reasoning
runtime_claude = MultiProviderRuntime("anthropic/claude-opus-4-5")

async for event in runtime_claude.run_turn(session, "Complex analysis?"):
    pass
```

### Custom Parameters

```python
runtime = MultiProviderRuntime(
    "openai/gpt-4",
    temperature=0.9,      # More creative
    top_p=0.95,           # Nucleus sampling
    max_tokens=2000       # Response length
)
```

### Fallback Chain

```python
async def try_with_fallback(message):
    providers = [
        "anthropic/claude-opus-4-5",
        "openai/gpt-4",
        "gemini/gemini-pro",
        "ollama/llama3"
    ]
    
    for model in providers:
        try:
            runtime = MultiProviderRuntime(model)
            async for event in runtime.run_turn(session, message):
                if event.type == "assistant":
                    return event
        except Exception as e:
            print(f"Failed with {model}: {e}")
            continue
    
    raise Exception("All providers failed")
```

---

## Troubleshooting

### API Key Errors
```python
# Check environment variables
import os
print(f"Anthropic: {bool(os.getenv('ANTHROPIC_API_KEY'))}")
print(f"OpenAI: {bool(os.getenv('OPENAI_API_KEY'))}")
print(f"Google: {bool(os.getenv('GOOGLE_API_KEY'))}")
```

### Ollama Not Running
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve
```

### Rate Limits
```python
# Add retry logic
runtime = MultiProviderRuntime(
    "openai/gpt-4",
    max_retries=5  # Retry on rate limits
)
```

---

## Examples

See:
- `examples/06_gemini_example.py` - Gemini usage
- `examples/07_multi_provider.py` - Test all providers

---

## Migration from Old Runtime

```python
# Old (only Anthropic/OpenAI)
from clawdbot.agents.runtime import AgentRuntime
runtime = AgentRuntime("anthropic/claude-opus")

# New (all providers)
from clawdbot.agents.runtime import MultiProviderRuntime
runtime = MultiProviderRuntime("gemini/gemini-pro")
```

The new runtime is backward compatible - it works with all existing code.

---

## Next Steps

1. **Get API Keys** for providers you want to use
2. **Try Examples**: Run `uv run python examples/07_multi_provider.py`
3. **Choose Model**: Based on your use case and budget
4. **Optimize**: Use faster models for simple tasks, powerful ones for complex tasks

---

**Questions?** Open an issue on GitHub!
