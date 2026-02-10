"""HTTP server for control UI - matches TypeScript implementation"""

import logging
from pathlib import Path
from typing import Optional
import mimetypes

from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse

logger = logging.getLogger(__name__)


class ControlUIServer:
    """HTTP server for serving control UI static files"""
    
    def __init__(self, gateway, base_path: str = "/", ui_port: int = 8080):
        self.gateway = gateway
        self.base_path = base_path.rstrip("/")
        self.ui_port = ui_port
        self.ui_dir = Path(__file__).parent.parent / "web" / "static" / "control-ui"
        
        self.app = FastAPI(
            title="OpenClaw Control UI",
            docs_url=None,  # Disable FastAPI docs
            redoc_url=None
        )
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup HTTP routes"""
        
        # Health check endpoint
        @self.app.get(f"{self.base_path}/health")
        async def health_check():
            return JSONResponse({
                "status": "ok",
                "gateway": "running",
                "version": "0.6.0"
            })
        
        # Serve static assets if UI directory exists
        if self.ui_dir.exists():
            assets_dir = self.ui_dir / "assets"
            if assets_dir.exists():
                self.app.mount(
                    f"{self.base_path}/assets",
                    StaticFiles(directory=str(assets_dir)),
                    name="assets"
                )
                logger.info(f"Mounted static assets from {assets_dir}")
        
        # SPA fallback - serve index.html for all other routes
        @self.app.get("/{path:path}")
        async def serve_spa(path: str, request: Request):
            """Serve SPA with config injection"""
            
            # If UI directory doesn't exist, return helpful message
            if not self.ui_dir.exists():
                return HTMLResponse(
                    content=self._get_placeholder_html(),
                    status_code=200
                )
            
            # Check if requesting a specific file
            file_path = self.ui_dir / path
            if file_path.is_file() and path not in ["", "index.html"]:
                # Serve the specific file
                return FileResponse(file_path)
            
            # Serve index.html with injected config
            index_path = self.ui_dir / "index.html"
            if not index_path.exists():
                return HTMLResponse(
                    content=self._get_placeholder_html(),
                    status_code=200
                )
            
            try:
                html = index_path.read_text()
                
                # Inject config
                config_script = self._get_config_script()
                html = html.replace("</head>", f"{config_script}</head>")
                
                return HTMLResponse(content=html)
            
            except Exception as e:
                logger.error(f"Error serving index.html: {e}", exc_info=True)
                return HTMLResponse(
                    content=f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>",
                    status_code=500
                )
    
    def _get_config_script(self) -> str:
        """Generate config injection script"""
        # Get assistant name from config
        assistant_name = "OpenClaw"
        try:
            if self.gateway.config and self.gateway.config.agents:
                if self.gateway.config.agents.defaults:
                    assistant_name = getattr(
                        self.gateway.config.agents.defaults, 
                        "name", 
                        "OpenClaw"
                    )
        except Exception:
            pass
        
        return f"""
        <script>
            window.__OPENCLAW_CONFIG__ = {{
                basePath: "{self.base_path}",
                assistantName: "{assistant_name}",
                wsUrl: "ws://127.0.0.1:{self.gateway.config.gateway.port}",
                httpUrl: "http://127.0.0.1:{self.ui_port}",
                version: "0.6.0"
            }};
        </script>
        """
    
    def _get_placeholder_html(self) -> str:
        """Get placeholder HTML when UI is not built"""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenClaw Control UI</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
        }
        .container {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            max-width: 600px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        h1 {
            font-size: 2.5em;
            margin: 0 0 20px 0;
        }
        .logo {
            font-size: 4em;
            margin-bottom: 20px;
        }
        p {
            font-size: 1.1em;
            line-height: 1.6;
            opacity: 0.9;
        }
        .code {
            background: rgba(0, 0, 0, 0.3);
            padding: 15px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            margin: 20px 0;
            font-size: 0.9em;
        }
        .status {
            margin-top: 30px;
            padding: 15px;
            background: rgba(0, 255, 0, 0.1);
            border-radius: 8px;
            border-left: 4px solid #4ade80;
        }
        .command {
            background: rgba(0, 0, 0, 0.4);
            padding: 10px 15px;
            border-radius: 6px;
            margin: 10px 0;
            font-family: monospace;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">🦞</div>
        <h1>OpenClaw Control UI</h1>
        <p>The control UI is not yet built. The TypeScript frontend needs to be compiled.</p>
        
        <div class="status">
            <strong>✅ Gateway is running</strong><br>
            WebSocket server is active and ready for connections.
        </div>
        
        <h3>To build the control UI:</h3>
        <div class="code">
            <div class="command">cd openclaw/ui</div>
            <div class="command">pnpm install</div>
            <div class="command">pnpm build</div>
            <div class="command">cp -r ../dist/control-ui openclaw-python/openclaw/web/static/</div>
        </div>
        
        <p>After building, restart the gateway to serve the full control UI.</p>
        
        <h3>Meanwhile, you can:</h3>
        <ul>
            <li>Use the CLI: <code>openclaw --help</code></li>
            <li>Connect via WebSocket to port {gateway_port}</li>
            <li>Configure channels: <code>openclaw channels list</code></li>
        </ul>
    </div>
</body>
</html>
        """.replace("{gateway_port}", str(self.gateway.config.gateway.port))
