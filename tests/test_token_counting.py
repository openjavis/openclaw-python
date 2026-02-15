"""
Unit tests for token counting functionality.

Tests the improved token estimation using CHARS_PER_TOKEN_ESTIMATE and TOKEN_BUFFER_RATIO.
"""
import pytest
from openclaw.agents.context import (
    estimate_tokens_from_text,
    estimate_tokens_from_messages,
    CHARS_PER_TOKEN_ESTIMATE,
    TOKEN_BUFFER_RATIO,
)


def test_token_estimation_empty_text():
    """Test token estimation with empty text"""
    assert estimate_tokens_from_text("") == 0
    assert estimate_tokens_from_text(None) == 0


def test_token_estimation_short_text():
    """Test token estimation with short text"""
    text = "Hello world"
    estimated = estimate_tokens_from_text(text)
    
    # Should be approximately 3-4 tokens (with buffer)
    assert 2 <= estimated <= 6, f"Expected 2-6 tokens, got {estimated}"


def test_token_estimation_long_text():
    """Test token estimation with long text"""
    text = "a" * 1000
    estimated = estimate_tokens_from_text(text)
    
    # Expected: 1000 / 3.5 * 1.1 = ~314 tokens
    expected = int(1000 / CHARS_PER_TOKEN_ESTIMATE * TOKEN_BUFFER_RATIO)
    assert abs(estimated - expected) < 10, f"Expected ~{expected} tokens, got {estimated}"


def test_token_estimation_unicode():
    """Test token estimation with Unicode text"""
    text = "你好世界"
    estimated = estimate_tokens_from_text(text)
    
    # Unicode characters count as 1 char each in Python len()
    # Should be approximately 4 chars / 3.5 * 1.1 = ~1-2 tokens
    assert estimated >= 1, f"Expected at least 1 token, got {estimated}"


def test_token_estimation_mixed_content():
    """Test token estimation with mixed English and Unicode"""
    text = "Mixed 中文 and English content with numbers 123"
    estimated = estimate_tokens_from_text(text)
    
    # Calculate expected
    char_count = len(text)
    expected = int(char_count / CHARS_PER_TOKEN_ESTIMATE * TOKEN_BUFFER_RATIO)
    
    # Should be within reasonable range
    assert abs(estimated - expected) < 5, f"Expected ~{expected} tokens, got {estimated}"


def test_token_buffer():
    """Test that token buffer provides safety margin"""
    text = "x" * 1000
    estimated = estimate_tokens_from_text(text)
    
    # Should be more conservative than simple chars // 4
    simple_estimate = len(text) // 4
    
    # Our estimate should be higher due to buffer
    assert estimated > simple_estimate, (
        f"Buffered estimate ({estimated}) should be > simple estimate ({simple_estimate})"
    )


def test_token_estimation_from_messages_empty():
    """Test token estimation from empty message list"""
    messages = []
    assert estimate_tokens_from_messages(messages) == 0


def test_token_estimation_from_messages():
    """Test token estimation from message list"""
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
    
    estimated = estimate_tokens_from_messages(messages)
    
    # Should estimate tokens for entire message structure
    assert estimated > 0
    
    # Should be more than just content tokens (includes role, structure, etc.)
    content_only = estimate_tokens_from_text("Hello Hi there!")
    assert estimated > content_only


def test_token_estimation_consistency():
    """Test that token estimation is consistent"""
    text = "This is a test message with consistent content."
    
    # Call multiple times
    estimate1 = estimate_tokens_from_text(text)
    estimate2 = estimate_tokens_from_text(text)
    estimate3 = estimate_tokens_from_text(text)
    
    # Should always return same result
    assert estimate1 == estimate2 == estimate3


def test_token_estimation_proportional():
    """Test that token estimation scales proportionally"""
    short_text = "Hello"
    long_text = short_text * 10  # 10x longer
    
    short_estimate = estimate_tokens_from_text(short_text)
    long_estimate = estimate_tokens_from_text(long_text)
    
    # Long text should have ~10x more tokens (with some tolerance)
    ratio = long_estimate / short_estimate if short_estimate > 0 else 0
    assert 8 <= ratio <= 12, f"Expected ratio ~10, got {ratio}"


def test_token_estimation_accuracy_range():
    """Test token estimation accuracy within acceptable range"""
    test_cases = [
        ("Hello world", 2, 5),  # Expected 2-5 tokens
        ("a" * 1000, 250, 350),  # Expected 250-350 tokens
        ("你好世界", 1, 4),  # Expected 1-4 tokens
        ("The quick brown fox jumps over the lazy dog", 10, 16),  # ~13 tokens
    ]
    
    for text, min_expected, max_expected in test_cases:
        estimated = estimate_tokens_from_text(text)
        assert min_expected <= estimated <= max_expected, (
            f"Text '{text[:20]}...' estimated {estimated} tokens, "
            f"expected {min_expected}-{max_expected}"
        )


def test_token_estimation_with_special_characters():
    """Test token estimation with special characters"""
    text = "Special chars: !@#$%^&*()_+-=[]{}|;:',.<>?/~`"
    estimated = estimate_tokens_from_text(text)
    
    # Should handle special characters gracefully
    assert estimated > 0
    
    # Calculate expected
    char_count = len(text)
    expected = int(char_count / CHARS_PER_TOKEN_ESTIMATE * TOKEN_BUFFER_RATIO)
    assert abs(estimated - expected) < 5


def test_token_estimation_with_whitespace():
    """Test token estimation with various whitespace"""
    text = "Text   with    multiple     spaces\n\nand\n\nnewlines\t\tand\ttabs"
    estimated = estimate_tokens_from_text(text)
    
    # Should count whitespace characters
    assert estimated > 0
    
    char_count = len(text)
    expected = int(char_count / CHARS_PER_TOKEN_ESTIMATE * TOKEN_BUFFER_RATIO)
    assert abs(estimated - expected) < 5


def test_token_estimation_code():
    """Test token estimation with code"""
    code = """
def hello_world():
    print("Hello, world!")
    return True
"""
    estimated = estimate_tokens_from_text(code)
    
    # Code should be estimated like any other text
    assert estimated > 0
    
    char_count = len(code)
    expected = int(char_count / CHARS_PER_TOKEN_ESTIMATE * TOKEN_BUFFER_RATIO)
    assert abs(estimated - expected) < 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
