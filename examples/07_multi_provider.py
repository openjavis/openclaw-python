"""
Example: Using Multiple LLM Providers

This example shows how to use different LLM providers with ClawdBot:
- Anthropic Claude
- OpenAI GPT
- Google Gemini
- Ollama (local)
- AWS Bedrock
"""

import asyncio
import os

from clawdbot.agents.runtime import MultiProviderRuntime
from clawdbot.agents.session import Session


async def test_provider(name: str, model: str, **kwargs):
    """Test a specific provider"""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"Model: {model}")
    print(f"{'='*60}\n")

    try:
        runtime = MultiProviderRuntime(model=model, **kwargs)
        session = Session(f"{name}-test", "./workspace")

        message = "Say 'Hello from {provider}!' where provider is your name. Be brief."

        print("Response: ", end="", flush=True)

        async for event in runtime.run_turn(session, message, max_tokens=100):
            if event.type == "assistant":
                if "delta" in event.data and "text" in event.data["delta"]:
                    print(event.data["delta"]["text"], end="", flush=True)
            elif event.type == "error":
                print(f"\n❌ Error: {event.data.get('message')}")
                return False

        print("\n✅ Success!")
        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


async def main():
    """Test multiple providers"""

    print("=== Multi-Provider Test ===")
    print("\nThis example tests different LLM providers.")
    print("Make sure to set the required API keys as environment variables.\n")

    results = {}

    # 1. Anthropic Claude
    if os.getenv("ANTHROPIC_API_KEY"):
        results["Anthropic"] = await test_provider(
            "Anthropic Claude", "anthropic/claude-sonnet-4-5"
        )
    else:
        print("\n⚠️  Skipping Anthropic (no ANTHROPIC_API_KEY)")
        results["Anthropic"] = None

    # 2. OpenAI GPT
    if os.getenv("OPENAI_API_KEY"):
        results["OpenAI"] = await test_provider("OpenAI GPT", "openai/gpt-4")
    else:
        print("\n⚠️  Skipping OpenAI (no OPENAI_API_KEY)")
        results["OpenAI"] = None

    # 3. Google Gemini
    if os.getenv("GOOGLE_API_KEY"):
        results["Gemini"] = await test_provider("Google Gemini", "gemini/gemini-pro")
    else:
        print("\n⚠️  Skipping Gemini (no GOOGLE_API_KEY)")
        results["Gemini"] = None

    # 4. Ollama (local)
    # Note: Ollama must be running locally
    print("\n" + "=" * 60)
    print("Testing: Ollama (Local)")
    print("Note: This requires Ollama to be running locally")
    print("Install: https://ollama.ai")
    print("=" * 60)

    try:
        import httpx

        # Check if Ollama is running
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:11434/api/tags", timeout=2.0)
            if response.status_code == 200:
                results["Ollama"] = await test_provider(
                    "Ollama", "ollama/llama3", base_url="http://localhost:11434"
                )
            else:
                print("\n⚠️  Skipping Ollama (not running)")
                results["Ollama"] = None
    except Exception:
        print("\n⚠️  Skipping Ollama (not running or not installed)")
        results["Ollama"] = None

    # 5. AWS Bedrock
    # Note: Requires AWS credentials
    if os.getenv("AWS_ACCESS_KEY_ID"):
        results["Bedrock"] = await test_provider(
            "AWS Bedrock", "bedrock/anthropic.claude-3-sonnet-20240229-v1:0"
        )
    else:
        print("\n⚠️  Skipping Bedrock (no AWS credentials)")
        results["Bedrock"] = None

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    for provider, result in results.items():
        if result is True:
            status = "✅ PASS"
        elif result is False:
            status = "❌ FAIL"
        else:
            status = "⚠️  SKIP"

        print(f"{provider:15} {status}")

    print("\n" + "=" * 60)
    print("\nSupported Providers:")
    print("- Anthropic: Claude models (API key)")
    print("- OpenAI: GPT models (API key)")
    print("- Google: Gemini models (API key)")
    print("- Ollama: Local models (no API key needed)")
    print("- Bedrock: AWS Bedrock models (AWS credentials)")
    print("- Custom: Any OpenAI-compatible API")


if __name__ == "__main__":
    asyncio.run(main())
