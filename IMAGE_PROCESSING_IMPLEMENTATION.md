# Image Processing Implementation

Complete image handling system matching TypeScript OpenClaw implementation.

## Overview

This implementation provides full-featured image processing capabilities equivalent to the TypeScript version:

- ✅ **Multi-source image loading** (files, URLs, data URLs)
- ✅ **HEIC conversion** to JPEG
- ✅ **Image optimization** (resize, quality adjustment, compression)
- ✅ **MIME type detection**
- ✅ **Vision model integration** (Claude, GPT-4)
- ✅ **Model fallback** mechanism
- ✅ **Sandbox path validation**
- ✅ **Telegram media** download and processing

## Architecture

### Core Modules

```
openclaw/media/
├── __init__.py           # Public API
├── mime.py               # MIME detection (matches src/media/mime.ts)
├── loader.py             # Media loading (matches src/web/media.ts)
└── image_ops.py          # Image operations (matches src/media/image-ops.ts)

openclaw/agents/tools/
└── image.py              # Image tool (matches src/agents/tools/image-tool.ts)

openclaw/channels/
└── telegram_media.py     # Telegram media handling (matches src/web/inbound/media.ts)
```

## Key Features

### 1. Media Loading (`media/loader.py`)

**Matches:** `src/web/media.ts`

```python
from openclaw.media import load_media

# Load from any source
media = await load_media(
    source="path/to/image.jpg",  # or URL or data URL
    max_bytes=20 * 1024 * 1024,  # 20MB limit
    optimize_images=True,
    workspace_root=Path("/workspace")  # Optional sandbox
)
```

**Supported sources:**
- Local files (`/path/to/image.jpg`, `~/image.jpg`)
- File URLs (`file:///path/to/image.jpg`)
- HTTP/HTTPS URLs (`https://example.com/image.jpg`)
- Data URLs (`data:image/png;base64,...`)

**Features:**
- Automatic MIME detection
- Size limits with enforcement
- Sandboxed access (workspace-relative paths)
- Media/inbound fallback (matches TS `resolveSandboxedImagePath`)

### 2. MIME Detection (`media/mime.py`)

**Matches:** `src/media/mime.ts`

```python
from openclaw.media import detect_mime, MediaKind, media_kind_from_mime

# Detect MIME from buffer or file
mime = detect_mime(buffer=image_bytes)  # "image/jpeg"

# Get media kind
kind = media_kind_from_mime(mime)  # MediaKind.IMAGE

# Extension mapping
from openclaw.media.mime import extension_for_mime
ext = extension_for_mime("image/jpeg")  # ".jpg"
```

**Supported types:**
- Images: JPEG, PNG, GIF, WebP, HEIC/HEIF
- Audio: MP3, OGG, M4A, WAV, FLAC, OPUS
- Video: MP4, MOV
- Documents: PDF, Office formats, text files

### 3. Image Operations (`media/image_ops.py`)

**Matches:** `src/media/image-ops.ts`

```python
from openclaw.media.image_ops import ImageProcessor

# Convert HEIC to JPEG
jpeg_buffer = await ImageProcessor.convert_heic_to_jpeg(heic_buffer)

# Resize to JPEG
resized = await ImageProcessor.resize_to_jpeg(
    buffer,
    max_side=2048,
    quality=85
)

# Optimize to PNG (preserving alpha)
optimized = await ImageProcessor.optimize_to_png(
    buffer,
    max_side=2048,
    compression_level=9
)

# Smart optimization (tries multiple strategies)
result = await ImageProcessor.optimize_image(
    buffer,
    max_bytes=5 * 1024 * 1024,  # 5MB target
    preserve_alpha=True
)
```

**Image backends:**
- **Pillow** (primary) - Full feature support
- **pillow-heif** - HEIC/HEIF conversion
- **sips** (macOS fallback) - HEIC conversion without dependencies

**Features:**
- HEIC/HEIF to JPEG conversion
- Smart resizing (maintains aspect ratio)
- Quality/compression optimization
- Alpha channel preservation
- Multi-strategy optimization (progressively smaller sizes/qualities)

### 4. Vision Tool (`agents/tools/image.py`)

**Matches:** `src/agents/tools/image-tool.ts`

```python
from openclaw.agents.tools.image import ImageTool

# Create tool
tool = ImageTool(
    workspace_root=Path("/workspace"),  # Optional sandbox
    model_has_vision=False,            # Adjust description
    max_bytes_mb=20.0,                 # Size limit
    optimize_images=True               # Auto-optimize
)

# Execute
result = await tool.execute({
    "image": "path/to/image.jpg",  # or URL or data URL
    "prompt": "Describe this image",
    "model": "claude-3-5-sonnet-20241022"  # Optional
})
```

