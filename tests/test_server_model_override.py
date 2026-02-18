from __future__ import annotations

from openclaw.api.server import _extract_model_override


def test_extract_model_override_valid_string():
    assert (
        _extract_model_override({"model": " google/gemini-3-flash-preview "})
        == "google/gemini-3-flash-preview"
    )


def test_extract_model_override_invalid_values():
    assert _extract_model_override(None) is None
    assert _extract_model_override({}) is None
    assert _extract_model_override({"model": "   "}) is None
    assert _extract_model_override({"model": 123}) is None
