# PowerPoint Generation Skill

Generate professional PowerPoint presentations programmatically using the OpenClaw agent.

## Overview

This skill enables the OpenClaw agent to create PowerPoint presentations (.pptx files) based on natural language requests. Users can request presentations with specific content, layouts, and themes, and receive a ready-to-use .pptx file.

## Features

- **Multiple Slide Layouts**: Title, content, section headers, blank slides
- **Text Formatting**: Bullet points, paragraphs, titles, subtitles
- **Theme Support**: Default professional template + custom themes
- **Automatic Generation**: From simple text descriptions to complete presentations
- **File Delivery**: Direct download via Telegram or other channels

## Quick Start

### Installation

```bash
# Install dependency
pip install python-pptx>=0.6.23

# Or install all project dependencies
cd openclaw-python
pip install -e .
```

### Basic Usage

**Via Telegram Bot:**

Simply send a message like:
- "Create a 3-slide presentation about Python programming"
- "Make a presentation with title 'Q1 Results' and 5 content slides"
- "Generate slides about machine learning, deep learning, and AI applications"

The agent will:
1. Understand your request
2. Generate appropriate slide content
3. Create the .pptx file
4. Send it to you via Telegram

**Direct Script Usage:**

```bash
# Create configuration
cat > config.json << 'EOF'
{
  "title": "My Presentation",
  "slides": [
    {
      "layout": "title",
      "title": "Main Title",
      "subtitle": "Subtitle"
    },
    {
      "layout": "content",
      "title": "Key Points",
      "content": {
        "bullets": ["Point 1", "Point 2", "Point 3"]
      }
    }
  ]
}
EOF

# Generate presentation
python scripts/generate_ppt.py --config config.json --output presentation.pptx
```

## File Structure

```
powerpoint/
├── SKILL.md                  # Main skill definition (loaded by agent)
├── README.md                 # This file
├── TEST_GUIDE.md            # Testing instructions
├── scripts/
│   ├── generate_ppt.py      # Main generation script
│   ├── add_slide.py         # Helper: add single slide
│   ├── apply_theme.py       # Helper: apply theme
│   └── create_default_template.py  # Create default template
├── assets/
│   ├── README.md            # Assets documentation
│   ├── default_template.pptx  # Default template (auto-generated)
│   └── themes/              # Custom theme templates
└── references/
    └── pptx_api_guide.md    # python-pptx API reference
```

## Configuration Format

The generation script uses JSON configuration:

```json
{
  "title": "Presentation Title",
  "author": "Author Name",
  "template": "assets/themes/custom.pptx",  // Optional
  "slides": [
    {
      "layout": "title",
      "title": "Main Title",
      "subtitle": "Subtitle"
    },
    {
      "layout": "content",
      "title": "Slide Title",
      "content": {
        "bullets": ["First point", "Second point"],
        // OR
        "text": "Paragraph text"
      }
    },
    {
      "layout": "section",
      "title": "Section Header"
    },
    {
      "layout": "blank",
      "title": "Optional title"
    }
  ]
}
```

## Supported Layouts

| Layout | Description | Usage |
|--------|-------------|-------|
| `title` | Title slide | Main presentation title + subtitle |
| `content` | Content slide | Title + bullet points or text |
| `section` | Section header | Section divider slide |
| `blank` | Blank slide | Empty slide for custom content |

## Example Requests

### Simple Presentation

"Create a 3-slide presentation about Python programming with introduction, features, and conclusion"

### Business Presentation

"Make a presentation about Q1 2026 results with:
- Title slide
- Executive summary with 3 key points
- Revenue breakdown with 4 bullet points
- Goals for Q2 with 5 action items"

### Educational Content

"Generate slides for a lecture on machine learning covering:
- Introduction to ML
- Supervised learning concepts
- Unsupervised learning concepts
- Real-world applications
- Conclusion"

## Customization

### Custom Themes

1. Create a PowerPoint template with your branding
2. Save it in `assets/themes/your_theme.pptx`
3. Reference in config: `"template": "assets/themes/your_theme.pptx"`

### Script Modification

The generation scripts are designed to be extended:
- Modify `scripts/generate_ppt.py` for custom slide types
- Add image support in slide generation
- Implement chart generation
- Add custom formatting

## Limitations

- No animation or transition support
- Basic chart support only
- No embedded video
- Images must be file paths or URLs
- Recommended maximum: 50 slides per presentation

## Troubleshooting

### python-pptx Not Installed

```bash
pip install python-pptx>=0.6.23
```

### Template Not Found

The script will create a blank presentation. To generate the default template:

```bash
python scripts/create_default_template.py
```

### File Not Sent via Telegram

- Check file path is absolute
- Verify file size < 50MB
- Review Telegram channel logs
- Ensure send_media supports local files

## Integration

### With OpenClaw Agent

The skill integrates automatically when:
1. SKILL.md is in `openclaw/skills/powerpoint/`
2. Dependencies are installed
3. Gateway is running

The agent will trigger this skill when it detects presentation-related requests.

### With Other Tools

The scripts can be used standalone:

```bash
# Generate presentation
python scripts/generate_ppt.py --config config.json --output output.pptx

# Add slide to existing presentation
python scripts/add_slide.py --pptx existing.pptx --layout content --title "New Slide" --output updated.pptx

# Apply theme
python scripts/apply_theme.py --pptx presentation.pptx --theme theme.pptx --output themed.pptx
```

## Development

### Testing

See [TEST_GUIDE.md](TEST_GUIDE.md) for comprehensive testing instructions.

Quick test:

```bash
# Run test suite
./test_powerpoint_skill.sh
```

### Contributing

When adding features:
1. Update SKILL.md with new capabilities
2. Add examples to the API guide
3. Include tests in TEST_GUIDE.md
4. Update this README

## Resources

- **SKILL.md**: Main skill definition and agent instructions
- **TEST_GUIDE.md**: Testing and verification procedures
- **references/pptx_api_guide.md**: python-pptx API reference
- **assets/README.md**: Template and theme documentation

## License

Part of the openclaw-python project. See main project LICENSE.

## Support

For issues or questions:
1. Check TEST_GUIDE.md for troubleshooting
2. Review gateway logs for errors
3. Verify dependencies are installed
4. See references/pptx_api_guide.md for API details
