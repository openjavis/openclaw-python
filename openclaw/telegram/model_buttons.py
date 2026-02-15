"""Telegram inline button utilities for model selection.

Callback data patterns (max 64 bytes for Telegram):
- mdl_prov              - show providers list
- mdl_list_{prov}_{pg}  - show models for provider (page N, 1-indexed)
- mdl_sel_{provider/id} - select model
- mdl_back              - back to providers list

Matches TypeScript src/telegram/model-buttons.ts
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Optional, TypedDict

# Telegram limits
MAX_CALLBACK_DATA_BYTES = 64
MODELS_PAGE_SIZE = 8


class ParsedModelCallback(TypedDict, total=False):
    """Parsed model callback data."""

    type: Literal["providers", "list", "select", "back"]
    provider: Optional[str]
    page: Optional[int]
    model: Optional[str]


@dataclass
class ProviderInfo:
    """Provider information."""

    id: str
    count: int


@dataclass
class ModelsKeyboardParams:
    """Parameters for building models keyboard."""

    provider: str
    models: list[str]
    current_model: Optional[str] = None
    current_page: int = 1
    total_pages: int = 1
    page_size: int = MODELS_PAGE_SIZE


ButtonRow = list[dict[str, str]]  # List of {"text": str, "callback_data": str}


def parse_model_callback_data(data: str) -> Optional[ParsedModelCallback]:
    """Parse a model callback_data string into a structured object.

    Args:
        data: Callback data string

    Returns:
        Parsed callback dict or None if invalid
    """
    trimmed = data.strip()
    if not trimmed.startswith("mdl_"):
        return None

    if trimmed == "mdl_prov" or trimmed == "mdl_back":
        return {"type": "providers" if trimmed == "mdl_prov" else "back"}

    # mdl_list_{provider}_{page}
    list_match = re.match(r"^mdl_list_([a-z0-9_-]+)_(\d+)$", trimmed, re.IGNORECASE)
    if list_match:
        provider = list_match.group(1)
        page_str = list_match.group(2)
        try:
            page = int(page_str)
            if page >= 1:
                return {"type": "list", "provider": provider, "page": page}
        except ValueError:
            pass

    # mdl_sel_{provider/model}
    sel_match = re.match(r"^mdl_sel_(.+)$", trimmed)
    if sel_match:
        model_ref = sel_match.group(1)
        if "/" in model_ref:
            slash_index = model_ref.index("/")
            if 0 < slash_index < len(model_ref) - 1:
                provider = model_ref[:slash_index]
                model = model_ref[slash_index + 1 :]
                return {"type": "select", "provider": provider, "model": model}

    return None


def build_provider_keyboard(providers: list[ProviderInfo]) -> list[ButtonRow]:
    """Build provider selection keyboard with 2 providers per row.

    Args:
        providers: List of provider info

    Returns:
        Button rows for inline keyboard
    """
    if not providers:
        return []

    rows: list[ButtonRow] = []
    current_row: ButtonRow = []

    for provider in providers:
        button_text = f"{provider.id} ({provider.count})"
        # Use provider ID as callback data (short)
        callback_data = f"mdl_list_{provider.id}_1"

        # Validate callback data length
        if len(callback_data.encode("utf-8")) > MAX_CALLBACK_DATA_BYTES:
            # Provider ID too long, truncate or skip
            provider_id_short = provider.id[:20]  # Limit provider ID
            callback_data = f"mdl_list_{provider_id_short}_1"

        current_row.append({"text": button_text, "callback_data": callback_data})

        if len(current_row) >= 2:
            rows.append(current_row)
            current_row = []

    # Add remaining button
    if current_row:
        rows.append(current_row)

    return rows


def calculate_total_pages(total_items: int, page_size: int = MODELS_PAGE_SIZE) -> int:
    """Calculate total number of pages for pagination.

    Args:
        total_items: Total number of items
        page_size: Items per page

    Returns:
        Total pages (at least 1)
    """
    if total_items <= 0:
        return 1
    return (total_items + page_size - 1) // page_size


def get_models_page_size() -> int:
    """Get the page size for model listings.

    Returns:
        Models per page (default 8)
    """
    return MODELS_PAGE_SIZE


def build_models_keyboard(params: ModelsKeyboardParams) -> list[ButtonRow]:
    """Build models keyboard with pagination.

    Args:
        params: Keyboard parameters

    Returns:
        Button rows for inline keyboard
    """
    rows: list[ButtonRow] = []

    if not params.models:
        return rows

    # Calculate pagination
    start_idx = (params.current_page - 1) * params.page_size
    end_idx = start_idx + params.page_size
    page_models = params.models[start_idx:end_idx]

    # Add model buttons (one per row)
    for model in page_models:
        is_current = params.current_model == model
        button_text = f"{'✓ ' if is_current else ''}{model}"

        # Build callback data: mdl_sel_{provider/model}
        callback_data = f"mdl_sel_{params.provider}/{model}"

        # Validate callback data length
        if len(callback_data.encode("utf-8")) > MAX_CALLBACK_DATA_BYTES:
            # Too long, try to shorten model name
            max_model_len = MAX_CALLBACK_DATA_BYTES - len(f"mdl_sel_{params.provider}/")
            model_short = model[:max_model_len]
            callback_data = f"mdl_sel_{params.provider}/{model_short}"

        rows.append([{"text": button_text, "callback_data": callback_data}])

    # Add pagination row if needed
    if params.total_pages > 1:
        pagination_row: ButtonRow = []

        # Previous page button
        if params.current_page > 1:
            prev_page = params.current_page - 1
            pagination_row.append({
                "text": "◀ Prev",
                "callback_data": f"mdl_list_{params.provider}_{prev_page}",
            })

        # Page indicator
        pagination_row.append({
            "text": f"📄 {params.current_page}/{params.total_pages}",
            "callback_data": "mdl_noop",  # No-op
        })

        # Next page button
        if params.current_page < params.total_pages:
            next_page = params.current_page + 1
            pagination_row.append({
                "text": "Next ▶",
                "callback_data": f"mdl_list_{params.provider}_{next_page}",
            })

        rows.append(pagination_row)

    # Add back button
    rows.append([{"text": "« Back to Providers", "callback_data": "mdl_back"}])

    return rows
