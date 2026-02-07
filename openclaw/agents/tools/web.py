"""Web tools - search and fetch"""

import logging
import random
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
        # NEW: Support both "parameters" and "args_schema" for compatibility with different LLMs
        self.parameters = {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "URL to fetch"}},
            "required": ["url"],
        }

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "URL to fetch"}},
            "required": ["url"],
        }

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """Fetch URL"""
        url = params.get("url", "")
        # We need a headers to avoid being blocked by some sites, and to mimic a real browser
        ua_list = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]

        headers = {
            "User-Agent": random.choice(ua_list),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "DNT": "1",  # Do Not Track
            "Connection": "keep-alive",
        }

        # proxy support if needed, e.g., for environments with restricted internet access

        if not url:
            return ToolResult(success=False, content="No URL provided", error="No URL provided")

        try:
            async with httpx.AsyncClient(
                headers=headers, timeout=30.0, follow_redirects=True
            ) as client:
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
            return ToolResult(success=False, content=f"Error fetching URL: {str(e)}", error=str(e))


class WebSearchTool(AgentTool):
    """Search the web using DuckDuckGo"""

    def __init__(self):
        super().__init__()
        self.name = "web_search"
        self.description = "Search the web for information using DuckDuckGo"
        # NEW: Support both "parameters" and "args_schema" for compatibility with different LLMs
        self.parameters = {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "num_results": {
                    "type": "integer",
                    "description": "Number of results",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for finding information on the web",
                },
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
            return ToolResult(success=False, content="No query provided", error="No query provided")

        try:
            from ddgs import DDGS

            # Perform search
            with DDGS() as ddgs:
                search_results = list(
                    ddgs.text(query, region="wt-wt", safesearch="moderate", max_results=num_results)
                )

            # Format results - aligned with TypeScript Brave Search format
            if search_results:
                formatted = []
                for i, result in enumerate(search_results, 1):
                    title = result.get("title", "No title")
                    url = result.get("href", "")
                    description = result.get("body", "No description")

                    formatted.append(f"{i}. **{title}**\n" f"   URL: {url}\n" f"   {description}\n")

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
                                "title": r.get("title", ""),
                                "url": r.get("href", ""),
                                "description": r.get("body", ""),
                            }
                            for r in search_results
                        ],
                    },
                )
            else:
                return ToolResult(
                    success=True,
                    content="No results found. Attempting fallback...",
                    metadata={"count": 0, "query": query},
                )

        except ImportError:
            return ToolResult(
                success=False,
                content="Web search error: duckduckgo-search not installed. Install with: pip install duckduckgo-search",
                error="duckduckgo-search not installed. Install with: pip install duckduckgo-search",
            )
        except Exception as e:
            logger.error(f"Web search error: {e}", exc_info=True)
            error_msg = f"Web search failed: {str(e)}. Please try another search term or method."
            return ToolResult(success=False, content=error_msg, error=str(e))
