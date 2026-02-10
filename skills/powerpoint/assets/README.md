# PowerPoint Skill Assets

This directory contains template files and themes for PowerPoint generation.

## Files

### default_template.pptx

The default professional template used when no custom template is specified.

**Creation:** This file is auto-generated on first use if it doesn't exist, or can be created manually by running:

```bash
python ../scripts/create_default_template.py
```

### themes/

Directory for custom theme templates. Place your custom `.pptx` templates here and reference them in your configuration:

```json
{
  "template": "assets/themes/corporate_blue.pptx",
  "slides": [...]
}
```

## Creating Custom Themes

1. Create a PowerPoint presentation with your desired styling
2. Set up slide masters with your branding
3. Save as `themes/your_theme_name.pptx`
4. Reference in generation config with `"template": "assets/themes/your_theme_name.pptx"`

## Default Template Generation

If `default_template.pptx` doesn't exist, the generation script will create a blank presentation with standard layouts. For a more professional look, run the template creation script after installing dependencies:

```bash
cd openclaw-python
python -m pip install python-pptx>=0.6.23
python openclaw/skills/powerpoint/scripts/create_default_template.py
```
