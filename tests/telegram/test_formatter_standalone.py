"""Standalone tests for formatter module.

Tests Markdown to HTML conversion without full package imports.
"""

import pytest
import sys
from pathlib import Path

# Add the openclaw directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Direct import of formatter module
from openclaw.channels.telegram import formatter


class TestEscapeHtml:
    """Test HTML escaping."""
    
    def test_escape_basic_entities(self):
        """Test escaping basic HTML entities."""
        assert formatter.escape_html("<div>") == "&lt;div&gt;"
        assert formatter.escape_html("a & b") == "a &amp; b"
    
    def test_no_escape_needed(self):
        """Test text with no entities."""
        assert formatter.escape_html("Hello World") == "Hello World"


class TestMarkdownToHtml:
    """Test Markdown to HTML conversion."""
    
    def test_bold_conversion(self):
        """Test bold text conversion."""
        result = formatter.markdown_to_html("**bold**")
        assert "<b>bold</b>" in result
    
    def test_inline_code_conversion(self):
        """Test inline code conversion."""
        result = formatter.markdown_to_html("`code`")
        assert "<code>code</code>" in result
    
    def test_link_conversion(self):
        """Test link conversion."""
        result = formatter.markdown_to_html("[Google](https://google.com)")
        assert '<a href=' in result
        assert 'Google' in result
    
    def test_html_escaping_in_text(self):
        """Test HTML is escaped in regular text."""
        result = formatter.markdown_to_html("This has <script> tags")
        assert "&lt;script&gt;" in result
        assert "<script>" not in result
    
    def test_empty_text(self):
        """Test empty text returns empty."""
        assert formatter.markdown_to_html("") == ""


class TestChunkMessage:
    """Test message chunking."""
    
    def test_short_message_no_chunking(self):
        """Test short message returns single chunk."""
        text = "Hello World"
        chunks = formatter.chunk_message(text, max_length=100)
        assert len(chunks) == 1
        assert chunks[0] == text
    
    def test_long_message_chunking(self):
        """Test long message gets chunked."""
        text = "a" * 5000
        chunks = formatter.chunk_message(text, max_length=4096)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= 4096


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
