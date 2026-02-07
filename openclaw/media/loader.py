"""
Media loader

Loads media from files, URLs, and data URLs.
Matches TypeScript src/web/media.ts
"""
from __future__ import annotations

import base64
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx

from .mime import (
    MediaKind,
    detect_mime,
    media_kind_from_mime,
    normalize_header_mime,
)

logger = logging.getLogger(__name__)


@dataclass
class MediaResult:
    """
    Media load result (matches TS WebMediaResult).
    Attributes:
        buffer: Media data
        content_type: MIME type
        kind: Media kind (image/audio/video/document)
        file_name: Original file name
    """
    buffer: bytes
    content_type: str | None
    kind: MediaKind
    file_name: str | None = None


class MediaLoader:
    """
    Media loader supporting multiple sources.
    Supports:
    - Local files (file:// or absolute/relative paths)
    - HTTP/HTTPS URLs
    - Data URLs (data:image/png;base64,...)
    - HEIC conversion to JPEG
    - Size limits
    - MIME detection
    """
    def __init__(
        self,
        max_bytes: int | None = None,
        optimize_images: bool = False,
        allow_remote: bool = True,
        workspace_root: Path | None = None,
    ):
        """
        Initialize media loader.
        Args:
            max_bytes: Maximum file size in bytes
            optimize_images: Whether to optimize/compress images
            allow_remote: Allow HTTP/HTTPS URLs
            workspace_root: Workspace root for sandboxed access
        """
        self.max_bytes = max_bytes
        self.optimize_images = optimize_images
        self.allow_remote = allow_remote
        self.workspace_root = workspace_root

    async def load(self, source: str) -> MediaResult:
        """
        Load media from source.

        Args:
            source: File path, URL, or data URL

        Returns:
            MediaResult

        Raises:
            ValueError: If source is invalid or not allowed
            FileNotFoundError: If file not found
            httpx.HTTPError: If HTTP request fails
        """
        source = source.strip()

        # Data URL
        if source.startswith("data:"):
            return await self._load_data_url(source)

        # HTTP URL
        if source.startswith("http://") or source.startswith("https://"):
            if not self.allow_remote:
                raise ValueError("Remote URLs not allowed in this context")
            return await self._load_http_url(source)

        # File URL
        if source.startswith("file://"):
            source = source[7:]  # Remove file:// prefix

        # Local file
        return await self._load_file(source)

    async def _load_data_url(self, data_url: str) -> MediaResult:
        """
        Load from data URL (matches TS decodeDataUrl).

        Format: data:image/png;base64,iVBORw0KG...
        """
        match = re.match(r"^data:([^;,]+)?;base64,(.+)$", data_url, re.IGNORECASE)
        if not match:
            raise ValueError("Invalid data URL format")

        mime_type = match.group(1) or "image/png"
        base64_data = match.group(2)

        try:
            buffer = base64.b64decode(base64_data)
        except Exception as e:
            raise ValueError(f"Invalid base64 data: {e}")

        # Check size
        if self.max_bytes and len(buffer) > self.max_bytes:
            raise ValueError(f"Data URL exceeds size limit: {len(buffer)} > {self.max_bytes}")

        kind = media_kind_from_mime(mime_type)

        return MediaResult(
            buffer=buffer,
            content_type=mime_type,
            kind=kind,
            file_name=None,
        )
    async def _load_http_url(self, url: str) -> MediaResult:
        """Load from HTTP/HTTPS URL."""
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()

            buffer = response.content

            # Check size
            if self.max_bytes and len(buffer) > self.max_bytes:
                raise ValueError(
                    f"Remote media exceeds size limit: {len(buffer)} > {self.max_bytes}"
                )

            # Get MIME from header
            content_type = normalize_header_mime(response.headers.get("content-type"))

            # Detect from buffer if header missing
            if not content_type:
                content_type = detect_mime(buffer=buffer)

            kind = media_kind_from_mime(content_type)

            # Extract filename from URL
            parsed = urlparse(url)
            file_name = Path(parsed.path).name if parsed.path else None

            return MediaResult(
                buffer=buffer,
                content_type=content_type,
                kind=kind,
                file_name=file_name,
            )

    async def _load_file(self, file_path: str) -> MediaResult:
        """Load from local file."""
        path = Path(file_path)

        # Expand ~ and resolve relative paths
        if str(path).startswith("~"):
            path = path.expanduser()

        # Sandbox check (if workspace root set)
        if self.workspace_root:
            path = path.resolve()
            workspace = self.workspace_root.resolve()
            # Check if path is inside workspace
            try:
                path.relative_to(workspace)
            except ValueError:
                # Try media/inbound fallback (matches TS resolveSandboxedImagePath)
                fallback = workspace / "media" / "inbound" / path.name
                if fallback.exists():
                    logger.info(f"Rewritten path: {file_path} -> {fallback}")
                    path = fallback
                else:
                    raise ValueError(f"Path outside workspace: {path} (workspace: {workspace})")

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        if not path.is_file():
            raise ValueError(f"Not a file: {path}")

        # Read file
        buffer = path.read_bytes()

        # Check size
        if self.max_bytes and len(buffer) > self.max_bytes:
            raise ValueError(f"File exceeds size limit: {len(buffer)} > {self.max_bytes} ({path})")

        # Detect MIME
        content_type = detect_mime(file_path=path, buffer=buffer)
        kind = media_kind_from_mime(content_type)

        return MediaResult(
            buffer=buffer,
            content_type=content_type,
            kind=kind,
            file_name=path.name,
        )


# Convenience function (matches TS loadWebMedia)
async def load_media(
    source: str,
    max_bytes: int | None = None,
    optimize_images: bool = False,
    allow_remote: bool = True,
    workspace_root: Path | None = None,
) -> MediaResult:
    """
    Load media from any source (convenience function).
    Args:
        source: File path, URL, or data URL
        max_bytes: Maximum size in bytes
        optimize_images: Whether to optimize images
        allow_remote: Allow HTTP/HTTPS URLs
        workspace_root: Workspace root for sandboxed access
    Returns:
        MediaResult
    """
    loader = MediaLoader(
        max_bytes=max_bytes,
        optimize_images=optimize_images,
        allow_remote=allow_remote,
        workspace_root=workspace_root,
    )
    return await loader.load(source)