**Features:**
- Multi-model support (Claude, GPT-4, MiniMax)
- **Automatic model fallback** (matches TS `runWithImageModelFallback`)
- HEIC auto-conversion
- Image optimization before API call
- Sandbox path validation
- @ prefix stripping (matches TS line 346)
- Data URL support

**Fallback order:**
1. Model override (if specified)
2. Claude Sonnet 4 (`claude-3-5-sonnet-20241022`)
3. GPT-4 Vision (`gpt-4-vision-preview`)
4. Claude Sonnet 3.5 (fallback)

### 5. Telegram Media (`channels/telegram_media.py`)

**Matches:** `src/web/inbound/media.ts` patterns

```python
from openclaw.channels.telegram_media import TelegramMediaHandler

# Initialize
handler = TelegramMediaHandler(
    workspace_root=Path("/workspace"),
    max_bytes=20 * 1024 * 1024
)

# Download media from message
buffer, info = await handler.download_media(
    message,
    save_to_workspace=True
)

# Or get as data URL
data_url, info = await handler.get_media_as_data_url(message)
```

**Supported Telegram media:**
- Photos (automatically selects largest size)
- Documents
- Videos
- Audio
- Voice messages
- Stickers

**Features:**
- Auto-save to `workspace/media/inbound/`
- Filename collision handling
- MIME type detection
- Size limit enforcement
- Data URL conversion for API calls

## TypeScript Alignment

### Feature Parity Matrix

| Feature | TypeScript | Python | Status |
|---------|-----------|--------|--------|
| File loading | ✓ | ✓ | ✅ Complete |
| HTTP URL loading | ✓ | ✓ | ✅ Complete |
| Data URL loading | ✓ | ✓ | ✅ Complete |
| HEIC conversion | ✓ | ✓ | ✅ Complete |
| Image optimization | ✓ | ✓ | ✅ Complete |
| MIME detection | ✓ | ✓ | ✅ Complete |
| Vision models | ✓ | ✓ | ✅ Complete |
| Model fallback | ✓ | ✓ | ✅ Complete |
| Sandbox paths | ✓ | ✓ | ✅ Complete |
| Media/inbound fallback | ✓ | ✓ | ✅ Complete |
| @ prefix stripping | ✓ | ✓ | ✅ Complete |
| Telegram download | ✓ | ✓ | ✅ Complete |
| WhatsApp download | ✓ | - | ⏳ Future |

### Key Alignments

1. **Session Key Format** (lines from `image-tool.ts:346`)
   ```typescript
   // TS: Remove @ prefix
   const imageRaw = imageRawInput.startsWith("@")
     ? imageRawInput.slice(1).trim()
     : imageRawInput;
   ```
   ```python
   # Python: Same logic
   if image_input.startswith("@"):
       image_input = image_input[1:].strip()
   ```

2. **Sandbox Path Resolution** (matches `resolveSandboxedImagePath`)
   ```typescript
   // TS: Try media/inbound fallback
   const candidateRel = path.join("media", "inbound", name);
   ```
   ```python
   # Python: Same fallback
   fallback = workspace / "media" / "inbound" / path.name
   ```

3. **Model Fallback** (matches `runWithImageModelFallback`)
   ```typescript
   // TS: Try models with fallback
   const result = await runWithImageModelFallback({...})
   ```
   ```python
   # Python: Same pattern
   result = await self._analyze_with_fallback(...)
   ```

4. **Image Optimization** (matches `optimizeImageWithFallback`)
   ```typescript
   // TS: Progressive size reduction
   for (const maxSide of [2048, 1536, 1024, 768, 512]) { ... }
   ```
   ```python
   # Python: Same strategy
   for max_side in [2048, 1536, 1024, 768, 512]:
   ```

## Dependencies

### Required
```toml
httpx = ">=0.24.0"        # HTTP client
```

### Image Processing (Optional)
```toml
Pillow = ">=10.0.0"       # Image operations
pillow-heif = ">=0.10.0"  # HEIC support
filetype = ">=1.2.0"      # MIME detection
```

### Vision Models (Optional)
```toml
anthropic = ">=0.18.0"    # Claude
openai = ">=1.0.0"        # GPT-4 Vision
```

## Usage Examples

### Basic Image Analysis

```python
from openclaw.agents.tools.image import ImageTool

tool = ImageTool()

# Analyze image
result = await tool.execute({
    "image": "photo.jpg",
    "prompt": "What's in this image?"
})

print(result.content)  # AI description
```

### With Optimization

```python
tool = ImageTool(
    max_bytes_mb=5.0,      # 5MB limit
    optimize_images=True   # Auto-optimize
)

result = await tool.execute({
    "image": "large_photo.heic",  # Will be converted & optimized
    "prompt": "Describe the scene"
})
```

### Sandboxed Access

