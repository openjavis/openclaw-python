---
name: canvas
description: "Present web content in OpenClaw canvas UI"
user-invocable: true
metadata:
  openclaw:
    emoji: "🎨"
    skillKey: "canvas"
    requires:
      config: ["canvas.enabled"]
---

# Canvas Presentation Skill

Present interactive web content in the OpenClaw canvas UI. The canvas provides a live-reload web view for displaying HTML/CSS/JS content.

## Tool: `canvas`

The canvas tool provides operations for presenting and controlling web content.

### Operations

#### `present`

Present HTML content in the canvas.

```javascript
{
  "operation": "present",
  "html": "<html>...</html>",
  "css": "body { ... }",
  "js": "console.log('...');"
}
```

- `html`: HTML content (required)
- `css`: CSS styles (optional)
- `js`: JavaScript code (optional)

#### `navigate`

Navigate the canvas to a URL.

```javascript
{
  "operation": "navigate",
  "url": "https://example.com"
}
```

#### `snapshot`

Get a snapshot of the current canvas state.

```javascript
{
  "operation": "snapshot"
}
```

Returns information about the current page, including:
- URL
- Title
- Viewport size

#### `hide`

Hide the canvas.

```javascript
{
  "operation": "hide"
}
```

#### `eval`

Execute JavaScript in the canvas context.

```javascript
{
  "operation": "eval",
  "js": "document.querySelector('h1').textContent"
}
```

Returns the result of the JavaScript expression.

## Best Practices

### HTML Structure

Always include a complete HTML structure:

```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Page Title</title>
</head>
<body>
  <!-- Content here -->
</body>
</html>
```

### Styling

- Use inline `<style>` tags or the `css` parameter
- Consider responsive design (mobile, tablet, desktop)
- Use modern CSS features (flexbox, grid)

### JavaScript

- Use modern ES6+ syntax
- Add event listeners for interactivity
- Consider using web APIs (localStorage, fetch, etc.)

### Live Reload

The canvas supports live reload:
- Files in `~/.openclaw/canvas/` are watched
- Changes automatically refresh the canvas
- Great for iterative development

## Examples

### Simple Page

```javascript
{
  "operation": "present",
  "html": "<!DOCTYPE html><html><head><meta charset='UTF-8'><title>Hello</title></head><body><h1>Hello, World!</h1></body></html>",
  "css": "body { font-family: sans-serif; text-align: center; padding: 2rem; }"
}
```

### Interactive Dashboard

```javascript
{
  "operation": "present",
  "html": "<!DOCTYPE html><html>...</html>",
  "js": "setInterval(() => { updateMetrics(); }, 1000);"
}
```

### Navigation

```javascript
{
  "operation": "navigate",
  "url": "https://github.com/user/repo"
}
```

## Tips

- Canvas is ideal for visualizations, dashboards, and interactive UIs
- Use `present` for custom HTML/CSS/JS
- Use `navigate` for existing web pages
- Use `eval` for querying page state
- Files in `~/.openclaw/canvas/` can be referenced and will live-reload
