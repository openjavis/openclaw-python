"""
Image operations (optimization, conversion, resize)

Matches TypeScript src/media/image-ops.ts
"""

from __future__ import annotations

import base64
import imghdr
import io
import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ImageMetadata:
    """Image metadata (matches TS ImageMetadata)."""
    width: int
    height: int
    format: str | None = None
    has_alpha: bool = False


@dataclass
class OptimizedImage:
    """Optimized image result."""
    buffer: bytes
    optimized_size: int
    resize_side: int
    format: str  # "jpeg" | "png"
    quality: int | None = None
    compression_level: int | None = None


class ImageProcessor:
    """
    Image processing operations.
    Features:
    - HEIC to JPEG conversion
    - Image resizing
    - Quality optimization
    - Alpha channel detection
    - PNG optimization
    Backends:
    - Pillow (PIL) for most operations
    - sips (macOS) fallback for HEIC
    - ImageMagick fallback
    """
    @staticmethod
    def has_pillow() -> bool:
        """Check if Pillow is available."""
        try:
            import PIL

            return True
        except ImportError:
            return False

    @staticmethod
    def has_sips() -> bool:
        """Check if sips is available (macOS)."""
        try:
            result = subprocess.run(["sips", "--version"], capture_output=True, timeout=5)
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @staticmethod
    async def convert_heic_to_jpeg(buffer: bytes) -> bytes:
        """
        Convert HEIC/HEIF to JPEG (matches TS convertHeicToJpeg).

        Args:
            buffer: HEIC image buffer

        Returns:
            JPEG buffer

        Raises:
            RuntimeError: If conversion fails
        """
        # Try Pillow first (if pillow-heif plugin available)
        if ImageProcessor.has_pillow():
            try:
                from PIL import Image
                from pillow_heif import register_heif_opener

                register_heif_opener()

                img = Image.open(io.BytesIO(buffer))

                # Convert to RGB if needed
                if img.mode != "RGB":
                    img = img.convert("RGB")

                # Save as JPEG
                output = io.BytesIO()
                img.save(output, format="JPEG", quality=90)

                logger.info(
                    f"Converted HEIC to JPEG using Pillow ({len(buffer)} -> {len(output.getvalue())} bytes)"
                )
                return output.getvalue()

            except ImportError:
                logger.debug("pillow-heif not available")
            except Exception as e:
                logger.warning(f"Pillow HEIC conversion failed: {e}")
        # Try sips (macOS)
        if ImageProcessor.has_sips():
            try:
                import tempfile

                with tempfile.NamedTemporaryFile(suffix=".heic", delete=False) as tmp_in:
                    tmp_in.write(buffer)
                    tmp_in_path = Path(tmp_in.name)

                tmp_out_path = tmp_in_path.with_suffix(".jpg")

                result = subprocess.run(
                    ["sips", "-s", "format", "jpeg", str(tmp_in_path), "--out", str(tmp_out_path)],
                    capture_output=True,
                    timeout=30,
                )

                if result.returncode == 0 and tmp_out_path.exists():
                    jpeg_buffer = tmp_out_path.read_bytes()
                    tmp_in_path.unlink(missing_ok=True)
                    tmp_out_path.unlink(missing_ok=True)

                    logger.info(
                        f"Converted HEIC to JPEG using sips ({len(buffer)} -> {len(jpeg_buffer)} bytes)"
                    )
                    return jpeg_buffer

                tmp_in_path.unlink(missing_ok=True)
                tmp_out_path.unlink(missing_ok=True)

            except Exception as e:
                logger.warning(f"sips HEIC conversion failed: {e}")

        raise RuntimeError("HEIC conversion not available. Install pillow-heif or use macOS sips.")

    @staticmethod
    async def get_image_metadata(buffer: bytes) -> ImageMetadata:
        """
        Get image metadata (width, height, format).

        Args:
            buffer: Image buffer

        Returns:
            ImageMetadata
        """
        if not ImageProcessor.has_pillow():
            raise RuntimeError("Pillow required for image metadata")

        from PIL import Image

        img = Image.open(io.BytesIO(buffer))

        return ImageMetadata(
            width=img.width,
            height=img.height,
            format=img.format,
            has_alpha=img.mode in ("RGBA", "LA", "PA"),
        )
    @staticmethod
    async def has_alpha_channel(buffer: bytes) -> bool:
        """
        Check if image has alpha channel (matches TS hasAlphaChannel).

        Args:
            buffer: Image buffer

        Returns:
            True if has alpha
        """
        try:
            metadata = await ImageProcessor.get_image_metadata(buffer)
            return metadata.has_alpha
        except Exception:
            return False
    @staticmethod
    async def resize_to_jpeg(
        buffer: bytes,
        max_side: int = 2048,
        quality: int = 85,
    ) -> bytes:
        """
        Resize image to JPEG (matches TS resizeToJpeg).
        Args:
            buffer: Image buffer
            max_side: Maximum side length
            quality: JPEG quality (1-100)
        Returns:
            Resized JPEG buffer
        """
        if not ImageProcessor.has_pillow():
            raise RuntimeError("Pillow required for image resize")

        from PIL import Image

        img = Image.open(io.BytesIO(buffer))

        # Convert to RGB if needed
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Resize if needed
        if img.width > max_side or img.height > max_side:
            # Calculate new size maintaining aspect ratio
            ratio = min(max_side / img.width, max_side / img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        # Save as JPEG with specified quality
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=quality, optimize=True)

        return output.getvalue()

    @staticmethod
    async def optimize_to_png(
        buffer: bytes,
        max_side: int = 2048,
        compression_level: int = 6,
    ) -> bytes:
        """
        Optimize image to PNG (preserving alpha) (matches TS optimizeImageToPng).
        Args:
            buffer: Image buffer
            max_side: Maximum side length
            compression_level: PNG compression (0-9)
        Returns:
            Optimized PNG buffer
        """
        if not ImageProcessor.has_pillow():
            raise RuntimeError("Pillow required for PNG optimization")

        from PIL import Image

        img = Image.open(io.BytesIO(buffer))

        # Resize if needed
        if img.width > max_side or img.height > max_side:
            ratio = min(max_side / img.width, max_side / img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        # Save as PNG
        output = io.BytesIO()
        img.save(output, format="PNG", compress_level=compression_level, optimize=True)

        return output.getvalue()

    @staticmethod
    async def optimize_image(
        buffer: bytes,
        max_bytes: int,
        preserve_alpha: bool = True,
    ) -> OptimizedImage:
        """
        Optimize image to fit within max_bytes (matches TS optimizeImageWithFallback).
        Strategy:
        1. Check if already under limit
        2. Try resize with progressively smaller dimensions
        3. Try quality reduction for JPEG
        4. For PNG, use compression
        Args:
            buffer: Image buffer
            max_bytes: Maximum size
            preserve_alpha: Preserve alpha channel (use PNG)
        Returns:
            OptimizedImage
        """
        if len(buffer) <= max_bytes:
            # Already under limit
            metadata = await ImageProcessor.get_image_metadata(buffer)
            return OptimizedImage(
                buffer=buffer,
                optimized_size=len(buffer),
                resize_side=max(metadata.width, metadata.height),
                format="png" if metadata.has_alpha else "jpeg",
            )

        # Determine format based on alpha
        has_alpha = await ImageProcessor.has_alpha_channel(buffer)
        use_png = preserve_alpha and has_alpha

        # Try progressively smaller sizes
        for max_side in [2048, 1536, 1024, 768, 512]:
            if use_png:
                optimized = await ImageProcessor.optimize_to_png(
                    buffer, max_side=max_side, compression_level=9
                )
                if len(optimized) <= max_bytes:
                    return OptimizedImage(
                        buffer=optimized,
                        optimized_size=len(optimized),
                        resize_side=max_side,
                        format="png",
                        compression_level=9,
                    )
            else:
                # Try multiple JPEG qualities
                for quality in [85, 75, 65, 55]:
                    optimized = await ImageProcessor.resize_to_jpeg(
                        buffer, max_side=max_side, quality=quality
                    )
                    if len(optimized) <= max_bytes:
                        return OptimizedImage(
                            buffer=optimized,
                            optimized_size=len(optimized),
                            resize_side=max_side,
                            format="jpeg",
                            quality=quality,
                        )

        # Could not optimize below limit
        raise ValueError(f"Could not optimize image below {max_bytes} bytes")


# Convenience functions
async def convert_heic_to_jpeg(buffer: bytes) -> bytes:
    """Convert HEIC to JPEG (convenience function)."""
    return await ImageProcessor.convert_heic_to_jpeg(buffer)


async def has_alpha_channel(buffer: bytes) -> bool:
    """Check if image has alpha (convenience function)."""
    return await ImageProcessor.has_alpha_channel(buffer)


async def resize_to_jpeg(buffer: bytes, max_side: int = 2048, quality: int = 85) -> bytes:
    """Resize to JPEG (convenience function)."""
    return await ImageProcessor.resize_to_jpeg(buffer, max_side, quality)


async def optimize_to_png(buffer: bytes, max_side: int = 2048) -> bytes:
    """Optimize to PNG (convenience function)."""
    return await ImageProcessor.optimize_to_png(buffer, max_side)


# Image encoding functions
def _mime_from_extension(path: str) -> str | None:
    """Get MIME type from file extension."""
    ext = os.path.splitext(path)[1].lower()
    if not ext:
        return None
    ext = ext.lstrip(".")
    mapping = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "webp": "image/webp",
        "bmp": "image/bmp",
        "tiff": "image/tiff",
    }
    return mapping.get(ext)


