"""
Live tests for token estimation accuracy.

Compares estimated tokens with actual model usage.
Requires a running gateway and model access.
"""
import pytest
import asyncio
import json
import websockets
from openclaw.agents.context import estimate_tokens_from_text, estimate_tokens_from_messages


# Test data
TEST_PROMPTS = [
    "Short message",
    "Hello, how are you today? I'm doing well, thank you for asking!",
    "x" * 1000,  # Long repeated text
    "Mixed 中文 and English content with numbers 123 and symbols !@#$",
    """
    Multi-line text
    with various content types:
    - Code: def hello(): return "world"
    - Numbers: 12345
    - Unicode: 你好世界
    """,
]


@pytest.mark.asyncio
@pytest.mark.integration
async def test_token_estimation_accuracy():
    """
    Test token estimation accuracy by comparing with actual model usage.
    
    This test:
    1. Estimates tokens using our function
    2. Sends to actual model via gateway
    3. Compares estimated vs actual usage
    4. Verifies accuracy within acceptable range (±20%)
    """
    gateway_url = "ws://localhost:3100"
    
    results = []
    
    try:
        async with websockets.connect(gateway_url) as ws:
            # Authenticate
            auth_msg = {
                "method": "session.create",
                "id": 1,
                "payload": {"key": "test-token-accuracy"}
            }
            await ws.send(json.dumps(auth_msg))
            auth_resp = await ws.recv()
            auth_data = json.loads(auth_resp)
            
            if auth_data.get("error"):
                pytest.skip(f"Gateway authentication failed: {auth_data['error']}")
                return
            
            session_id = auth_data.get("payload", {}).get("session_id")
            
            # Test each prompt
            for i, prompt in enumerate(TEST_PROMPTS):
                # Estimate tokens
                estimated = estimate_tokens_from_text(prompt)
                
                # Send to model
                request_id = 100 + i
                request_msg = {
                    "method": "chat.send",
                    "id": request_id,
                    "payload": {
                        "session_id": session_id,
                        "message": prompt,
                    }
                }
                await ws.send(json.dumps(request_msg))
                
                # Collect response and usage
                actual_tokens = None
                while True:
                    resp = await asyncio.wait_for(ws.recv(), timeout=30.0)
                    data = json.loads(resp)
                    
                    if data.get("id") != request_id:
                        continue
                    
                    if data.get("method") == "agent.done":
                        # Extract usage from final response
                        payload = data.get("payload", {})
                        usage = payload.get("usage", {})
                        actual_tokens = usage.get("total_tokens") or usage.get("totalTokens")
                        break
                    
                    if data.get("error"):
                        pytest.skip(f"Model request failed: {data['error']}")
                        return
                
                if actual_tokens:
                    error_ratio = abs(estimated - actual_tokens) / actual_tokens if actual_tokens > 0 else 0
                    
                    results.append({
                        "prompt": prompt[:50] + "..." if len(prompt) > 50 else prompt,
                        "estimated": estimated,
                        "actual": actual_tokens,
                        "error_ratio": error_ratio,
                        "within_20_percent": error_ratio < 0.2,
                    })
    
    except (websockets.exceptions.WebSocketException, OSError) as e:
        pytest.skip(f"Gateway not available: {e}")
        return
    except asyncio.TimeoutError:
        pytest.skip("Gateway request timed out")
        return
    
    # Analyze results
    if not results:
        pytest.skip("No results collected")
        return
    
    print("\n\nToken Estimation Accuracy Results:")
    print("=" * 80)
    for r in results:
        status = "✓" if r["within_20_percent"] else "✗"
        print(f"{status} Prompt: {r['prompt']}")
        print(f"  Estimated: {r['estimated']}, Actual: {r['actual']}, Error: {r['error_ratio']:.1%}")
    print("=" * 80)
    
    # Calculate overall statistics
    avg_error = sum(r["error_ratio"] for r in results) / len(results)
    within_20_count = sum(1 for r in results if r["within_20_percent"])
    
    print(f"\nOverall Statistics:")
    print(f"  Average Error: {avg_error:.1%}")
    print(f"  Within 20%: {within_20_count}/{len(results)} ({within_20_count/len(results):.1%})")
    
    # Assert that most estimates are within 20%
    assert within_20_count >= len(results) * 0.7, (
        f"Too many estimates outside 20% range: {within_20_count}/{len(results)}"
    )
    
    # Assert average error is reasonable
    assert avg_error < 0.3, f"Average error too high: {avg_error:.1%}"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_message_list_token_estimation():
    """Test token estimation for message lists"""
    gateway_url = "ws://localhost:3100"
    
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there! How can I help you today?"},
        {"role": "user", "content": "What's the weather like?"},
    ]
    
    # Estimate tokens
    estimated = estimate_tokens_from_messages(messages)
    
    try:
        async with websockets.connect(gateway_url) as ws:
            # Authenticate
            auth_msg = {
                "method": "session.create",
                "id": 1,
                "payload": {"key": "test-msg-accuracy"}
            }
            await ws.send(json.dumps(auth_msg))
            auth_resp = await ws.recv()
            auth_data = json.loads(auth_resp)
            
            if auth_data.get("error"):
                pytest.skip(f"Gateway authentication failed: {auth_data['error']}")
                return
            
            session_id = auth_data.get("payload", {}).get("session_id")
            
            # Send conversation
            for msg in messages:
                if msg["role"] == "user":
                    request_msg = {
                        "method": "chat.send",
                        "id": 200,
                        "payload": {
                            "session_id": session_id,
                            "message": msg["content"],
                        }
                    }
                    await ws.send(json.dumps(request_msg))
                    
                    # Wait for response
                    while True:
                        resp = await asyncio.wait_for(ws.recv(), timeout=30.0)
                        data = json.loads(resp)
                        if data.get("method") == "agent.done":
                            break
            
            # Get final usage
            # (In real implementation, would accumulate usage across turns)
            
            print(f"\nMessage List Estimation:")
            print(f"  Estimated tokens: {estimated}")
            print(f"  (Actual usage would be retrieved from model)")
    
    except (websockets.exceptions.WebSocketException, OSError) as e:
        pytest.skip(f"Gateway not available: {e}")
        return
    except asyncio.TimeoutError:
        pytest.skip("Gateway request timed out")
        return


def test_token_estimation_vs_simple_method():
    """Compare new estimation method with old simple method"""
    test_texts = [
        "Short",
        "Medium length text with some words",
        "x" * 1000,
        "Unicode 你好世界 content",
    ]
    
    for text in test_texts:
        # New method
        new_estimate = estimate_tokens_from_text(text)
        
        # Old method (chars // 4)
        old_estimate = len(text) // 4
        
        print(f"\nText: {text[:30]}...")
        print(f"  New estimate: {new_estimate}")
        print(f"  Old estimate: {old_estimate}")
        print(f"  Difference: {new_estimate - old_estimate} tokens")
        
        # New method should generally give higher estimates (more conservative)
        # due to buffer ratio
        assert new_estimate >= old_estimate * 0.8  # Within reasonable range


if __name__ == "__main__":
    # Run with: pytest test_token_accuracy_live.py -v -s
    pytest.main([__file__, "-v", "-s", "-m", "integration"])
