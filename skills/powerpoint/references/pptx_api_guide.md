# python-pptx API Reference Guide

Quick reference for the python-pptx library used in PowerPoint generation.

## Installation

```bash
pip install python-pptx>=0.6.23
```

## Basic Usage

### Create New Presentation

```python
from pptx import Presentation

prs = Presentation()  # Blank presentation
# or
prs = Presentation('template.pptx')  # From template
```

### Add Slides

```python
# Get a slide layout
title_slide_layout = prs.slide_layouts[0]  # Title slide
content_layout = prs.slide_layouts[1]      # Title and content

# Add a slide
slide = prs.slides.add_slide(title_slide_layout)
```

### Save Presentation

```python
prs.save('presentation.pptx')
```

## Slide Layouts

Common built-in layouts (indices may vary by template):

| Index | Layout Name | Description |
|-------|-------------|-------------|
| 0 | Title Slide | Title + subtitle |
| 1 | Title and Content | Title + body text |
| 2 | Section Header | Section title |
| 3 | Two Content | Title + two columns |
| 4 | Comparison | Title + comparison columns |
| 5 | Title Only | Title, blank body |
| 6 | Blank | Completely blank |

## Working with Text

### Title and Placeholders

```python
# Set title
slide.shapes.title.text = "Slide Title"

# Access placeholders
subtitle = slide.placeholders[1]
subtitle.text = "Subtitle text"
```

### Text Boxes

```python
from pptx.util import Inches, Pt

# Add text box
left = Inches(1)
top = Inches(2)
width = Inches(8)
height = Inches(1)

textbox = slide.shapes.add_textbox(left, top, width, height)
text_frame = textbox.text_frame
text_frame.text = "Hello World"
```

### Paragraphs and Formatting

```python
# Get text frame
text_frame = shape.text_frame

# Clear existing text
text_frame.clear()

# Add paragraphs
p = text_frame.paragraphs[0]
p.text = "First paragraph"
p.level = 0  # Indent level

p2 = text_frame.add_paragraph()
p2.text = "Second paragraph"
p2.level = 1  # Indented

# Formatting
p.font.size = Pt(18)
p.font.bold = True
p.font.italic = False
p.font.name = 'Arial'
```

### Bullet Points

```python
text_frame = slide.placeholders[1].text_frame
text_frame.clear()

# First bullet
p = text_frame.paragraphs[0]
p.text = "First bullet"
p.level = 0

# Additional bullets
for bullet_text in ["Second", "Third"]:
    p = text_frame.add_paragraph()
    p.text = bullet_text
    p.level = 0  # Level 0 = main bullet, 1 = sub-bullet
```

## Working with Colors

```python
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

# Set text color
run = p.runs[0]
run.font.color.rgb = RGBColor(255, 0, 0)  # Red

# Set background color
fill = shape.fill
fill.solid()
fill.fore_color.rgb = RGBColor(0, 128, 255)  # Blue

# Alignment
p.alignment = PP_ALIGN.CENTER  # or LEFT, RIGHT, JUSTIFY
```

## Adding Images

```python
from pptx.util import Inches

# Add image
img_path = 'image.jpg'
left = Inches(1)
top = Inches(2)
width = Inches(3)
height = Inches(2)

pic = slide.shapes.add_picture(img_path, left, top, width, height)
```

## Adding Shapes

```python
from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Inches

# Add a shape
left = Inches(1)
top = Inches(2)
width = Inches(2)
height = Inches(1)

shape = slide.shapes.add_shape(
    MSO_SHAPE.RECTANGLE,
    left, top, width, height
)

# Set shape properties
shape.fill.solid()
shape.fill.fore_color.rgb = RGBColor(0, 128, 255)
shape.line.color.rgb = RGBColor(0, 0, 0)
```

## Adding Tables

