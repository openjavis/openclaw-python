"""
File management utilities for generated files (PPT, PDFs, images, etc.)

This module provides utilities for organizing and naming generated files
in a consistent way across all channels and skills.
"""

import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def get_presentations_dir(workspace_dir: Path) -> Path:
    """
    Get or create presentations directory in workspace
    
    Args:
        workspace_dir: Base workspace directory (typically session workspace)
    
    Returns:
        Path to presentations directory
        
    Example:
        >>> workspace = Path("/workspace/session-123")
        >>> ppt_dir = get_presentations_dir(workspace)
        >>> # Returns: /workspace/session-123/presentations
    """
    presentations_dir = workspace_dir / "presentations"
    presentations_dir.mkdir(parents=True, exist_ok=True)
    return presentations_dir


def get_documents_dir(workspace_dir: Path) -> Path:
    """Get or create documents directory"""
    docs_dir = workspace_dir / "documents"
    docs_dir.mkdir(parents=True, exist_ok=True)
    return docs_dir


def get_images_dir(workspace_dir: Path) -> Path:
    """Get or create images directory"""
    images_dir = workspace_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    return images_dir


def sanitize_filename(text: str, max_length: int = 50) -> str:
    """
    Sanitize text for use in filename
    
    Args:
        text: Raw text to sanitize
        max_length: Maximum length of sanitized text
        
    Returns:
        Safe filename component (no extension)
        
    Example:
        >>> sanitize_filename("AI & ML: Overview (2026)")
        'AI_ML_Overview_2026'
        >>> sanitize_filename("Hello World!")
        'Hello_World'
    """
    # Remove special characters (keep alphanumeric, spaces, hyphens, underscores)
    safe = re.sub(r'[^\w\s-]', '', text)
    
    # Replace whitespace with underscores
    safe = re.sub(r'[\s]+', '_', safe)
    
    # Remove leading/trailing underscores
    safe = safe.strip('_')
    
    # Limit length
    if len(safe) > max_length:
        safe = safe[:max_length]
    
    # Ensure not empty
    if not safe:
        safe = "untitled"
    
    return safe


def generate_presentation_filename(
    title: str | None = None,
    timestamp: datetime | None = None
) -> str:
    """
    Generate a unique presentation filename
    
    Args:
        title: Presentation title (will be sanitized)
        timestamp: Timestamp for uniqueness (defaults to now)
        
    Returns:
        Filename with .pptx extension
        
    Example:
        >>> generate_presentation_filename("AI Introduction")
        'AI_Introduction_20260208_143022.pptx'
        >>> generate_presentation_filename()
        'presentation_20260208_143022.pptx'
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    time_str = timestamp.strftime("%Y%m%d_%H%M%S")
    
    if title:
        safe_title = sanitize_filename(title)
        return f"{safe_title}_{time_str}.pptx"
    else:
        return f"presentation_{time_str}.pptx"


def generate_document_filename(
    title: str | None = None,
    extension: str = "pdf",
    timestamp: datetime | None = None
) -> str:
    """
    Generate a unique document filename
    
    Args:
        title: Document title
        extension: File extension (without dot)
        timestamp: Timestamp for uniqueness
        
    Returns:
        Filename with specified extension
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    time_str = timestamp.strftime("%Y%m%d_%H%M%S")
    
    # Ensure extension doesn't have leading dot
    ext = extension.lstrip('.')
    
    if title:
        safe_title = sanitize_filename(title)
        return f"{safe_title}_{time_str}.{ext}"
    else:
        return f"document_{time_str}.{ext}"


def generate_image_filename(
    description: str | None = None,
    extension: str = "png",
    timestamp: datetime | None = None
) -> str:
    """
    Generate a unique image filename
    
    Args:
        description: Image description
        extension: File extension (without dot)
        timestamp: Timestamp for uniqueness
        
    Returns:
        Filename with specified extension
    """
    if timestamp is None:
        timestamp = datetime.now()
    
    time_str = timestamp.strftime("%Y%m%d_%H%M%S")
    ext = extension.lstrip('.')
    
    if description:
        safe_desc = sanitize_filename(description)
        return f"{safe_desc}_{time_str}.{ext}"
    else:
        return f"image_{time_str}.{ext}"


def get_file_type_from_extension(file_path: str | Path) -> str:
    """
    Determine file type for channel sending
    
    Args:
        file_path: Path to file
        
    Returns:
        File type: "photo", "video", "audio", or "document"
        
    Example:
        >>> get_file_type_from_extension("test.pptx")
        'document'
        >>> get_file_type_from_extension("image.jpg")
        'photo'
    """
    ext = Path(file_path).suffix.lower()
    
    photo_exts = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'}
    video_exts = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv'}
    audio_exts = {'.mp3', '.wav', '.ogg', '.m4a', '.flac', '.aac'}
    
    if ext in photo_exts:
        return "photo"
    elif ext in video_exts:
        return "video"
    elif ext in audio_exts:
        return "audio"
    else:
        return "document"


def create_file_metadata(
    file_path: Path,
    title: str | None = None,
    description: str | None = None
) -> dict[str, Any]:
    """
    Create metadata dictionary for a generated file
    
    Args:
        file_path: Path to the generated file
        title: File title
        description: File description
        
    Returns:
        Metadata dictionary ready for event data
        
    Example:
        >>> metadata = create_file_metadata(
        ...     Path("/workspace/presentations/AI_20260208.pptx"),
        ...     title="AI Introduction"
        ... )
        >>> metadata['file_type']
        'document'
    """
    file_type = get_file_type_from_extension(file_path)
    
    # Generate caption
    caption = title or file_path.stem
    if description:
        caption = f"{caption}: {description}"
    
    return {
        "file_path": str(file_path.absolute()),
        "file_name": file_path.name,
        "file_type": file_type,
        "file_size": file_path.stat().st_size if file_path.exists() else 0,
        "caption": caption,
        "created_at": datetime.now().isoformat(),
    }


# Convenience function for agent tools
def prepare_file_for_sending(
    workspace_dir: Path,
    file_category: str,  # "presentations", "documents", "images"
    title: str | None = None,
    extension: str = "pptx",
) -> tuple[Path, str]:
    """
    Prepare a path and filename for a generated file
    
    Args:
        workspace_dir: Base workspace directory
        file_category: Category of file (presentations, documents, images)
        title: Title for filename generation
        extension: File extension
        
    Returns:
        Tuple of (output_path, filename)
        
    Example:
        >>> path, name = prepare_file_for_sending(
        ...     Path("/workspace"),
        ...     "presentations",
        ...     "AI Intro"
        ... )
        >>> str(path)
        '/workspace/presentations/AI_Intro_20260208_143022.pptx'
    """
    # Get appropriate directory
    if file_category == "presentations":
        output_dir = get_presentations_dir(workspace_dir)
        filename = generate_presentation_filename(title)
    elif file_category == "documents":
        output_dir = get_documents_dir(workspace_dir)
        filename = generate_document_filename(title, extension)
    elif file_category == "images":
        output_dir = get_images_dir(workspace_dir)
        filename = generate_image_filename(title, extension)
    else:
        output_dir = workspace_dir / file_category
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = sanitize_filename(title) if title else "file"
        filename = f"{safe_title}_{timestamp}.{extension.lstrip('.')}"
    
    output_path = output_dir / filename
    
    return output_path, filename
