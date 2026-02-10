---
name: powerpoint
description: Create and generate PowerPoint presentations (.pptx files). Use when user requests creating a new presentation, generating slides with specific content, adding charts/images to slides, or applying themes/templates. Can generate the file and send it back via Telegram or other channels.
---

# PowerPoint Generation Skill

Generate professional PowerPoint presentations programmatically using python-pptx library.

## Overview

This skill enables creating PowerPoint presentations with:
- Multiple slide layouts (title, content, bullet points, images)
- Text formatting and styling
- Basic charts and tables
- Theme application
- File generation and delivery

## Workflow Decision Tree

1. **Analyze Request** → Identify slide count, content type, theme preference
2. **Determine Output Location** → Use session workspace presentations directory with timestamp filename
3. **Prepare Configuration** → Create JSON config with slide definitions
4. **Execute Generation** → Run `scripts/generate_ppt.py` with configuration
5. **Return File Info** → Include file_path, file_type, and caption in tool result
6. **Auto Send** → System automatically sends .pptx file via channel

## Core Operations

### 1. Create Basic Text Presentation

**Use case:** Simple presentation with title and bullet points

**Steps:**
1. Create JSON config:
```json
{
  "title": "Presentation Title",
  "slides": [
    {
      "layout": "title",
      "title": "Main Title",
      "subtitle": "Subtitle text"
    },
    {
      "layout": "content",
      "title": "Slide Title",
      "content": {
        "bullets": [
          "First point",
          "Second point",
          "Third point"
        ]
      }
    }
  ]
}
```

2. Determine output path:
```python
# Use file_manager utilities
from openclaw.agents.tools.file_manager import prepare_file_for_sending
output_path, filename = prepare_file_for_sending(
    workspace_dir=session.workspace_dir,
    file_category="presentations",
    title="Presentation Title"  # Extract from request
)
# Example output: /workspace/presentations/Presentation_Title_20260208_143022.pptx
```

3. Execute generation:
```bash
# Script automatically returns JSON with file info
python skills/powerpoint/scripts/generate_ppt.py \
  --config /path/to/config.json \
  --output {output_path}

# Output (automatically):
# {"file_path": "/full/path.pptx", "file_type": "document", "caption": "已生成演示文稿：Title"}
```

4. System automatically handles file sending:
- Script returns JSON with file_path, file_type, caption
- Runtime detects file info and emits AGENT_FILE_GENERATED event
- Channel Manager sends file via Telegram/channel
- User receives .pptx file instantly

### 2. Create Presentation with Multiple Layouts

**Supported layouts:**
- `title` - Title slide (main title + subtitle)
- `content` - Content slide (title + bullet points or text)
- `section` - Section header slide
- `blank` - Blank slide for custom content

**Example configuration:**
```json
{
  "title": "Project Overview",
  "author": "OpenClaw",
  "slides": [
    {
      "layout": "title",
      "title": "Project Overview",
      "subtitle": "2026 Q1 Report"
    },
    {
      "layout": "section",
      "title": "Executive Summary"
    },
    {
      "layout": "content",
      "title": "Key Findings",
      "content": {
        "bullets": [
          "Revenue increased 25%",
          "Customer satisfaction: 92%",
          "New product launch successful"
        ]
      }
    },
    {
      "layout": "content",
      "title": "Next Steps",
      "content": {
        "text": "We will focus on expanding our market presence and improving customer experience."
      }
    }
  ]
}
```

### 3. Apply Themes and Styling

**Basic styling options:**
- Font size adjustment
- Color schemes (via theme templates)
- Layout customization

**Using default template:**
The skill includes `assets/default_template.pptx` which provides professional styling.

**Custom themes:**
Place custom .pptx template files in `assets/themes/` and reference them:
```json
{
  "template": "assets/themes/corporate_blue.pptx",
  "slides": [...]
}
```

## Script Reference

### generate_ppt.py

Main PowerPoint generation script.

**Arguments:**
- `--config PATH` - JSON configuration file (required)
- `--output PATH` - Output .pptx file path (required)
- `--template PATH` - Template .pptx file (optional, uses default if not specified)

**Returns:**
- Exit code 0 on success
- Prints output file path to stdout
- Exit code 1 on error with error message to stderr

**Example usage:**
```bash
python openclaw/skills/powerpoint/scripts/generate_ppt.py \
  --config /tmp/presentation_config.json \
  --output ~/.openclaw/workspace/presentations/my_presentation.pptx
```

