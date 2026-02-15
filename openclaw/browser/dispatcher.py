"""
Route dispatcher for browser HTTP routes.

Provides regex-based routing for browser control endpoints.
"""
from __future__ import annotations

import re
import logging
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


class BrowserRouteDispatcher:
    """
    Regex-based route dispatcher for browser endpoints.
    
    Supports:
    - GET /path
    - POST /path
    - DELETE /path
    - Path parameters: /tabs/:targetId
    """
    
    def __init__(self):
        self.routes: dict[str, dict[str, tuple[Callable, list[str]]]] = {
            "GET": {},
            "POST": {},
            "DELETE": {},
            "PUT": {}
        }
    
    def get(self, path: str):
        """Register GET route"""
        def decorator(handler: Callable):
            pattern, params = self.compile_route(path)
            self.routes["GET"][path] = (handler, pattern, params)
            return handler
        return decorator
    
    def post(self, path: str):
        """Register POST route"""
        def decorator(handler: Callable):
            pattern, params = self.compile_route(path)
            self.routes["POST"][path] = (handler, pattern, params)
            return handler
        return decorator
    
    def delete(self, path: str):
        """Register DELETE route"""
        def decorator(handler: Callable):
            pattern, params = self.compile_route(path)
            self.routes["DELETE"][path] = (handler, pattern, params)
            return handler
        return decorator
    
    def put(self, path: str):
        """Register PUT route"""
        def decorator(handler: Callable):
            pattern, params = self.compile_route(path)
            self.routes["PUT"][path] = (handler, pattern, params)
            return handler
        return decorator
    
    def compile_route(self, path: str) -> tuple[re.Pattern, list[str]]:
        """
        Compile route path to regex pattern.
        
        Converts /tabs/:targetId to regex and extracts param names.
        
        Args:
            path: Route path with :param syntax
            
        Returns:
            Tuple of (pattern, param_names)
        """
        param_names = []
        
        # Find all :param patterns
        pattern_str = path
        for match in re.finditer(r':(\w+)', path):
            param_name = match.group(1)
            param_names.append(param_name)
            # Replace :param with regex capture group
            pattern_str = pattern_str.replace(f':{param_name}', r'([^/]+)')
        
        # Compile regex
        pattern = re.compile(f'^{pattern_str}$')
        
        return pattern, param_names
    
    async def dispatch(
        self,
        method: str,
        path: str,
        query: dict,
        body: dict,
        context: Any = None
    ) -> Any:
        """
        Dispatch request to matching route handler.
        
        Args:
            method: HTTP method
            path: Request path
            query: Query parameters
            body: Request body
            context: Request context
            
        Returns:
            Handler response
        """
        routes = self.routes.get(method, {})
        
        # Try to match path
        for route_path, (handler, pattern, param_names) in routes.items():
            match = pattern.match(path)
            if match:
                # Extract path parameters
                params = dict(zip(param_names, match.groups()))
                
                # Call handler
                try:
                    return await handler(
                        params=params,
                        query=query,
                        body=body,
                        context=context
                    )
                except Exception as e:
                    logger.error(f"Error in handler for {method} {path}: {e}", exc_info=True)
                    return {"error": str(e)}
        
        # No route matched
        return {"error": "Not found", "path": path, "method": method}


__all__ = [
    "BrowserRouteDispatcher",
]
