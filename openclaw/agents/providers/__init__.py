from .base import LLMProvider, LLMMessage, LLMResponse
from .openai_provider import OpenAIProvider

# Keep compatibility with both old and new Google provider modules.
try:
    from .gemini_provider import GeminiProvider
except ImportError:
    GeminiProvider = None

try:
    from .google_provider import GoogleGenAIProvider
except ImportError:
    GoogleGenAIProvider = None

# Backward-compatible alias expected by runtime.py
if GeminiProvider is None and GoogleGenAIProvider is not None:
    GeminiProvider = GoogleGenAIProvider

# Dynamically import other providers to avoid hard crashes if dependencies are missing
try:
    from .anthropic_provider import AnthropicProvider
except ImportError:
    AnthropicProvider = None

try:
    from .ollama_provider import OllamaProvider
except ImportError:
    OllamaProvider = None

try:
    from .bedrock_provider import BedrockProvider
except ImportError:
    BedrockProvider = None

__all__ = [
    "LLMProvider",
    "LLMMessage",
    "LLMResponse",
    "OpenAIProvider",
    "GeminiProvider",
    "GoogleGenAIProvider",
    "AnthropicProvider",
    "OllamaProvider",
    "BedrockProvider",
]
