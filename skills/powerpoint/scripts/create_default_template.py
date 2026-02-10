#!/usr/bin/env python3
"""
Create Default Template Script

Generates the default PowerPoint template for the skill.
This is run once to create assets/default_template.pptx
"""

import sys
from pathlib import Path

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.enum.text import PP_ALIGN
    from pptx.dml.color import RGBColor
except ImportError:
    print("Error: python-pptx not installed", file=sys.stderr)
    sys.exit(1)


def create_default_template():
    """Create a basic professional template"""
    
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)
    
    # Set default properties
    prs.core_properties.title = "OpenClaw Presentation"
    prs.core_properties.author = "OpenClaw"
    
    # Get script directory
    script_dir = Path(__file__).parent
    assets_dir = script_dir.parent / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    
    # Save template
    template_path = assets_dir / "default_template.pptx"
    prs.save(str(template_path))
    
    print(f"✅ Created default template: {template_path}")
    return str(template_path)


if __name__ == "__main__":
    try:
        create_default_template()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
