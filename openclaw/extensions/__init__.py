"""Extension system for pi agent runtime

Extensions extend the agent runtime (NOT the gateway).
This is fundamentally different from plugins.

Matches TypeScript pi-mono/packages/coding-agent/src/core/extensions/
"""
from .api import ExtensionAPI
from .loader import ExtensionLoader, discover_extensions
from .runner import ExtensionRunner
from .runtime import ExtensionRuntime
from .types import Extension, ExtensionContext, ExtensionManifest
from .memory_extension import MemoryExtension, create_memory_extension

__all__ = [
    "ExtensionAPI",
    "ExtensionLoader",
    "ExtensionRunner", 
    "ExtensionRuntime",
    "Extension",
    "ExtensionContext",
    "ExtensionManifest",
    "discover_extensions",
    "MemoryExtension",
    "create_memory_extension",
]

__all__ = [
    "Extension",
    "ExtensionManifest",
    "ExtensionContext",
    "ExtensionAPI",
    "ExtensionLoader",
    "ExtensionRunner",
    "ExtensionRuntime",
    "discover_extensions",
]
