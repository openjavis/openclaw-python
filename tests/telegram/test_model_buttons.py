"""Unit tests for openclaw.telegram.model_buttons module.

Tests model selection keyboard building and callback parsing.
"""

import pytest
from openclaw.telegram.model_buttons import (
    parse_model_callback_data,
    build_provider_keyboard,
    build_models_keyboard,
    calculate_total_pages,
    get_models_page_size,
    ProviderInfo,
    ModelsKeyboardParams,
)


class TestParseModelCallbackData:
    """Test model callback data parsing."""
    
    def test_parse_providers_callback(self):
        """Test parsing providers callback."""
        result = parse_model_callback_data("mdl_prov")
        assert result is not None
        assert result["type"] == "providers"
    
    def test_parse_back_callback(self):
        """Test parsing back callback."""
        result = parse_model_callback_data("mdl_back")
        assert result is not None
        assert result["type"] == "back"
    
    def test_parse_list_callback(self):
        """Test parsing list callback."""
        result = parse_model_callback_data("mdl_list_anthropic_1")
        assert result is not None
        assert result["type"] == "list"
        assert result["provider"] == "anthropic"
        assert result["page"] == 1
    
    def test_parse_select_callback(self):
        """Test parsing select callback."""
        result = parse_model_callback_data("mdl_sel_anthropic/claude-3-opus")
        assert result is not None
        assert result["type"] == "select"
        assert result["provider"] == "anthropic"
        assert result["model"] == "claude-3-opus"
    
    def test_parse_invalid_callback(self):
        """Test parsing invalid callback returns None."""
        assert parse_model_callback_data("invalid_data") is None
        assert parse_model_callback_data("mdl_") is None
        assert parse_model_callback_data("") is None
    
    def test_parse_list_with_invalid_page(self):
        """Test parsing list with invalid page."""
        result = parse_model_callback_data("mdl_list_anthropic_0")
        # Page 0 is invalid (should be >= 1)
        assert result is None
    
    def test_parse_select_without_slash(self):
        """Test parsing select without slash."""
        result = parse_model_callback_data("mdl_sel_anthropic")
        assert result is None  # Missing slash separator


class TestBuildProviderKeyboard:
    """Test provider keyboard building."""
    
    def test_empty_providers(self):
        """Test empty providers list."""
        keyboard = build_provider_keyboard([])
        assert keyboard == []
    
    def test_single_provider(self):
        """Test single provider."""
        providers = [ProviderInfo(id="anthropic", count=5)]
        keyboard = build_provider_keyboard(providers)
        
        assert len(keyboard) == 1
        assert len(keyboard[0]) == 1
        assert "anthropic" in keyboard[0][0]["text"]
        assert "(5)" in keyboard[0][0]["text"]
        assert keyboard[0][0]["callback_data"] == "mdl_list_anthropic_1"
    
    def test_two_providers_one_row(self):
        """Test two providers fit in one row."""
        providers = [
            ProviderInfo(id="anthropic", count=5),
            ProviderInfo(id="openai", count=8),
        ]
        keyboard = build_provider_keyboard(providers)
        
        assert len(keyboard) == 1
        assert len(keyboard[0]) == 2
    
    def test_three_providers_two_rows(self):
        """Test three providers split into two rows."""
        providers = [
            ProviderInfo(id="anthropic", count=5),
            ProviderInfo(id="openai", count=8),
            ProviderInfo(id="google", count=4),
        ]
        keyboard = build_provider_keyboard(providers)
        
        assert len(keyboard) == 2
        assert len(keyboard[0]) == 2
        assert len(keyboard[1]) == 1


class TestCalculateTotalPages:
    """Test total pages calculation."""
    
    def test_zero_items(self):
        """Test zero items returns 1 page."""
        assert calculate_total_pages(0) == 1
    
    def test_exact_page_size(self):
        """Test items exactly matching page size."""
        assert calculate_total_pages(8, page_size=8) == 1
        assert calculate_total_pages(16, page_size=8) == 2
    
    def test_partial_page(self):
        """Test items requiring partial page."""
        assert calculate_total_pages(9, page_size=8) == 2
        assert calculate_total_pages(15, page_size=8) == 2
        assert calculate_total_pages(17, page_size=8) == 3


class TestGetModelsPageSize:
    """Test getting models page size."""
    
    def test_page_size_is_8(self):
        """Test page size is 8."""
        assert get_models_page_size() == 8


class TestBuildModelsKeyboard:
    """Test models keyboard building."""
    
    def test_empty_models(self):
        """Test empty models list."""
        params = ModelsKeyboardParams(
            provider="anthropic",
            models=[],
            current_page=1,
            total_pages=1,
        )
        keyboard = build_models_keyboard(params)
        
        # Should have at least back button
        assert len(keyboard) >= 1
        assert any("Back" in btn["text"] for row in keyboard for btn in row)
    
    def test_single_page_models(self):
        """Test single page of models."""
        models = ["model-1", "model-2", "model-3"]
        params = ModelsKeyboardParams(
            provider="anthropic",
            models=models,
            current_page=1,
            total_pages=1,
        )
        keyboard = build_models_keyboard(params)
        
        # Should have 3 model buttons + back button
        model_buttons = [row for row in keyboard if not any("Back" in btn["text"] for btn in row)]
        assert len(model_buttons) == 3
    
    def test_multiple_pages_models(self):
        """Test multiple pages of models."""
        models = [f"model-{i}" for i in range(20)]
        params = ModelsKeyboardParams(
            provider="anthropic",
            models=models,
            current_page=1,
            total_pages=3,
            page_size=8,
        )
        keyboard = build_models_keyboard(params)
        
        # Should have pagination row
        has_pagination = any(
            any("Prev" in btn["text"] or "Next" in btn["text"] for btn in row)
            for row in keyboard
        )
        assert has_pagination
    
    def test_current_model_marked(self):
        """Test current model is marked with checkmark."""
        models = ["model-1", "model-2", "model-3"]
        params = ModelsKeyboardParams(
            provider="anthropic",
            models=models,
            current_model="model-2",
            current_page=1,
            total_pages=1,
        )
        keyboard = build_models_keyboard(params)
        
        # Find model-2 button
        model2_button = None
        for row in keyboard:
            for btn in row:
                if "model-2" in btn["text"]:
                    model2_button = btn
                    break
        
        assert model2_button is not None
        assert "✓" in model2_button["text"]
    
    def test_pagination_buttons(self):
        """Test pagination buttons for middle page."""
        models = [f"model-{i}" for i in range(20)]
        params = ModelsKeyboardParams(
            provider="anthropic",
            models=models,
            current_page=2,
            total_pages=3,
            page_size=8,
        )
        keyboard = build_models_keyboard(params)
        
        # Should have both Prev and Next buttons
        pagination_row = None
        for row in keyboard:
            if any("Prev" in btn["text"] or "Next" in btn["text"] for btn in row):
                pagination_row = row
                break
        
        assert pagination_row is not None
        assert any("Prev" in btn["text"] for btn in pagination_row)
        assert any("Next" in btn["text"] for btn in pagination_row)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
