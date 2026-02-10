"""Table formatting"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List


@dataclass
class TableColumn:
    """Table column definition"""
    
    header: str
    key: str
    width: int | None = None
    align: str = "left"  # left, right, center


def format_table(
    data: List[dict[str, Any]],
    columns: List[TableColumn],
    show_header: bool = True,
) -> str:
    """
    Format data as table
    
    Args:
        data: List of row dictionaries
        columns: Column definitions
        show_header: Show header row
        
    Returns:
        Formatted table string
    """
    if not data:
        return ""
    
    # Calculate column widths
    widths = {}
    for col in columns:
        if col.width:
            widths[col.key] = col.width
        else:
            # Auto-calculate width
            max_width = len(col.header)
            for row in data:
                value = str(row.get(col.key, ""))
                max_width = max(max_width, len(value))
            widths[col.key] = max_width
    
    lines = []
    
    # Header
    if show_header:
        header_parts = []
        for col in columns:
            width = widths[col.key]
            header = col.header.ljust(width)
            header_parts.append(header)
        
        lines.append(" | ".join(header_parts))
        
        # Separator
        separator_parts = []
        for col in columns:
            width = widths[col.key]
            separator_parts.append("-" * width)
        
        lines.append("-+-".join(separator_parts))
    
    # Rows
    for row in data:
        row_parts = []
        for col in columns:
            width = widths[col.key]
            value = str(row.get(col.key, ""))
            
            # Align
            if col.align == "right":
                value = value.rjust(width)
            elif col.align == "center":
                value = value.center(width)
            else:
                value = value.ljust(width)
            
            row_parts.append(value)
        
        lines.append(" | ".join(row_parts))
    
    return "\n".join(lines)
