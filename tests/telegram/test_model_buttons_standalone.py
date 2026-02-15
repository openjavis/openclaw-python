"""Standalone tests for model_buttons module."""

import pytest
import sys
from pathlib import Path

# Add openclaw to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from openclaw.telegram import model_buttons


class TestParseModelCallbackData:
    """Test model callback data parsing."""
    
    def test_parse_providers_callback(self):
        """Test parsing providers callback."""
        result = model_buttons.parse_model_callback_data("mdl_prov")
        assert result is not None
        assert result["type"] == "providers"
    
    def test_parse_back_callback(self):
        """Test parsing back callback."""
        result = model_buttons.parse_model_callback_data("mdl_back")
        assert result is not None
        assert result["type"] == "back"
    
    def test_parse_list_callback(self):
        """Test parsing list callback."""
        result = model_buttons.parse_model_callback_data("mdl_list_anthropic_1")
        assert result is not None
        assert result["type"] == "list"
        assert result["provider"] == "anthropic"
        assert result["page"] == 1
    
    def test_parse_select_callback(self):
        """Test parsing select callback."""
        result = model_buttons.parse_model_callback_data("mdl_sel_anthropic/claude-3-opus")
        assert result is not None
        assert result["type"] == "select"
        assert result["provider"] == "anthropic"
        assert result["model"] == "claude-3-opus"
    
    def test_parse_invalid_callback(self):
        """Test parsing invalid callback returns None."""
        assert model_buttons.parse_model_callback_data("invalid_data") is None
        assert model_buttons.parse_model_callback_data("mdl_") is None
        assert model_buttons.parse_model_callback_data("") is None


class TestBuildProviderKeyboard:
    """Test provider keyboard building."""
    
    def test_empty_providers(self):
        """Test empty providers list."""
        keyboard = model_buttons.build_provider_keyboard([])
        assert keyboard == []
    
    def test_single_provider(self):
        """Test single provider."""
        providers = [model_buttons.ProviderInfo(id="anthropic", count=5)]
        keyboard = model_buttons.build_provider_keyboard(providers)
        
        assert len(keyboard) == 1
        assert len(keyboard[0]) == 1
        assert "anthropic" in keyboard[0][0]["text"]
        assert "(5)" in keyboard[0][0]["text"]


class TestCalculateTotalPages:
    """Test total pages calculation."""
    
    def test_zero_items(self):
        """Test zero items returns 1 page."""
        assert model_buttons.calculate_total_pages(0) == 1
    
    def test_exact_page_size(self):
        """Test items exactly matching page size."""
        assert model_buttons.calculate_total_pages(8, page_size=8) == 1
        assert model_buttons.calculate_total_pages(16, page_size=8) == 2
    
    def test_partial_page(self):
        """Test items requiring partial page."""
        assert model_buttons.calculate_total_pages(9, page_size=8) == 2
        assert model_buttons.calculate_total_pages(15, page_size=8) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
