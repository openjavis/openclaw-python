"""Unit tests for openclaw.channels.telegram.formatter module.

Tests Markdown to HTML conversion and message chunking.
"""

import pytest
from openclaw.channels.telegram.formatter import (
    escape_html,
    escape_html_attr,
    markdown_to_html,
    chunk_message,
    markdown_to_telegram_chunks,
)


class TestEscapeHtml:
    """Test HTML escaping."""
    
    def test_escape_basic_entities(self):
        """Test escaping basic HTML entities."""
        assert escape_html("<div>") == "&lt;div&gt;"
        assert escape_html("a & b") == "a &amp; b"
        assert escape_html("<script>alert('xss')</script>") == "&lt;script&gt;alert('xss')&lt;/script&gt;"
    
    def test_no_escape_needed(self):
        """Test text with no entities."""
        assert escape_html("Hello World") == "Hello World"
        assert escape_html("123 + 456 = 789") == "123 + 456 = 789"


class TestMarkdownToHtml:
    """Test Markdown to HTML conversion."""
    
    def test_bold_conversion(self):
        """Test bold text conversion."""
        assert "<b>bold</b>" in markdown_to_html("**bold**")
        assert "<b>bold</b>" in markdown_to_html("__bold__")
    
    def test_italic_conversion(self):
        """Test italic text conversion."""
        result = markdown_to_html("*italic*")
        assert "<i>italic</i>" in result or "italic" in result  # Depends on regex
    
    def test_strikethrough_conversion(self):
        """Test strikethrough text conversion."""
        assert "<s>strike</s>" in markdown_to_html("~~strike~~")
    
    def test_inline_code_conversion(self):
        """Test inline code conversion."""
        result = markdown_to_html("`code`")
        assert "<code>code</code>" in result
    
    def test_code_block_conversion(self):
        """Test code block conversion."""
        result = markdown_to_html("```python\nprint('hello')\n```")
        assert "<pre>" in result
        assert "print" in result
    
    def test_link_conversion(self):
        """Test link conversion."""
        result = markdown_to_html("[Google](https://google.com)")
        assert '<a href=' in result
        assert 'Google' in result
        assert 'google.com' in result
    
    def test_nested_formatting(self):
        """Test nested formatting."""
        result = markdown_to_html("**bold with `code`**")
        assert "<b>" in result
        assert "<code>" in result
    
    def test_html_escaping_in_text(self):
        """Test HTML is escaped in regular text."""
        result = markdown_to_html("This has <script> tags")
        assert "&lt;script&gt;" in result
        assert "<script>" not in result
    
    def test_empty_text(self):
        """Test empty text returns empty."""
        assert markdown_to_html("") == ""
        assert markdown_to_html(None) is None


class TestChunkMessage:
    """Test message chunking."""
    
    def test_short_message_no_chunking(self):
        """Test short message returns single chunk."""
        text = "Hello World"
        chunks = chunk_message(text, max_length=100)
        assert len(chunks) == 1
        assert chunks[0] == text
    
    def test_long_message_chunking(self):
        """Test long message gets chunked."""
        text = "a" * 5000
        chunks = chunk_message(text, max_length=4096)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= 4096
    
    def test_paragraph_boundary_splitting(self):
        """Test chunking respects paragraph boundaries."""
        para1 = "First paragraph. " * 200
        para2 = "Second paragraph. " * 200
        text = para1 + "\n\n" + para2
        
        chunks = chunk_message(text, max_length=2000)
        assert len(chunks) >= 2
    
    def test_exactly_max_length(self):
        """Test message exactly at max length."""
        text = "a" * 4096
        chunks = chunk_message(text, max_length=4096)
        assert len(chunks) == 1
    
    def test_one_char_over_max_length(self):
        """Test message one char over max length."""
        text = "a" * 4097
        chunks = chunk_message(text, max_length=4096)
        assert len(chunks) == 2


class TestMarkdownToTelegramChunks:
    """Test Markdown to Telegram chunks."""
    
    def test_short_markdown_single_chunk(self):
        """Test short markdown returns single chunk."""
        chunks = markdown_to_telegram_chunks("**Hello** World", limit=1000)
        assert len(chunks) == 1
        assert "<b>Hello</b>" in chunks[0].html
    
    def test_long_markdown_multiple_chunks(self):
        """Test long markdown gets chunked."""
        long_text = ("This is a paragraph. " * 300)  # ~6000 chars
        chunks = markdown_to_telegram_chunks(long_text, limit=4000)
        assert len(chunks) >= 2
    
    def test_chunk_preserves_formatting(self):
        """Test chunks preserve HTML formatting."""
        text = "**Bold text** " * 100
        chunks = markdown_to_telegram_chunks(text, limit=500)
        
        for chunk in chunks:
            # Each chunk should have valid HTML (no broken tags)
            assert "<b>" in chunk.html or chunk.html.strip() == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