### add_slide.py

Helper script to add a single slide to an existing presentation.

**Arguments:**
- `--pptx PATH` - Existing presentation file
- `--layout TYPE` - Slide layout (title/content/section/blank)
- `--title TEXT` - Slide title
- `--content JSON` - Slide content as JSON

### apply_theme.py

Helper script to apply a theme to an existing presentation.

**Arguments:**
- `--pptx PATH` - Presentation file to modify
- `--theme PATH` - Theme template file
- `--output PATH` - Output file path

## Integration with Channels

### Telegram
After generating the presentation, use the Message tool to send:
```python
# Agent will call this internally
message(
  channel="telegram",
  target="<chat_id>",
  media_url="/path/to/presentation.pptx",
  media_type="document",
  text="Here's your presentation!"
)
```

### File Handling
- Generated files are saved to: `~/.openclaw/workspace/presentations/`
- Temporary config files use: `/tmp/openclaw_ppt_*.json`
- Files are automatically cleaned up after sending

## Examples

### Example 1: Simple 3-Slide Presentation

**User request:** "Create a 3-slide presentation about Python programming"

**Agent workflow:**
1. Create config with title slide, content slides
2. Execute `generate_ppt.py` with configuration
3. Save to workspace
4. Send via Telegram

### Example 2: Multi-Section Presentation

**User request:** "Create a presentation with introduction, 3 topics, and conclusion"

**Agent workflow:**
1. Create config with:
   - Title slide
   - Section slide for "Introduction"
   - 3 content slides for topics
   - Section slide for "Conclusion"
2. Execute generation
3. Deliver file

## Troubleshooting

**Error: "python-pptx not installed"**
- Solution: Install dependency: `pip install python-pptx>=0.6.23`

**Error: "Template file not found"**
- Solution: Ensure default_template.pptx exists in assets/ or specify custom template

**Error: "Cannot send file via Telegram"**
- Solution: Check that send_media supports local file paths
- Verify file size is under Telegram's limit (50MB for documents)

## Resources

- **scripts/generate_ppt.py** - Main generation script with full implementation
- **scripts/add_slide.py** - Helper for adding individual slides
- **scripts/apply_theme.py** - Helper for theme application
- **assets/default_template.pptx** - Default professional template
- **references/pptx_api_guide.md** - python-pptx API reference and examples

## Limitations

- No support for complex animations or transitions
- Charts are basic (bar, line, pie only)
- Images must be accessible file paths or URLs
- Maximum recommended slides: 50 (performance consideration)

## Tips

- Keep slide content concise (5-7 bullets maximum per slide)
- Use section slides to organize long presentations
- Test with simple presentations first
- Generated files are typically 50-500KB depending on content

## Important Implementation Notes

### File Output and Auto-Sending (CRITICAL)

When generating PowerPoint files, always follow this workflow:

1. **Use workspace presentations directory**:
   ```python
   from openclaw.agents.tools.file_manager import prepare_file_for_sending
   output_path, filename = prepare_file_for_sending(
       workspace_dir=session.workspace_dir,
       file_category="presentations",
       title="AI Introduction"  # Extract from user request
   )
   # Returns: /workspace/session-xxx/presentations/AI_Introduction_20260208_143022.pptx
   ```

2. **Return file information in tool result**:
   ```python
   # Your bash tool result MUST include these keys:
   {
       "file_path": "/full/path/to/presentation.pptx",
       "file_type": "document",
       "caption": "已生成演示文稿：AI Introduction"
   }
   ```

3. **System automatically sends file**:
   - Runtime detects `file_path` in tool result
   - Emits `AGENT_FILE_GENERATED` event
   - Channel Manager receives event
   - Sends .pptx file via Telegram/other channel
   - User receives file instantly

### File Naming Convention

- Format: `{sanitized_title}_{YYYYMMDD_HHMMSS}.pptx`
- Title is sanitized: special chars removed, spaces → underscores
- Examples:
  - `AI_Introduction_20260208_143022.pptx`
  - `Q1_Report_20260208_150000.pptx`
  - `Python_Tutorial_20260208_120000.pptx`

### Workspace Structure

```
~/.openclaw/workspace/
└── session-{session_id}/
    ├── presentations/      # PowerPoint files
    │   ├── AI_Intro_20260208.pptx
    │   └── Report_20260208.pptx
    ├── documents/          # PDF, Word files
    └── images/             # Generated images
```
