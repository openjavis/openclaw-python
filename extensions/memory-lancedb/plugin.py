"""LanceDB memory plugin"""

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MemorySearchTool:
    """Memory search tool using LanceDB"""

    def __init__(self, db_path: Path | None = None):
        self.name = "memory_search"
        self.description = "Search through conversation memory using semantic search"

        if db_path is None:
            db_path = Path.home() / ".openclaw" / "memory"

        self.db_path = db_path
        self.db_path.mkdir(parents=True, exist_ok=True)
        self._db = None
        self._table = None
        self._encoder = None

    def _init_db(self):
        """Initialize database and encoder"""
        if self._db is not None:
            return

        try:
            import lancedb
            from sentence_transformers import SentenceTransformer

            # Connect to LanceDB
            self._db = lancedb.connect(str(self.db_path))

            # Load embedding model
            self._encoder = SentenceTransformer("all-MiniLM-L6-v2")

            # Check if table exists
            table_name = "memory"
            if table_name not in self._db.table_names():
                # Create empty table with schema
                import pyarrow as pa

                schema = pa.schema(
                    [
                        pa.field("text", pa.string()),
                        pa.field("vector", pa.list_(pa.float32(), 384)),
                        pa.field("timestamp", pa.string()),
                        pa.field("session_id", pa.string()),
                        pa.field("metadata", pa.string()),
                    ]
                )
                self._table = self._db.create_table(table_name, schema=schema, mode="create")
            else:
                self._table = self._db.open_table(table_name)

            logger.info("LanceDB memory initialized")

        except ImportError as e:
            logger.error(f"Missing dependencies: {e}")
            logger.error("Install with: pip install lancedb sentence-transformers pyarrow")
            raise

    def get_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results",
                    "default": 5,
                },
                "session_id": {"type": "string", "description": "Filter by session ID (optional)"},
            },
            "required": ["query"],
        }

    async def execute(self, params: dict[str, Any]) -> dict[str, Any]:
        """Search memory"""
        query = params.get("query", "")
        limit = params.get("limit", 5)
        session_filter = params.get("session_id")

        if not query:
            return {"success": False, "content": "", "error": "No query provided"}

        try:
            # Initialize DB if needed
            self._init_db()

            # Check if table has data
            if self._table.count_rows() == 0:
                return {
                    "success": True,
                    "content": "Memory is empty. No entries to search.",
                    "metadata": {"count": 0},
                }

            # Generate query embedding
            query_embedding = self._encoder.encode(query).tolist()

            # Search
            results = self._table.search(query_embedding).limit(limit)

            # Apply session filter if provided
            if session_filter:
                results = results.where(f"session_id = '{session_filter}'")

            results_list = results.to_list()

            if not results_list:
                return {
                    "success": True,
                    "content": "No matching memories found.",
                    "metadata": {"count": 0},
                }

            # Format results
            formatted = []
            for i, result in enumerate(results_list, 1):
                formatted.append(
                    f"{i}. **{result.get('session_id', 'unknown')}** "
                    f"({result.get('timestamp', 'no time')}):\n"
                    f"   {result.get('text', 'No content')}\n"
                )

            content = "Memory search results:\n\n" + "\n".join(formatted)

            return {
                "success": True,
                "content": content,
                "metadata": {"count": len(results_list), "query": query},
            }

        except ImportError:
            return {
                "success": False,
                "content": "",
                "error": "LanceDB not installed. Install with: pip install lancedb sentence-transformers pyarrow",
            }
        except Exception as e:
            logger.error(f"Memory search error: {e}", exc_info=True)
            return {"success": False, "content": "", "error": str(e)}

    async def add_memory(
        self, text: str, session_id: str, timestamp: str, metadata: dict | None = None
    ) -> bool:
        """Add entry to memory"""
        try:
            self._init_db()

            # Generate embedding
            vector = self._encoder.encode(text).tolist()

            # Add to database
            import json

            self._table.add(
                [
                    {
                        "text": text,
                        "vector": vector,
                        "timestamp": timestamp,
                        "session_id": session_id,
                        "metadata": json.dumps(metadata or {}),
                    }
                ]
            )

            return True

        except Exception as e:
            logger.error(f"Add memory error: {e}", exc_info=True)
            return False


def register(api):
    """Register memory search tool"""
    from openclaw.agents.tools.registry import get_tool_registry

    memory_tool = MemorySearchTool()
    registry = get_tool_registry()
    registry.register(memory_tool)

    logger.info("Registered LanceDB memory tool")