async def encode_image_to_base64(image_source: str) -> str:
    """
    Encode an image from a URL or local path to a Base64 data URI.

    Detection order for MIME type:
    1. Use response Content-Type if it's an image/*
    2. Use imghdr to detect image type from bytes
    3. Infer from URL/local file extension
    4. Fallback to image/jpeg

    Args:
        image_source: URL or local file path to image

    Returns:
        Base64 data URI string (format: data:image/...;base64,...)
    """
    try:
        # Fetch bytes
        if image_source.startswith(("http://", "https://")):
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(image_source)
                if response.status_code != 200:
                    raise Exception(f"Download failed: {response.status_code}")
                content = response.content
                header_ct = (response.headers.get("Content-Type") or "").lower()
        else:
            with open(image_source, "rb") as f:
                content = f.read()
            header_ct = ""

        # 1) Prefer response header if it clearly identifies an image
        if header_ct and header_ct.startswith("image/"):
            mime_type = header_ct
        else:
            # 2) Try imghdr to detect type from content
            img_type = imghdr.what(None, h=content)
            if img_type:
                mime_type = f"image/{img_type}"
            else:
                # 3) Try to infer from URL/file extension
                try:
                    path = urlparse(image_source).path
                    ext_mime = _mime_from_extension(path)
                except Exception:
                    ext_mime = None

                if ext_mime:
                    mime_type = ext_mime
                else:
                    # 4) Fallback
                    mime_type = "image/jpeg"

        base64_str = base64.b64encode(content).decode("utf-8")
        logger.info(
            f"Encoded image from {image_source} to Base64 (size: {len(base64_str)} chars), mime={mime_type}"
        )
        return f"data:{mime_type};base64,{base64_str}"

    except Exception as e:
        logger.error(f"Encoding error for {image_source}: {e}")
        return image_source
