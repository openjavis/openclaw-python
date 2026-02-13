"""
Smart image loading for agent context
Based on openclaw TypeScript: src/agents/pi-embedded-runner/run/images.ts

Implements intelligent image loading that:
- Only loads images explicitly referenced in prompts
- Deduplicates images across current prompt and history
- Skips images already loaded in previous messages
- Only scans user messages (not assistant messages)
"""
from __future__ import annotations


import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Common image file extensions
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".heic", ".heif", ".tiff", ".tif"}


@dataclass
class DetectedImageRef:
    """Detected image reference in text"""

    raw: str  # Original matched string
    type: str  # "path" or "url"
    resolved: str  # Resolved path or URL
    message_index: int | None = None  # For history images


def is_image_extension(path: str) -> bool:
    """Check if file extension indicates an image file"""
    ext = Path(path).suffix.lower()
    return ext in IMAGE_EXTENSIONS


def detect_image_references(text: str) -> list[DetectedImageRef]:
    """
    Detect image references in text
    
    Patterns detected:
    - ![alt text](path/to/image.png) - Markdown syntax
    - [media attached: path.jpg (type) | url]
    - [Image: source: /path/to/image.jpg]
    - /absolute/path/to/image.png
    - ~/Pictures/screenshot.png
    - ./relative/image.jpg
    
    Args:
        text: Text to scan for image references
    
    Returns:
        List of detected image references
    """
    refs: list[DetectedImageRef] = []
    seen = set()

    def add_path_ref(raw: str):
        """Helper to add a path reference"""
        trimmed = raw.strip()
        if not trimmed or trimmed.lower() in seen:
            return
        if not is_image_extension(trimmed):
            return

        seen.add(trimmed.lower())
        resolved = str(Path(trimmed).expanduser()) if trimmed.startswith("~") else trimmed
        refs.append(DetectedImageRef(raw=trimmed, type="path", resolved=resolved))

    # Pattern 0: Markdown image syntax: ![alt](path)
    markdown_pattern = r"!\[([^\]]*)\]\(([^)]+)\)"
    for match in re.finditer(markdown_pattern, text):
        path = match.group(2).strip()
        if path:
            add_path_ref(path)

    # Pattern 1: [media attached: path (type) | url] or [media attached N/M: path (type) | url]
    # Each bracket = ONE file. The | separates path from URL, not multiple files.
    media_pattern = r"\[media attached(?:\s+\d+/\d+)?:\s*([^\]]+)\]"
    for match in re.finditer(media_pattern, text, re.IGNORECASE):
        content = match.group(1)

        # Skip "[media attached: N files]" header lines
        if re.match(r"^\d+\s+files?$", content.strip(), re.IGNORECASE):
            continue

        # Extract path before the (mime/type) or | delimiter
        # Format is: path (type) | url  OR  just: path (type)
        # Path may contain spaces (e.g., "ChatGPT Image Apr 21.png")
        path_match = re.match(
            r"^\s*(.+?\.(?:png|jpe?g|gif|webp|bmp|tiff?|heic|heif))\s*(?:\(|$|\|)",
            content,
            re.IGNORECASE,
        )
        if path_match and path_match.group(1):
            add_path_ref(path_match.group(1).strip())

    # Pattern 2: [Image: source: /path/...] format from messaging systems
    image_source_pattern = (
        r"\[Image:\s*source:\s*([^\]]+\.(?:png|jpe?g|gif|webp|bmp|tiff?|heic|heif))\]"
    )
    for match in re.finditer(image_source_pattern, text, re.IGNORECASE):
        raw = match.group(1).strip() if match.group(1) else None
        if raw:
            add_path_ref(raw)

    # Pattern 3: File paths (absolute, relative, or home)
    # Matches:
    # - /absolute/path/to/file.ext
    # - ./relative/path.ext
    # - ../parent/path.ext
    # - ~/home/path.ext
    path_pattern = (
        r"(?:^|\s|[\"'`(])((\.\.?/|[~/])[^\s\"'`()\[\]]*\.(?:png|jpe?g|gif|webp|bmp|tiff?|heic|heif))"
    )
    for match in re.finditer(path_pattern, text, re.IGNORECASE):
        if match.group(1):
            add_path_ref(match.group(1))

    return refs


