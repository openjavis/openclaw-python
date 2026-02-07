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
        # Description aligned with TypeScript version (Brave Search equivalent)
        self.description = "Search the web for information using DuckDuckGo. Returns titles, URLs, and snippets for fast research. Use this for finding articles, websites, news, and general information on the internet."

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query for finding information on the web"},
                "count": {
                    "type": "integer",
                    "description": "Number of results to return (default: 5, max: 10)",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 10,
                },
            },
            "required": ["query"],
        }

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """Search web using DuckDuckGo
        
        Returns results in format aligned with TypeScript version's Brave Search output:
        - title: Page title
        - url: Page URL
        - description: Page snippet
        """
        query = params.get("query", "")
        # Support both 'count' (TypeScript style) and 'num_results' (legacy)
        count = params.get("count") or params.get("num_results", 5)
        # Enforce max of 10 like TypeScript version
        count = min(int(count), 10)

        if not query:
            return ToolResult(success=False, content="", error="No query provided")

        try:
            from ddgs import DDGS

            # Perform search
            with DDGS() as ddgs:
                search_results = list(ddgs.text(query, max_results=count))

            # Format results - aligned with TypeScript Brave Search format
            if search_results:
                formatted = []
                for i, result in enumerate(search_results, 1):
                    title = result.get('title', 'No title')
                    url = result.get('href', '')
                    description = result.get('body', 'No description')
                    
                    formatted.append(
                        f"{i}. **{title}**\n"
                        f"   URL: {url}\n"
                        f"   {description}\n"
                    )

                content = "\n".join(formatted)
                return ToolResult(
                    success=True,
                    content=content,
                    metadata={
                        "query": query,
                        "provider": "duckduckgo",
                        "count": len(search_results),
                        "results": [
                            {
                                "title": r.get('title', ''),
                                "url": r.get('href', ''),
                                "description": r.get('body', ''),
                            }
                            for r in search_results
                        ],
                    },
                )
            else:
                return ToolResult(
                    success=True,
                    content="No results found for this query.",
                    metadata={"query": query, "provider": "duckduckgo", "count": 0},
                )

        except ImportError:
            return ToolResult(
                success=False,
                content="",
                error="ddgs not installed. Install with: pip install ddgs",
            )
        except Exception as e:
            logger.error(f"Web search error: {e}", exc_info=True)
            return ToolResult(success=False, content="", error=str(e))
