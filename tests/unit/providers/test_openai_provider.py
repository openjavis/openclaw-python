"""Unit tests for OpenAI provider."""

import json

from openclaw.agents.providers.base import LLMMessage
from openclaw.agents.providers.openai_provider import OpenAIProvider


def test_openai_imports():
    """Test OpenAI provider imports."""
    assert OpenAIProvider is not None


def test_convert_messages_preserves_tool_schema_and_ids():
    provider = OpenAIProvider("openai/gpt-4o")

    messages = [
        LLMMessage(
            role="assistant",
            content="",
            tool_calls=[
                {
                    "id": "call_1",
                    "name": "bash",
                    "arguments": {"command": "pwd"},
                }
            ],
        ),
        LLMMessage(
            role="tool",
            content="/home/mm",
            tool_call_id="call_1",
            name="bash",
        ),
    ]

    converted = provider._convert_messages(messages)

    assert converted[0]["role"] == "assistant"
    assert converted[0]["tool_calls"][0]["id"] == "call_1"
    assert converted[0]["tool_calls"][0]["function"]["name"] == "bash"
    assert json.loads(converted[0]["tool_calls"][0]["function"]["arguments"]) == {"command": "pwd"}

    assert converted[1]["role"] == "tool"
    assert converted[1]["tool_call_id"] == "call_1"
    assert converted[1]["content"] == "/home/mm"


def test_convert_messages_drops_tool_without_tool_call_id():
    provider = OpenAIProvider("openai/gpt-4o")

    messages = [
        LLMMessage(role="user", content="hello"),
        LLMMessage(role="tool", content="orphan tool result", tool_call_id=None, name="bash"),
    ]

    converted = provider._convert_messages(messages)

    assert len(converted) == 1
    assert converted[0] == {"role": "user", "content": "hello"}


def test_convert_messages_supports_openai_function_shape_input():
    provider = OpenAIProvider("openai/gpt-4o")

    messages = [
        LLMMessage(
            role="assistant",
            content=None,
            tool_calls=[
                {
                    "id": "call_2",
                    "function": {
                        "name": "read",
                        "arguments": '{"path":"/tmp/test.txt"}',
                    },
                }
            ],
        ),
    ]

    converted = provider._convert_messages(messages)

    assert converted[0]["tool_calls"][0]["function"]["name"] == "read"
    assert converted[0]["tool_calls"][0]["function"]["arguments"] == '{"path":"/tmp/test.txt"}'
