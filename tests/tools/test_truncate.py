"""Tests for truncation utilities"""
import pytest

from openclaw.agents.tools.truncate import (
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_LINES,
    truncate_head,
    truncate_tail,
    truncate_string_to_bytes_from_end,
    format_size,
)


def test_truncate_head_no_truncation():
    """Test that small content is not truncated"""
    content = "line 1\nline 2\nline 3"
    result = truncate_head(content)
    
    assert not result.truncated
    assert result.content == content
    assert result.total_lines == 3
    assert result.output_lines == 3


def test_truncate_head_by_lines():
    """Test truncation by line limit"""
    lines = [f"line {i}" for i in range(2500)]
    content = "\n".join(lines)
    
    result = truncate_head(content)
    
    assert result.truncated
    assert result.truncated_by == "lines"
    assert result.output_lines == DEFAULT_MAX_LINES
    assert result.total_lines == 2500


def test_truncate_head_by_bytes():
    """Test truncation by byte limit"""
    # Create content that exceeds byte limit but not line limit
    large_line = "x" * (DEFAULT_MAX_BYTES // 10)
    lines = [large_line for i in range(15)]
    content = "\n".join(lines)
    
    result = truncate_head(content)
    
    assert result.truncated
    assert result.truncated_by == "bytes"
    assert result.output_bytes <= DEFAULT_MAX_BYTES


def test_truncate_head_first_line_exceeds_limit():
    """Test case where first line alone exceeds byte limit"""
    content = "x" * (DEFAULT_MAX_BYTES + 1000)
    
    result = truncate_head(content)
    
    assert result.truncated
    assert result.first_line_exceeds_limit
    assert result.content == ""
    assert result.output_lines == 0


def test_truncate_tail_no_truncation():
    """Test that small content is not truncated"""
    content = "line 1\nline 2\nline 3"
    result = truncate_tail(content)
    
    assert not result.truncated
    assert result.content == content
    assert result.total_lines == 3
    assert result.output_lines == 3


def test_truncate_tail_by_lines():
    """Test tail truncation by line limit"""
    lines = [f"line {i}" for i in range(2500)]
    content = "\n".join(lines)
    
    result = truncate_tail(content)
    
    assert result.truncated
    assert result.truncated_by == "lines"
    assert result.output_lines == DEFAULT_MAX_LINES
    # Should keep last 2000 lines
    assert "line 2499" in result.content
    assert "line 500" in result.content
    assert "line 499" not in result.content


def test_truncate_tail_by_bytes():
    """Test tail truncation by byte limit"""
    # Create content that exceeds byte limit
    large_line = "x" * (DEFAULT_MAX_BYTES // 10)
    lines = [large_line for i in range(15)]
    content = "\n".join(lines)
    
    result = truncate_tail(content)
    
    assert result.truncated
    assert result.truncated_by == "bytes"
    assert result.output_bytes <= DEFAULT_MAX_BYTES


def test_truncate_tail_last_line_partial():
    """Test tail truncation when last line alone exceeds limit"""
    content = "x" * (DEFAULT_MAX_BYTES + 1000)
    
    result = truncate_tail(content)
    
    assert result.truncated
    assert result.last_line_partial
    assert result.output_bytes <= DEFAULT_MAX_BYTES


def test_truncate_string_to_bytes_from_end():
    """Test UTF-8 safe truncation from end"""
    text = "Hello 世界 World"
    
    # Truncate to 10 bytes
    result = truncate_string_to_bytes_from_end(text, 10)
    
    # Should be valid UTF-8
    assert isinstance(result, str)
    # Should be at most 10 bytes
    assert len(result.encode('utf-8')) <= 10


def test_truncate_string_utf8_safety():
    """Test that UTF-8 multibyte characters are handled correctly"""
    # Chinese characters are 3 bytes each in UTF-8
    text = "世界你好"  # 12 bytes total
    
    # Truncate to 7 bytes (would cut in middle of character)
    result = truncate_string_to_bytes_from_end(text, 7)
    
    # Should produce valid UTF-8 (may be shorter than 7 bytes to avoid breaking char)
    result.encode('utf-8')  # Should not raise
    assert len(result.encode('utf-8')) <= 7


def test_format_size():
    """Test size formatting"""
    assert format_size(500) == "500B"
    assert format_size(1024) == "1.0KB"
    assert format_size(1536) == "1.5KB"
    assert format_size(1024 * 1024) == "1.0MB"
    assert format_size(1024 * 1024 * 1.5) == "1.5MB"
