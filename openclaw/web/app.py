"""Web UI FastAPI application"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..agents.runtime import AgentRuntime
from ..agents.session import SessionManager
from ..agents.tools.registry import get_tool_registry
from ..channels.registry import get_channel_registry
from ..config import load_config

logger = logging.getLogger(__name__)

app = FastAPI(title="ClawdBot Control Panel")

# Setup templates and static files
templates_dir = Path(__file__).parent / "templates"
static_dir = Path(__file__).parent / "static"

templates = Jinja2Templates(directory=str(templates_dir))

if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Control panel home page"""
    config = load_config()
    channel_registry = get_channel_registry()

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "config": config, "channels": channel_registry.list_channels()},
    )


@app.get("/webchat", response_class=HTMLResponse)
async def webchat(request: Request):
    """WebChat interface"""
    return templates.TemplateResponse("webchat.html", {"request": request})


@app.get("/api/status")
async def api_status():
    """Get system status"""
    config = load_config()
    channel_registry = get_channel_registry()

    return {
        "status": "ok",
        "gateway": {"port": config.gateway.port, "bind": config.gateway.bind},
        "channels": [
            {"id": ch.id, "label": ch.label, "running": ch.is_running()}
            for ch in channel_registry.list_channels()
        ],
    }


@app.get("/api/sessions")
async def api_sessions():
    """List sessions"""
    session_manager = SessionManager()
    session_ids = session_manager.list_sessions()

    return {
        "sessions": [
            {"id": sid, "messageCount": 0} for sid in session_ids  # TODO: Get actual message count
        ]
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            # Handle different message types
            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif data.get("type") == "chat":
                # TODO: Handle chat message
                await websocket.send_json(
                    {"type": "chat_response", "text": "Echo: " + data.get("text", "")}
                )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)


# OpenAI-compatible Chat Completions API
@app.post("/v1/chat/completions")
async def chat_completions(request: dict[str, Any]):
    """OpenAI-compatible Chat Completions API endpoint"""
    import json

    from fastapi.responses import StreamingResponse

    messages = request.get("messages", [])
    model = request.get("model", "claude-opus-4-5-20250514")
    stream = request.get("stream", False)
    max_tokens = request.get("max_tokens", 4096)

    if not messages:
        return {"error": {"message": "messages required", "type": "invalid_request_error"}}

    try:
        load_config()
        runtime = AgentRuntime(model=model)
        session_manager = SessionManager()

        # Create temporary session
        session = session_manager.get_session(f"api-{datetime.now().timestamp()}")

        # Add messages to session
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                session.add_user_message(content)
            elif role == "assistant":
                session.add_assistant_message(content)

        # Get last user message
        last_message = messages[-1].get("content", "") if messages else ""

        if stream:
            # Streaming response
            async def generate():
                accumulated = ""
                async for event in runtime.run_turn(session, last_message, [], max_tokens):
                    if event.type == "assistant":
                        delta = event.data.get("delta", {})
                        text = delta.get("text", "")
                        if text:
                            accumulated += text
                            chunk = {
                                "id": f"chatcmpl-{int(datetime.now().timestamp())}",
                                "object": "chat.completion.chunk",
                                "created": int(datetime.now().timestamp()),
                                "model": model,
                                "choices": [
                                    {"index": 0, "delta": {"content": text}, "finish_reason": None}
                                ],
                            }
                            yield f"data: {json.dumps(chunk)}\n\n"

                # Final chunk
                final_chunk = {
                    "id": f"chatcmpl-{int(datetime.now().timestamp())}",
                    "object": "chat.completion.chunk",
                    "created": int(datetime.now().timestamp()),
                    "model": model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                }
                yield f"data: {json.dumps(final_chunk)}\n\n"
                yield "data: [DONE]\n\n"

            return StreamingResponse(generate(), media_type="text/event-stream")
        else:
            # Non-streaming response
            accumulated = ""
            async for event in runtime.run_turn(session, last_message, [], max_tokens):
                if event.type == "assistant":
                    delta = event.data.get("delta", {})
                    text = delta.get("text", "")
                    accumulated += text

            return {
                "id": f"chatcmpl-{int(datetime.now().timestamp())}",
                "object": "chat.completion",
                "created": int(datetime.now().timestamp()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": accumulated},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            }

    except Exception as e:
        logger.error(f"Chat completions error: {e}", exc_info=True)
        return {"error": {"message": str(e), "type": "server_error"}}


# Tool invocation API
@app.post("/tools/invoke")
async def tools_invoke(request: dict[str, Any]):
    """Direct tool invocation endpoint"""
    tool_name = request.get("tool")
    params = request.get("params", {})

    if not tool_name:
        return {"success": False, "error": "tool name required"}

    try:
        tool_registry = get_tool_registry()
        tool = tool_registry.get(tool_name)

        if not tool:
            return {"success": False, "error": f"Tool '{tool_name}' not found"}

        result = await tool.execute(params)

        return {
            "success": result.success,
            "content": result.content,
            "error": result.error,
            "metadata": result.metadata,
        }

    except Exception as e:
        logger.error(f"Tool invocation error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# Models list endpoint
@app.get("/api/models")
async def api_models():
    """List available models"""
    return {
        "models": [
            {
                "id": "anthropic/claude-opus-4-5-20250514",
                "name": "Claude Opus 4.5",
                "provider": "anthropic",
            },
            {
                "id": "anthropic/claude-3-5-sonnet-20241022",
                "name": "Claude 3.5 Sonnet",
                "provider": "anthropic",
            },
            {"id": "openai/gpt-4", "name": "GPT-4", "provider": "openai"},
            {"id": "openai/gpt-4-turbo", "name": "GPT-4 Turbo", "provider": "openai"},
        ]
    }


# Tools list endpoint
@app.get("/api/tools")
async def api_tools():
    """List available tools"""
    tool_registry = get_tool_registry()
    tools = tool_registry.list_tools()

    return {
        "tools": [
            {"name": tool.name, "description": tool.description, "schema": tool.get_schema()}
            for tool in tools
        ]
    }


def create_web_app() -> FastAPI:
    """Create and configure the web application"""
    return app