def message_has_image_content(msg: dict) -> bool:
    """
    Check if message already has image content
    
    Args:
        msg: Message dictionary with optional 'images' field
    
    Returns:
        True if message has images, False otherwise
    """
    images = msg.get("images")
    return bool(images and len(images) > 0)


def detect_images_from_history(messages: list[dict]) -> list[DetectedImageRef]:
    """
    Extract image references from conversation history
    
    Only scans user messages for image paths/URLs.
    Skips messages that already have image content (prevents reloading).
    
    Returns refs with message_index for targeted injection.
    
    Note: Global deduplication is intentional - if the same image appears in multiple
    messages, we only inject it at the FIRST occurrence. This is sufficient because:
    1. The model sees all message content including the image
    2. Later references to "the image" or "that picture" will work since it's in context
    3. Injecting duplicates would waste tokens and potentially hit size limits
    
    Args:
        messages: List of message dictionaries with 'role', 'content', 'images' fields
    
    Returns:
        List of detected image references with message indices
    """
    all_refs: list[DetectedImageRef] = []
    seen = set()

    for i, msg in enumerate(messages):
        # Only scan user messages
        if msg.get("role") != "user":
            continue

        # Skip if message already has image content (prevents reloading each turn)
        if message_has_image_content(msg):
            logger.debug(f"Skipping message {i}: already has image content")
            continue

        text = msg.get("content", "")
        if not text:
            continue

        refs = detect_image_references(text)
        for ref in refs:
            key = ref.resolved.lower()
            if key not in seen:
                seen.add(key)
                ref.message_index = i
                all_refs.append(ref)
                logger.debug(f"Detected image in history[{i}]: {ref.resolved}")

    return all_refs


def is_path_in_sandbox(path: Path, sandbox_root: Path | None) -> bool:
    """
    Check if path is within sandbox directory.
    
    Args:
        path: Path to check
        sandbox_root: Sandbox root directory (None = no restriction)
        
    Returns:
        True if path is allowed, False if outside sandbox
    """
    if not sandbox_root:
        return True
    
    try:
        # Resolve to absolute paths
        abs_path = path.resolve()
        abs_sandbox = sandbox_root.resolve()
        
        # Check if path is relative to sandbox
        return abs_path.is_relative_to(abs_sandbox)
    except (ValueError, OSError):
        return False


def load_image_data(path: Path, max_size_bytes: int | None = None) -> dict | None:
    """
    Load image file and convert to content format.
    
    Args:
        path: Path to image file
        max_size_bytes: Maximum file size (None = no limit)
        
    Returns:
        Image content dict with 'type', 'source', etc., or None if failed
    """
    try:
        if not path.exists() or not path.is_file():
            logger.warning(f"Image file not found: {path}")
            return None
        
        # Check file size
        file_size = path.stat().st_size
        if max_size_bytes and file_size > max_size_bytes:
            logger.warning(f"Image too large ({file_size} bytes): {path}")
            return None
        
        # Read image data
        with open(path, "rb") as f:
            data = f.read()
        
        # Convert to base64
        import base64
        encoded = base64.b64encode(data).decode("utf-8")
        
        # Determine media type
        suffix = path.suffix.lower()
        media_type_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        media_type = media_type_map.get(suffix, "image/jpeg")
        
        return {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": encoded,
            }
        }
    except Exception as e:
        logger.error(f"Failed to load image {path}: {e}")
        return None


