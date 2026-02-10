"""Command detection from message text"""
from __future__ import annotations

import re
import logging
from typing import Optional

from .types import CommandInvocation

logger = logging.getLogger(__name__)


# Command pattern: /command [args...]
COMMAND_PATTERN = re.compile(r'^/([a-zA-Z0-9_-]+)(?:\s+(.*))?$')

# Skill command pattern: /skill:name [args...]
SKILL_COMMAND_PATTERN = re.compile(r'^/skill:([a-zA-Z0-9_-]+)(?:\s+(.*))?$')


def detect_command(text: str) -> Optional[CommandInvocation]:
    """
    Detect command from message text
    
    Supports:
    - Built-in commands: /command [args...]
    - Skill commands: /skill:name [args...]
    
    Args:
        text: Message text
        
    Returns:
        CommandInvocation if command detected, None otherwise
    """
    if not text or not text.strip():
        return None
    
    text = text.strip()
    
    # Check for skill command first
    skill_match = SKILL_COMMAND_PATTERN.match(text)
    if skill_match:
        skill_name = skill_match.group(1)
        args_str = skill_match.group(2) or ""
        
        # Parse args
        args, kwargs = _parse_args(args_str)
        
        return CommandInvocation(
            command_name=f"skill:{skill_name}",
            args=args,
            kwargs=kwargs,
            raw_text=text,
        )
    
    # Check for regular command
    cmd_match = COMMAND_PATTERN.match(text)
    if cmd_match:
        command_name = cmd_match.group(1)
        args_str = cmd_match.group(2) or ""
        
        # Parse args
        args, kwargs = _parse_args(args_str)
        
        return CommandInvocation(
            command_name=command_name,
            args=args,
            kwargs=kwargs,
            raw_text=text,
        )
    
    return None


def _parse_args(args_str: str) -> tuple[list[str], dict[str, str]]:
    """
    Parse command arguments
    
    Supports:
    - Positional args: arg1 arg2 arg3
    - Named args: key=value key2="value with spaces"
    
    Args:
        args_str: Arguments string
        
    Returns:
        (args, kwargs) tuple
    """
    if not args_str:
        return [], {}
    
    # Split by whitespace (respecting quotes)
    parts = _split_respecting_quotes(args_str)
    
    args = []
    kwargs = {}
    
    for part in parts:
        # Check if it's a key=value pair
        if "=" in part:
            key, value = part.split("=", 1)
            # Remove quotes from value
            value = value.strip('"').strip("'")
            kwargs[key] = value
        else:
            # Positional arg
            # Remove quotes
            part = part.strip('"').strip("'")
            args.append(part)
    
    return args, kwargs


def _split_respecting_quotes(text: str) -> list[str]:
    """
    Split text by whitespace, respecting quoted strings
    
    Args:
        text: Text to split
        
    Returns:
        List of parts
    """
    parts = []
    current = []
    in_quotes = False
    quote_char = None
    
    for char in text:
        if char in ('"', "'"):
            if not in_quotes:
                # Start quote
                in_quotes = True
                quote_char = char
                current.append(char)
            elif char == quote_char:
                # End quote
                in_quotes = False
                quote_char = None
                current.append(char)
            else:
                # Different quote inside
                current.append(char)
        elif char.isspace():
            if in_quotes:
                # Space inside quotes
                current.append(char)
            else:
                # Space outside quotes - split
                if current:
                    parts.append("".join(current))
                    current = []
        else:
            current.append(char)
    
    # Add last part
    if current:
        parts.append("".join(current))
    
    return parts


def is_command(text: str) -> bool:
    """
    Check if text is a command
    
    Args:
        text: Text to check
        
    Returns:
        True if text starts with /
    """
    if not text:
        return False
    
    return text.strip().startswith("/")
