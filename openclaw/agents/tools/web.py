"""Web tools - search and fetch"""

import logging
from typing import Any

import httpx

from .base import AgentTool, ToolResult

logger = logging.getLogger(__name__)


class WebFetchTool(AgentTool):
    """Fetch web page contents"""

    def __init__(self):
        super().__init__()
        self.name = "web_fetch"
        self.description = "Fetch content from a URL"

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "URL to fetch"}},
            "required": ["url"],
        }

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """Fetch URL"""
        url = params.get("url", "")

        if not url:
            return ToolResult(success=False, content="", error="No URL provided")

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()

                content_type = response.headers.get("content-type", "")

                if "text" in content_type or "html" in content_type:
                    # Return text content
                    return ToolResult(
                        success=True,
                        content=response.text,
                        metadata={
                            "status_code": response.status_code,
                            "content_type": content_type,
                            "url": str(response.url),
                        },
                    )
                else:
                    # Non-text content
                    return ToolResult(
                        success=True,
                        content=f"Fetched {len(response.content)} bytes of {content_type}",
                        metadata={
                            "status_code": response.status_code,
                            "content_type": content_type,
                            "size": len(response.content),
                        },
                    )

        except httpx.HTTPStatusError as e:
            return ToolResult(
                success=False, content="", error=f"HTTP {e.response.status_code}: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Web fetch error: {e}", exc_info=True)
            return ToolResult(success=False, content="", error=str(e))


class WebSearchTool(AgentTool):
    """Search the web using DuckDuckGo"""

    def __init__(self):
        super().__init__()
        self.name = "web_search"
        self.description = "Search the web for information using DuckDuckGo"

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """Search web using DuckDuckGo"""
        query = params.get("query", "")
        num_results = params.get("num_results", 5)

        if not query:
            return ToolResult(success=False, content="", error="No query provided")

        try:
            from duckduckgo_search import DDGS

            # Perform search
            with DDGS() as ddgs:
                search_results = list(ddgs.text(query, max_results=num_results))

            # Format results
            if search_results:
                formatted = []
                for i, result in enumerate(search_results, 1):
                    formatted.append(
                        f"{i}. **{result.get('title', 'No title')}**\n"
                        f"   URL: {result.get('href', 'No URL')}\n"
                        f"   {result.get('body', 'No description')}\n"
                    )

                content = "\n".join(formatted)
                return ToolResult(
                    success=True,
                    content=content,
                    metadata={"count": len(search_results), "query": query},
                )
            else:
                return ToolResult(
                    success=True, content="No results found", metadata={"count": 0, "query": query}
                )

        except ImportError:
            return ToolResult(
                success=False,
                content="",
                error="duckduckgo-search not installed. Install with: pip install duckduckgo-search",
            )
        except Exception as e:
            logger.error(f"Web search error: {e}", exc_info=True)
            return ToolResult(success=False, content="", error=str(e))