```python
from pathlib import Path

tool = ImageTool(workspace_root=Path("/workspace"))

# Only files inside /workspace/ are accessible
result = await tool.execute({
    "image": "image.jpg",  # Will check /workspace/media/inbound/image.jpg
    "prompt": "Analyze"
})
```

### Telegram Integration

```python
from openclaw.channels.telegram_media import TelegramMediaHandler

handler = TelegramMediaHandler(
    workspace_root=Path("/workspace")
)

# In message handler
async def on_message(message):
    if message.photo:
        buffer, info = await handler.download_media(message)
        print(f"Downloaded {info.media_type}: {len(buffer)} bytes")
        
        # Use with image tool
        data_url, _ = await handler.get_media_as_data_url(message)
        result = await image_tool.execute({
            "image": data_url,
            "prompt": "What's in this photo?"
        })
```

### Direct Media Loading

```python
from openclaw.media import load_media

# From file
media = await load_media("photo.jpg")

# From URL
media = await load_media("https://example.com/image.png")

# From data URL
media = await load_media("data:image/png;base64,...")

print(media.kind)         # MediaKind.IMAGE
print(media.content_type) # "image/jpeg"
print(len(media.buffer))  # Size in bytes
```

## Testing

Comprehensive test suite covering all functionality:

```bash
# Run all media tests
pytest tests/media/

# Run specific test files
pytest tests/media/test_mime.py       # MIME detection
pytest tests/media/test_loader.py     # Media loading
pytest tests/media/test_image_ops.py  # Image operations
pytest tests/agents/test_image_tool.py # Image tool

# Run with coverage
pytest --cov=openclaw.media tests/media/
```

**Test coverage:**
- ✅ MIME detection and mapping
- ✅ Data URL parsing
- ✅ File loading (with sandbox)
- ✅ Size limit enforcement
- ✅ HEIC conversion
- ✅ Image resize/optimization
- ✅ Alpha channel detection
- ✅ Tool schema and execution
- ✅ @ prefix handling
- ✅ Model fallback logic

## Performance Notes

### Image Optimization Strategy

Matches TypeScript `optimizeImageWithFallback`:

1. **Check if already under limit** → return as-is
2. **Try progressive resizing** (2048 → 1536 → 1024 → 768 → 512)
3. **For JPEG:** Try quality levels (85 → 75 → 65 → 55)
4. **For PNG:** Use max compression (level 9)
5. **Preserve alpha** if requested

### HEIC Conversion Backends

**Priority order:**
1. **pillow-heif** (Pillow plugin) - Best quality, cross-platform
2. **sips** (macOS) - No dependencies, macOS only
3. **Fail** with helpful error message

## Migration Guide

### From Basic Image Tool

**Before:**
```python
tool = ImageTool()
result = await tool.execute({"image": path, "prompt": prompt})
```

**After (with new features):**
```python
tool = ImageTool(
    workspace_root=workspace,  # Add sandbox
    optimize_images=True,      # Enable optimization
    max_bytes_mb=10.0         # Set size limit
)
result = await tool.execute({
    "image": path,
    "prompt": prompt,
    "model": "claude-3-5-sonnet-20241022"  # Specify model
})
```

### Adding Telegram Support

```python
from openclaw.channels.telegram_media import TelegramMediaHandler

# Initialize handler
media_handler = TelegramMediaHandler(
    workspace_root=workspace,
    max_bytes=20 * 1024 * 1024
)

# In message handler
async def handle_photo(update, context):
    message = update.message
    
    # Download
    buffer, info = await media_handler.download_media(message)
    
    # Analyze with vision model
    data_url, _ = await media_handler.get_media_as_data_url(message)
    result = await image_tool.execute({
        "image": data_url,
        "prompt": "Describe this photo"
    })
    
    await message.reply_text(result.content)
```

## Known Limitations

1. **HEIC Conversion:**
   - Requires `pillow-heif` or macOS `sips`
   - Fallback error message guides installation

2. **Image Backends:**
   - Pillow required for most operations
   - Graceful degradation without it

3. **Remote URLs:**
   - Disabled in sandboxed mode (matches TS behavior)
   - Size limits enforced before download completes

## Future Enhancements

- [ ] WhatsApp media support
- [ ] Video thumbnail extraction
- [ ] GIF animation handling
- [ ] PDF page rendering
- [ ] Image metadata preservation (EXIF)
- [ ] Progressive JPEG loading
- [ ] WebP conversion

## Summary

This implementation provides **complete feature parity** with the TypeScript OpenClaw image processing system:

✅ All loading methods (file/URL/data URL)  
✅ HEIC conversion  
✅ Image optimization  
✅ Vision model integration  
✅ Model fallback  
✅ Sandbox security  
✅ Telegram integration  
✅ Comprehensive tests  

The Python implementation matches the TypeScript architecture, function signatures, and behavior while leveraging Python idioms and best practices.
