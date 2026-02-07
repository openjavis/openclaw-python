"""Media handling (images, audio, video)"""

from .image_ops import encode_image_to_base64
from .loader import MediaLoader, MediaResult, load_media
from .mime import MediaKind, detect_mime, extension_for_mime, media_kind_from_mime

__all__ = [
    "MediaLoader",
    "MediaResult",
    "load_media",
    "MediaKind",
    "detect_mime",
    "extension_for_mime",
    "media_kind_from_mime",
    "encode_image_to_base64",
]
