"""
Tests for MIME detection

Matches TypeScript src/media/mime.ts
"""
from __future__ import annotations

import pytest

from openclaw.media.mime import (
    EXT_BY_MIME,
    MediaKind,
    detect_mime,
    extension_for_mime,
    is_heic_file,
    is_heic_mime,
    media_kind_from_mime,
    mime_for_extension,
    normalize_header_mime,
)


class TestNormalizeHeaderMime:
    """Tests for normalize_header_mime."""
    
    def test_clean_mime(self):
        assert normalize_header_mime("image/jpeg") == "image/jpeg"
    
    def test_remove_charset(self):
        assert normalize_header_mime("image/jpeg; charset=utf-8") == "image/jpeg"
    
    def test_none(self):
        assert normalize_header_mime(None) is None
    
    def test_empty(self):
        assert normalize_header_mime("") is None


class TestExtensionForMime:
    """Tests for extension_for_mime."""
    
    def test_common_types(self):
        assert extension_for_mime("image/jpeg") == ".jpg"
        assert extension_for_mime("image/png") == ".png"
        assert extension_for_mime("image/heic") == ".heic"
        assert extension_for_mime("audio/mpeg") == ".mp3"
    
    def test_case_insensitive(self):
        assert extension_for_mime("IMAGE/JPEG") == ".jpg"
    
    def test_unknown(self):
        assert extension_for_mime("unknown/type") is None


class TestMimeForExtension:
    """Tests for mime_for_extension."""
    
    def test_with_dot(self):
        assert mime_for_extension(".jpg") == "image/jpeg"
        assert mime_for_extension(".png") == "image/png"
    
    def test_without_dot(self):
        assert mime_for_extension("jpg") == "image/jpeg"
        assert mime_for_extension("png") == "image/png"
    
    def test_jpeg_alias(self):
        assert mime_for_extension(".jpeg") == "image/jpeg"


class TestMediaKindFromMime:
    """Tests for media_kind_from_mime."""
    
    def test_images(self):
        assert media_kind_from_mime("image/jpeg") == MediaKind.IMAGE
        assert media_kind_from_mime("image/png") == MediaKind.IMAGE
        assert media_kind_from_mime("image/heic") == MediaKind.IMAGE
    
    def test_audio(self):
        assert media_kind_from_mime("audio/mpeg") == MediaKind.AUDIO
        assert media_kind_from_mime("audio/ogg") == MediaKind.AUDIO
    
    def test_video(self):
        assert media_kind_from_mime("video/mp4") == MediaKind.VIDEO
        assert media_kind_from_mime("video/quicktime") == MediaKind.VIDEO
    
    def test_documents(self):
        assert media_kind_from_mime("application/pdf") == MediaKind.DOCUMENT
        assert media_kind_from_mime("text/plain") == MediaKind.DOCUMENT
    
    def test_unknown(self):
        assert media_kind_from_mime("unknown/type") == MediaKind.UNKNOWN
        assert media_kind_from_mime(None) == MediaKind.UNKNOWN


class TestHeicDetection:
    """Tests for HEIC detection."""
    
    def test_is_heic_mime(self):
        assert is_heic_mime("image/heic")
        assert is_heic_mime("image/heif")
        assert not is_heic_mime("image/jpeg")
    
    def test_is_heic_file(self):
        from pathlib import Path
        
        assert is_heic_file(Path("photo.heic"))
        assert is_heic_file(Path("photo.HEIC"))
        assert is_heic_file(Path("photo.heif"))
        assert not is_heic_file(Path("photo.jpg"))