def smart_load_images(
    current_prompt: str,
    history_messages: list[dict] | None = None,
    existing_images: list[str] | None = None,
    workspace_dir: Path | None = None,
    sandbox_root: Path | None = None,
    max_image_size: int | None = None,
) -> dict:
    """
    Smart image loading for agent context
    
    Implements intelligent image loading that:
    - Only loads images explicitly referenced in prompts
    - Deduplicates images across current prompt and history
    - Skips images already loaded in previous messages
    - Only scans user messages (not assistant messages)
    - Respects sandbox path restrictions
    - Converts images to base64 format
    
    Args:
        current_prompt: Current user prompt text
        history_messages: Previous conversation messages
        existing_images: Images already attached to current message
        workspace_dir: Workspace directory for resolving relative paths
        sandbox_root: Sandbox root (images must be within this directory)
        max_image_size: Maximum image size in bytes
    
    Returns:
        Dictionary with:
        - current_images: Images for current prompt (existing + detected)
        - history_images_by_index: Images from history, keyed by message index
        - loaded_count: Number of new images loaded
        - skipped_count: Number of images skipped (duplicates or not found)
        - prompt_refs: Image references detected in current prompt
        - history_refs: Image references detected in history
    
    Example:
        >>> result = smart_load_images(
        ...     current_prompt="Show me the chart at ~/data/chart.png",
        ...     history_messages=[
        ...         {"role": "user", "content": "Look at ~/old_chart.png"},
        ...         {"role": "assistant", "content": "I see the chart"}
        ...     ],
        ...     workspace_dir=Path.cwd()
        ... )
        >>> result["loaded_count"]
        2  # One from current, one from history
    """
    # Detect images from current prompt
    prompt_refs = detect_image_references(current_prompt)
    logger.debug(f"Detected {len(prompt_refs)} image refs in current prompt")

    # Detect images from history (with message indices)
    history_refs = detect_images_from_history(history_messages or [])
    logger.debug(f"Detected {len(history_refs)} image refs in history")

    # Deduplicate: if image is in current prompt, don't also load from history
    seen_paths = {r.resolved.lower() for r in prompt_refs}
    unique_history_refs = [r for r in history_refs if r.resolved.lower() not in seen_paths]

    if prompt_refs or unique_history_refs:
        logger.info(
            f"Image detection: {len(prompt_refs)} in prompt, "
            f"{len(unique_history_refs)} unique in history"
        )

    # Start with existing images
    current_images = list(existing_images or [])

    # Load images for current prompt
    loaded_count = 0
    skipped_count = 0

    for ref in prompt_refs:
        path = Path(ref.resolved)
        
        # Resolve relative paths from workspace
        if not path.is_absolute() and workspace_dir:
            path = workspace_dir / path
        
        # Check sandbox restrictions
        if not is_path_in_sandbox(path, sandbox_root):
            logger.warning(f"Image outside sandbox, skipped: {path}")
            skipped_count += 1
            continue
        
        if path.exists() and path.is_file():
            # Load image data
            image_content = load_image_data(path, max_image_size)
            if image_content:
                current_images.append(image_content)
                loaded_count += 1
                logger.debug(f"Loaded current prompt image: {path}")
            else:
                skipped_count += 1
        else:
            skipped_count += 1
            logger.debug(f"Image file not found: {path}")

    # Load history images, organized by message index
    history_images_by_index = {}
    for ref in unique_history_refs:
        path = Path(ref.resolved)
        
        # Resolve relative paths from workspace
        if not path.is_absolute() and workspace_dir:
            path = workspace_dir / path
        
        # Check sandbox restrictions
        if not is_path_in_sandbox(path, sandbox_root):
            logger.warning(f"History image outside sandbox, skipped: {path}")
            skipped_count += 1
            continue
        
        if path.exists() and path.is_file():
            idx = ref.message_index
            if idx is not None:
                # Load image data
                image_content = load_image_data(path, max_image_size)
                if image_content:
                    if idx not in history_images_by_index:
                        history_images_by_index[idx] = []
                    history_images_by_index[idx].append(image_content)
                    loaded_count += 1
                    logger.debug(f"Loaded history image for message[{idx}]: {path}")
                else:
                    skipped_count += 1
        else:
            skipped_count += 1

    return {
        "current_images": current_images,
        "history_images_by_index": history_images_by_index,
        "loaded_count": loaded_count,
        "skipped_count": skipped_count,
        "prompt_refs": prompt_refs,
        "history_refs": unique_history_refs,
    }
