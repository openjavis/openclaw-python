"""ANSI escape codes for terminal formatting"""
from __future__ import annotations

from enum import Enum


class ANSIColors(str, Enum):
    """ANSI color codes"""
    
    # Reset
    RESET = "\033[0m"
    
    # Basic colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright colors
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"
    
    # Background colors
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"


class ANSIStyles(str, Enum):
    """ANSI text styles"""
    
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    REVERSE = "\033[7m"
    HIDDEN = "\033[8m"
    STRIKETHROUGH = "\033[9m"


def format_color(text: str, color: ANSIColors | str) -> str:
    """
    Format text with color
    
    Args:
        text: Text to format
        color: ANSI color code
        
    Returns:
        Formatted text
    """
    if isinstance(color, ANSIColors):
        color = color.value
    
    return f"{color}{text}{ANSIColors.RESET.value}"


def format_bold(text: str) -> str:
    """Format text as bold"""
    return f"{ANSIStyles.BOLD.value}{text}{ANSIColors.RESET.value}"


def format_dim(text: str) -> str:
    """Format text as dim"""
    return f"{ANSIStyles.DIM.value}{text}{ANSIColors.RESET.value}"


def format_italic(text: str) -> str:
    """Format text as italic"""
    return f"{ANSIStyles.ITALIC.value}{text}{ANSIColors.RESET.value}"


def format_underline(text: str) -> str:
    """Format text with underline"""
    return f"{ANSIStyles.UNDERLINE.value}{text}{ANSIColors.RESET.value}"


def strip_ansi(text: str) -> str:
    """Remove ANSI codes from text"""
    import re
    
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


def rgb_color(r: int, g: int, b: int, background: bool = False) -> str:
    """
    Create RGB color code
    
    Args:
        r: Red (0-255)
        g: Green (0-255)
        b: Blue (0-255)
        background: Background color if True
        
    Returns:
        ANSI RGB color code
    """
    if background:
        return f"\033[48;2;{r};{g};{b}m"
    else:
        return f"\033[38;2;{r};{g};{b}m"
