"""
Tests for file_manager utilities
"""

import pytest
from datetime import datetime
from pathlib import Path
import tempfile
import shutil

from openclaw.agents.tools.file_manager import (
    get_presentations_dir,
    get_documents_dir,
    get_images_dir,
    sanitize_filename,
    generate_presentation_filename,
    generate_document_filename,
    generate_image_filename,
    get_file_type_from_extension,
    create_file_metadata,
    prepare_file_for_sending,
)


@pytest.fixture
def temp_workspace():
    """Create temporary workspace directory"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


def test_get_presentations_dir(temp_workspace):
    """Test presentations directory creation"""
    ppt_dir = get_presentations_dir(temp_workspace)
    assert ppt_dir.exists()
    assert ppt_dir.is_dir()
    assert ppt_dir == temp_workspace / "presentations"


def test_get_documents_dir(temp_workspace):
    """Test documents directory creation"""
    docs_dir = get_documents_dir(temp_workspace)
    assert docs_dir.exists()
    assert docs_dir == temp_workspace / "documents"


def test_get_images_dir(temp_workspace):
    """Test images directory creation"""
    img_dir = get_images_dir(temp_workspace)
    assert img_dir.exists()
    assert img_dir == temp_workspace / "images"


def test_sanitize_filename():
    """Test filename sanitization"""
    # Basic sanitization
    assert sanitize_filename("Hello World") == "Hello_World"
    assert sanitize_filename("AI & ML: Overview") == "AI_ML_Overview"
    assert sanitize_filename("Test (2026)") == "Test_2026"
    
    # Special characters
    assert sanitize_filename("file@#$%name") == "filename"
    assert sanitize_filename("hello!world?") == "helloworld"
    
    # Whitespace handling
    assert sanitize_filename("  multiple   spaces  ") == "multiple_spaces"
    
    # Empty or invalid
    assert sanitize_filename("") == "untitled"
    assert sanitize_filename("@#$%") == "untitled"
    
    # Length limit
    long_name = "a" * 100
    result = sanitize_filename(long_name)
    assert len(result) <= 50


def test_generate_presentation_filename():
    """Test presentation filename generation"""
    timestamp = datetime(2026, 2, 8, 14, 30, 22)
    
    # With title
    filename = generate_presentation_filename("AI Introduction", timestamp)
    assert filename == "AI_Introduction_20260208_143022.pptx"
    
    # Without title
    filename = generate_presentation_filename(timestamp=timestamp)
    assert filename == "presentation_20260208_143022.pptx"
    
    # Special characters in title
    filename = generate_presentation_filename("AI & ML: Overview (2026)", timestamp)
    assert "AI_ML_Overview_2026" in filename
    assert filename.endswith(".pptx")
    
    # Auto timestamp (just check format)
    filename = generate_presentation_filename("Test")
    assert filename.startswith("Test_")
    assert filename.endswith(".pptx")
    assert len(filename.split("_")) >= 3  # title_YYYYMMDD_HHMMSS.pptx


def test_generate_document_filename():
    """Test document filename generation"""
    timestamp = datetime(2026, 2, 8, 14, 30, 22)
    
    # With title
    filename = generate_document_filename("Report", "pdf", timestamp)
    assert filename == "Report_20260208_143022.pdf"
    
    # Without title
    filename = generate_document_filename(extension="docx", timestamp=timestamp)
    assert filename == "document_20260208_143022.docx"
    
    # Extension with dot
    filename = generate_document_filename("Doc", ".txt", timestamp)
    assert filename.endswith(".txt")
    assert not filename.endswith("..txt")


def test_generate_image_filename():
    """Test image filename generation"""
    timestamp = datetime(2026, 2, 8, 14, 30, 22)
    
    # With description
    filename = generate_image_filename("Logo", "png", timestamp)
    assert filename == "Logo_20260208_143022.png"
    
    # Without description
    filename = generate_image_filename(extension="jpg", timestamp=timestamp)
    assert filename == "image_20260208_143022.jpg"


def test_get_file_type_from_extension():
    """Test file type detection"""
    # Photos
    assert get_file_type_from_extension("image.jpg") == "photo"
    assert get_file_type_from_extension("photo.png") == "photo"
    assert get_file_type_from_extension("pic.gif") == "photo"
    
    # Videos
    assert get_file_type_from_extension("video.mp4") == "video"
    assert get_file_type_from_extension("movie.avi") == "video"
    assert get_file_type_from_extension("clip.mov") == "video"
    
    # Audio
    assert get_file_type_from_extension("song.mp3") == "audio"
    assert get_file_type_from_extension("audio.wav") == "audio"
    
    # Documents (default)
    assert get_file_type_from_extension("doc.pdf") == "document"
    assert get_file_type_from_extension("presentation.pptx") == "document"
    assert get_file_type_from_extension("file.txt") == "document"
    assert get_file_type_from_extension("unknown.xyz") == "document"


def test_create_file_metadata(temp_workspace):
    """Test file metadata creation"""
    # Create a test file
    test_file = temp_workspace / "test.pptx"
    test_file.write_text("test content")
    
    metadata = create_file_metadata(
        test_file,
        title="Test Presentation",
        description="A test file"
    )
    
    assert "file_path" in metadata
    assert "file_name" in metadata
    assert "file_type" in metadata
    assert "file_size" in metadata
    assert "caption" in metadata
    assert "created_at" in metadata
    
    assert metadata["file_name"] == "test.pptx"
    assert metadata["file_type"] == "document"
    assert metadata["file_size"] > 0
    assert "Test Presentation" in metadata["caption"]


def test_prepare_file_for_sending(temp_workspace):
    """Test prepare file for sending"""
    # Presentations
    path, filename = prepare_file_for_sending(
        temp_workspace,
        "presentations",
        "AI Introduction"
    )
    assert path.parent == temp_workspace / "presentations"
    assert filename.startswith("AI_Introduction_")
    assert filename.endswith(".pptx")
    
    # Documents
    path, filename = prepare_file_for_sending(
        temp_workspace,
        "documents",
        "Report",
        "pdf"
    )
    assert path.parent == temp_workspace / "documents"
    assert filename.startswith("Report_")
    assert filename.endswith(".pdf")
    
    # Images
    path, filename = prepare_file_for_sending(
        temp_workspace,
        "images",
        "Logo",
        "png"
    )
    assert path.parent == temp_workspace / "images"
    assert filename.startswith("Logo_")
    assert filename.endswith(".png")
    
    # Custom category
    path, filename = prepare_file_for_sending(
        temp_workspace,
        "custom",
        "File",
        "txt"
    )
    assert path.parent == temp_workspace / "custom"
    assert path.parent.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
