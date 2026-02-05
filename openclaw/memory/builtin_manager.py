"""Built-in memory manager using SQLite + Vector + FTS."""
import hashlib
import logging
import sqlite3
from pathlib import Path
from typing import Optional

from .types import MemorySearchResult, MemorySource

logger = logging.getLogger(__name__)


class BuiltinMemoryManager:
    """Manages agent memory with vector and full-text search."""
    
    def __init__(
        self,
        agent_id: str,
        workspace_dir: Path,
        embedding_provider: Optional[str] = None
    ):
        self.agent_id = agent_id
        self.workspace_dir = workspace_dir
        self.embedding_provider = embedding_provider or "openai"
        
        # Set up database path
        memory_dir = workspace_dir / ".openclaw" / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = memory_dir / f"{agent_id}_index.db"
        self.db: Optional[sqlite3.Connection] = None
        
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize database with schema."""
        self.db = sqlite3.connect(str(self.db_path))
        self.db.row_factory = sqlite3.Row
        
        # Create schema
        self.db.executescript("""
            -- Files table
            CREATE TABLE IF NOT EXISTS files (
                path TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                hash TEXT NOT NULL,
                mtime INTEGER NOT NULL,
                size INTEGER NOT NULL,
                indexed_at INTEGER NOT NULL
            );
            
            -- Chunks table
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                path TEXT NOT NULL,
                source TEXT NOT NULL,
                start_line INTEGER NOT NULL,
                end_line INTEGER NOT NULL,
                hash TEXT NOT NULL,
                model TEXT NOT NULL,
                text TEXT NOT NULL,
                embedding BLOB,
                updated_at INTEGER NOT NULL,
                FOREIGN KEY (path) REFERENCES files(path)
            );
            
            CREATE INDEX IF NOT EXISTS idx_chunks_path ON chunks(path);
            CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source);
            
            -- FTS5 virtual table for full-text search
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                id UNINDEXED,
                path,
                text,
                content='chunks',
                content_rowid='rowid'
            );
            
            -- FTS triggers
            CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
                INSERT INTO chunks_fts(rowid, id, path, text)
                VALUES (new.rowid, new.id, new.path, new.text);
            END;
            
            CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
                DELETE FROM chunks_fts WHERE rowid = old.rowid;
            END;
            
            CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
                DELETE FROM chunks_fts WHERE rowid = old.rowid;
                INSERT INTO chunks_fts(rowid, id, path, text)
                VALUES (new.rowid, new.id, new.path, new.text);
            END;
        """)
        
        self.db.commit()
        logger.info(f"Initialized memory database at {self.db_path}")
    
    async def search(
        self,
        query: str,
        limit: int = 5,
        sources: Optional[list[MemorySource]] = None,
        use_vector: bool = False
    ) -> list[MemorySearchResult]:
        """
        Search memory using full-text search (and optionally vector search).
        
        Args:
            query: Search query
            limit: Maximum number of results
            sources: Filter by memory sources
            use_vector: Use vector search (requires embeddings)
            
        Returns:
            List of search results
        """
        if not self.db:
            return []
        
        # For now, implement FTS only (vector search requires embedding generation)
        return await self._fts_search(query, limit, sources)
    
    async def _fts_search(
        self,
        query: str,
        limit: int,
        sources: Optional[list[MemorySource]]
    ) -> list[MemorySearchResult]:
        """Full-text search using FTS5."""
        try:
            # Build source filter
            source_filter = ""
            source_values = []
            if sources:
                source_names = [s.value for s in sources]
                placeholders = ','.join('?' * len(source_names))
                source_filter = f"AND chunks.source IN ({placeholders})"
                source_values = source_names
            
            # FTS5 query
            sql = f"""
                SELECT 
                    chunks.id,
                    chunks.path,
                    chunks.source,
                    chunks.text,
                    chunks.start_line,
                    chunks.end_line,
                    bm25(chunks_fts) as score
                FROM chunks_fts
                JOIN chunks ON chunks.rowid = chunks_fts.rowid
                WHERE chunks_fts MATCH ?
                {source_filter}
                ORDER BY score
                LIMIT ?
            """
            
            cursor = self.db.execute(
                sql,
                [query] + source_values + [limit]
            )
            
            results = []
            for row in cursor.fetchall():
                # Create snippet (first 200 chars)
                snippet = row['text'][:200] + ('...' if len(row['text']) > 200 else '')
                
                results.append(MemorySearchResult(
                    id=row['id'],
                    path=row['path'],
                    source=MemorySource(row['source']),
                    text=row['text'],
                    snippet=snippet,
                    start_line=row['start_line'],
                    end_line=row['end_line'],
                    score=abs(row['score'])  # BM25 scores are negative
                ))
            
            return results
            
        except Exception as e:
            logger.error(f"FTS search error: {e}", exc_info=True)
            return []
    
    async def add_file(
        self,
        file_path: Path,
        source: MemorySource = MemorySource.MEMORY
    ) -> int:
        """
        Add a file to memory index.
        
        Args:
            file_path: Path to file
            source: Memory source type
            
        Returns:
            Number of chunks created
        """
        if not self.db:
            return 0
        
        try:
            # Read file content
            content = file_path.read_text(encoding='utf-8')
            file_hash = self._hash_content(content)
            
            # Check if file already indexed
            existing = self.db.execute(
                'SELECT hash FROM files WHERE path = ?',
                [str(file_path)]
            ).fetchone()
            
            if existing and existing['hash'] == file_hash:
                logger.debug(f"File unchanged: {file_path}")
                return 0
            
            # Chunk the file
            chunks = self._chunk_text(content, str(file_path))
            
            # Delete old chunks
            self.db.execute('DELETE FROM chunks WHERE path = ?', [str(file_path)])
            
            # Insert chunks
            import time
            now = int(time.time())
            
            for chunk in chunks:
                chunk_id = f"{file_path}:{chunk['start_line']}-{chunk['end_line']}"
                
                self.db.execute("""
                    INSERT INTO chunks 
                    (id, path, source, start_line, end_line, hash, model, text, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    chunk_id,
                    str(file_path),
                    source.value,
                    chunk['start_line'],
                    chunk['end_line'],
                    self._hash_content(chunk['text']),
                    self.embedding_provider,
                    chunk['text'],
                    now
                ])
            
            # Update files table
            stat = file_path.stat()
            self.db.execute("""
                INSERT OR REPLACE INTO files 
                (path, source, hash, mtime, size, indexed_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [
                str(file_path),
                source.value,
                file_hash,
                int(stat.st_mtime),
                stat.st_size,
                now
            ])
            
            self.db.commit()
            logger.info(f"Indexed {len(chunks)} chunks from {file_path}")
            return len(chunks)
            
        except Exception as e:
            logger.error(f"Error adding file {file_path}: {e}", exc_info=True)
            return 0
    
    def _chunk_text(
        self,
        content: str,
        path: str,
        chunk_size: int = 500
    ) -> list[dict]:
        """
        Chunk text into smaller pieces.
        
        Args:
            content: File content
            path: File path
            chunk_size: Target chunk size in lines
            
        Returns:
            List of chunk dicts
        """
        lines = content.split('\n')
        chunks = []
        
        # Simple chunking by line count
        for i in range(0, len(lines), chunk_size):
            chunk_lines = lines[i:i + chunk_size]
            chunk_text = '\n'.join(chunk_lines)
            
            chunks.append({
                'text': chunk_text,
                'start_line': i + 1,
                'end_line': min(i + chunk_size, len(lines))
            })
        
        return chunks
    
    def _hash_content(self, content: str) -> str:
        """Hash content for change detection."""
        return hashlib.sha256(content.encode()).hexdigest()
    
    async def sync(self) -> dict:
        """
        Sync memory index with filesystem.
        
        Returns:
            Sync statistics
        """
        stats = {
            'files_added': 0,
            'files_updated': 0,
            'files_removed': 0,
            'chunks_created': 0
        }
        
        # TODO: Implement full sync logic
        # - Scan memory directories
        # - Add/update changed files
        # - Remove deleted files
        
        return stats
    
    def close(self) -> None:
        """Close database connection."""
        if self.db:
            self.db.close()
            self.db = None
