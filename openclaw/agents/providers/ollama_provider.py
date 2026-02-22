"""
Ollama provider implementation
"""
from __future__ import annotations


import json
import logging
from collections.abc import AsyncIterator

import httpx

from .base import LLMMessage, LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """
    Ollama provider for local models

    Supports any Ollama model:
    - llama3, llama2
    - mistral, mixtral
    - codellama
    - phi, gemma
    - qwen, deepseek-coder
    - And many more!

    Example:
        # Default (localhost:11434)
        provider = OllamaProvider("llama3")

        # Custom host
        provider = OllamaProvider("mistral", base_url="http://192.168.1.100:11434")
    """

    def __init__(self, model: str = "llama3", base_url: str | None = None, **kwargs):
        super().__init__(model, base_url=base_url or "http://localhost:11434", **kwargs)

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def supports_tool_calling(self) -> bool:
        # Ollama has experimental tool support for some models
        return False

    def validate_model(self, model: str) -> bool:
        """Ollama accepts any non-empty model name."""
        return bool(model and model.strip())

    def _format_messages(self, messages: list[LLMMessage]) -> list[dict]:
        """Convert LLMMessages to Ollama chat format."""
        result = []
        for msg in messages:
            result.append({"role": msg.role, "content": msg.content or ""})
        return result

    async def _make_request(self, path: str, method: str = "GET", json: dict | None = None) -> dict:
        """
        Make a single HTTP request to Ollama and return the parsed JSON response.

        Args:
            path: API path (e.g. "/api/tags")
            method: HTTP method
            json: Request body

        Returns:
            Parsed JSON response dict
        """
        client = self.get_client()
        if method.upper() == "GET":
            response = await client.get(path)
        else:
            response = await client.post(path, json=json or {})
        response.raise_for_status()
        return response.json()

    async def _make_api_call(
        self,
        messages: list[LLMMessage],
        model: str | None = None,
        max_tokens: int = 4096,
        **kwargs,
    ) -> AsyncIterator[dict]:
        """
        Low-level streaming API call to Ollama.

        Yields raw JSON chunks from the /api/chat endpoint.
        """
        client = self.get_client()
        ollama_messages = self._format_messages(messages)
        request_data = {
            "model": model or self.model,
            "messages": ollama_messages,
            "stream": True,
            "options": {
                "num_predict": max_tokens,
                "temperature": kwargs.get("temperature", 0.7),
            },
        }
        if kwargs.get("stop"):
            request_data["options"]["stop"] = kwargs["stop"]

        async with client.stream("POST", "/api/chat", json=request_data) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    try:
                        yield json.loads(line)
                    except json.JSONDecodeError:
                        continue

    async def list_models(self) -> list[dict]:
        """List available local models from Ollama."""
        try:
            data = await self._make_request("/api/tags")
            return data.get("models", [])
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    async def check_connection(self) -> bool:
        """Check whether the Ollama server is reachable."""
        try:
            await self._make_request("/api/version")
            return True
        except Exception:
            return False

    async def pull_model(self, model: str) -> dict:
        """Pull a model from the Ollama library."""
        try:
            return await self._make_request("/api/pull", method="POST", json={"name": model})
        except Exception as e:
            logger.error(f"Failed to pull model {model}: {e}")
            return {"status": "error", "error": str(e)}

    def get_client(self) -> httpx.AsyncClient:
        """Get HTTP client for Ollama"""
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=300.0)
        return self._client

    async def stream(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        max_tokens: int = 4096,
        **kwargs,
    ) -> AsyncIterator[LLMResponse]:
        """Stream responses from Ollama"""
        client = self.get_client()

        # Convert messages to Ollama format
        ollama_messages = []
        for msg in messages:
            ollama_messages.append({"role": msg.role, "content": msg.content})

        try:
            # Build request
            request_data = {
                "model": self.model,
                "messages": ollama_messages,
                "stream": True,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": kwargs.get("temperature", 0.7),
                },
            }

            # Stream request
            async with client.stream("POST", "/api/chat", json=request_data) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    try:
                        chunk = json.loads(line)

                        # Text content
                        if "message" in chunk:
                            content = chunk["message"].get("content", "")
                            if content:
                                yield LLMResponse(type="text_delta", content=content)

                        # Check if done
                        if chunk.get("done"):
                            yield LLMResponse(type="done", content=None, finish_reason="stop")
                            break

                    except json.JSONDecodeError:
                        continue

        except httpx.HTTPError as e:
            logger.error(f"Ollama HTTP error: {e}")
            yield LLMResponse(type="error", content=f"Ollama error: {str(e)}")
        except Exception as e:
            logger.error(f"Ollama streaming error: {e}")
            yield LLMResponse(type="error", content=str(e))