```python
from pptx.util import Inches

# Add table
rows = 3
cols = 3
left = Inches(1)
top = Inches(2)
width = Inches(8)
height = Inches(3)

table = slide.shapes.add_table(rows, cols, left, top, width, height).table

# Set cell values
table.cell(0, 0).text = "Header 1"
table.cell(0, 1).text = "Header 2"
table.cell(1, 0).text = "Row 1, Col 1"
table.cell(1, 1).text = "Row 1, Col 2"

# Format cells
cell = table.cell(0, 0)
cell.text_frame.paragraphs[0].font.bold = True
```

## Adding Charts

```python
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE
from pptx.util import Inches

# Prepare chart data
chart_data = CategoryChartData()
chart_data.categories = ['Q1', 'Q2', 'Q3', 'Q4']
chart_data.add_series('Sales', (10, 15, 12, 18))

# Add chart
x, y, cx, cy = Inches(2), Inches(2), Inches(6), Inches(4)
chart = slide.shapes.add_chart(
    XL_CHART_TYPE.COLUMN_CLUSTERED,
    x, y, cx, cy,
    chart_data
).chart

# Customize chart
chart.has_legend = True
chart.legend.position = XL_LEGEND_POSITION.BOTTOM
```

## Presentation Properties

```python
# Set metadata
prs.core_properties.title = 'Presentation Title'
prs.core_properties.author = 'Author Name'
prs.core_properties.subject = 'Subject'
prs.core_properties.keywords = 'keyword1, keyword2'
prs.core_properties.comments = 'Comments'

# Slide size
from pptx.util import Inches
prs.slide_width = Inches(10)  # Standard 4:3
prs.slide_height = Inches(7.5)

# Or for 16:9
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
```

## Common Patterns

### Iterate Through Slides

```python
for slide in prs.slides:
    print(f"Slide {slide.slide_id}")
    for shape in slide.shapes:
        if hasattr(shape, "text"):
            print(f"  Shape text: {shape.text}")
```

### Clone a Slide

```python
# python-pptx doesn't support direct cloning
# Workaround: copy elements manually or use template approach
```

### Find Shapes by Type

```python
from pptx.enum.shapes import MSO_SHAPE_TYPE

for shape in slide.shapes:
    if shape.shape_type == MSO_SHAPE_TYPE.TEXT_BOX:
        print(f"Text box: {shape.text}")
    elif shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
        print("Found an image")
```

## Error Handling

```python
try:
    prs = Presentation('template.pptx')
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    prs.save('output.pptx')
except FileNotFoundError:
    print("Template file not found")
except IndexError:
    print("Layout index out of range")
except Exception as e:
    print(f"Error: {e}")
```

## Best Practices

1. **Use Templates**: Start with a template for consistent styling
2. **Check Layout Count**: Verify layout index before using
3. **Handle Exceptions**: Wrap I/O operations in try-catch
4. **Test Incrementally**: Build presentations step by step
5. **Units**: Always use `Inches()` or `Pt()` for measurements
6. **Resources**: Close file handles and cleanup temporary files

## Limitations

- No animation or transition support
- No embedded video support
- Limited chart customization compared to PowerPoint UI
- No direct slide master editing
- No SmartArt support

## References

- Official Documentation: https://python-pptx.readthedocs.io/
- GitHub Repository: https://github.com/scanny/python-pptx
- API Reference: https://python-pptx.readthedocs.io/en/latest/api/

## Quick Example: Complete Presentation

```python
from pptx import Presentation
from pptx.util import Inches, Pt

# Create presentation
prs = Presentation()

# Title slide
title_slide = prs.slides.add_slide(prs.slide_layouts[0])
title_slide.shapes.title.text = "Project Overview"
title_slide.placeholders[1].text = "Q1 2026 Report"

# Content slide
content_slide = prs.slides.add_slide(prs.slide_layouts[1])
content_slide.shapes.title.text = "Key Points"

text_frame = content_slide.placeholders[1].text_frame
text_frame.clear()

points = ["Revenue up 25%", "Customer satisfaction: 92%", "New product launched"]
for i, point in enumerate(points):
    p = text_frame.paragraphs[0] if i == 0 else text_frame.add_paragraph()
    p.text = point
    p.level = 0

# Save
prs.save('project_overview.pptx')
print("Presentation created successfully!")
```
