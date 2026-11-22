import os
import json
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from contextlib import contextmanager

from backend.config.settings import DB_PATH, get_db_path
from backend.processing.chunker import DocumentChunk

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Persistent SQLite storage manager for LENS.
    Deterministic connection management ensuring no file locks are leaked.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or get_db_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(str(self.db_path), timeout=20.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 20000")
        try:
            yield conn
        finally:
            conn.close()

    def init_db(self):
        """Create tables and indexes if they do not exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Files table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                file_name TEXT NOT NULL,
                extension TEXT NOT NULL,
                category TEXT NOT NULL,
                file_size_bytes INTEGER NOT NULL,
                modified_at TEXT NOT NULL,
                indexed_at TEXT NOT NULL,
                content_hash TEXT,
                status TEXT NOT NULL DEFAULT 'indexed',
                error_message TEXT
            )
            """)

            # Chunks table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
                unit_type TEXT NOT NULL,
                unit_number INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                chunk_text TEXT NOT NULL,
                source_info TEXT,
                embedding_id INTEGER UNIQUE,
                metadata_json TEXT,
                created_at TEXT NOT NULL
            )
            """)

            # Indexing runs history
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS indexing_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                total_files INTEGER DEFAULT 0,
                indexed_files INTEGER DEFAULT 0,
                failed_files INTEGER DEFAULT 0,
                status TEXT NOT NULL,
                message TEXT
            )
            """)

            # Indexes for high performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_path ON files(file_path)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_category ON files(category)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_file_id ON chunks(file_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_embedding_id ON chunks(embedding_id)")

            conn.commit()

    def upsert_file(
        self,
        file_path: str,
        file_name: str,
        extension: str,
        category: str,
        file_size_bytes: int,
        modified_at: str,
        content_hash: Optional[str] = None,
        status: str = "indexed",
        error_message: Optional[str] = None
    ) -> int:
        """Insert or update a file record. Returns file_id."""
        now = datetime.now().astimezone().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO files (
                file_path, file_name, extension, category,
                file_size_bytes, modified_at, indexed_at,
                content_hash, status, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(file_path) DO UPDATE SET
                file_name = excluded.file_name,
                extension = excluded.extension,
                category = excluded.category,
                file_size_bytes = excluded.file_size_bytes,
                modified_at = excluded.modified_at,
                indexed_at = excluded.indexed_at,
                content_hash = excluded.content_hash,
                status = excluded.status,
                error_message = excluded.error_message
            """, (
                file_path, file_name, extension, category,
                file_size_bytes, modified_at, now,
                content_hash, status, error_message
            ))
            cursor.execute("SELECT id FROM files WHERE file_path = ?", (file_path,))
            row = cursor.fetchone()
            conn.commit()
            return row["id"]

    def prune_chunks_for_file(self, file_id: int) -> List[int]:
        """
        Delete old chunks for file_id and return their embedding_ids so vector store can prune them.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT embedding_id FROM chunks WHERE file_id = ? AND embedding_id IS NOT NULL", (file_id,))
            old_ids = [r["embedding_id"] for r in cursor.fetchall()]
            cursor.execute("DELETE FROM chunks WHERE file_id = ?", (file_id,))
            conn.commit()
            return old_ids

    def insert_chunks(self, chunks: List[DocumentChunk], file_id: int) -> List[int]:
        """
        Delete old chunks for file_id and insert new chunks.
        Returns the list of generated chunk IDs (which serve as FAISS embedding IDs).
        """
        now = datetime.now().astimezone().isoformat()
        chunk_ids = []

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM chunks WHERE file_id = ?", (file_id,))

            for chunk in chunks:
                cursor.execute("""
                INSERT INTO chunks (
                    file_id, unit_type, unit_number, chunk_index,
                    chunk_text, source_info, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    file_id, chunk.unit_type, chunk.unit_number, chunk.chunk_index,
                    chunk.chunk_text, chunk.source_info,
                    json.dumps(chunk.metadata), now
                ))
                c_id = cursor.lastrowid
                cursor.execute("UPDATE chunks SET embedding_id = ? WHERE id = ?", (c_id, c_id))
                chunk.chunk_id = c_id
                chunk_ids.append(c_id)

            conn.commit()

        return chunk_ids

    def record_indexing_run_start(self, total_files: int = 0) -> int:
        now = datetime.now().astimezone().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO indexing_runs (started_at, total_files, status, message)
            VALUES (?, ?, 'running', 'Indexing started')
            """, (now, total_files))
            run_id = cursor.lastrowid
            conn.commit()
            return run_id

    def record_indexing_run_finish(self, run_id: int, indexed: int, failed: int, status: str, message: str):
        now = datetime.now().astimezone().isoformat()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE indexing_runs
            SET finished_at = ?, indexed_files = ?, failed_files = ?, status = ?, message = ?
            WHERE id = ?
            """, (now, indexed, failed, status, message, run_id))
            conn.commit()

    def get_chunks_for_file(self, file_id: int) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM chunks WHERE file_id = ? ORDER BY unit_number, chunk_index", (file_id,))
            return [dict(r) for r in cursor.fetchall()]

    def get_file_by_id(self, file_id: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM files WHERE id = ?", (file_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_file_by_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM files WHERE file_path = ?", (file_path,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_indexed_files(self) -> Dict[str, Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM files")
            rows = cursor.fetchall()
            return {row["file_path"]: dict(row) for row in rows}

    def get_chunks_by_embedding_ids(self, embedding_ids: List[int]) -> List[Dict[str, Any]]:
        if not embedding_ids:
            return []
        placeholders = ",".join("?" for _ in embedding_ids)
        query = f"""
        SELECT c.*, f.file_path, f.file_name, f.extension, f.category, f.file_size_bytes, f.modified_at
        FROM chunks c
        JOIN files f ON c.file_id = f.id
        WHERE c.embedding_id IN ({placeholders})
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, embedding_ids)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    def delete_file(self, file_path: str) -> List[int]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM files WHERE file_path = ?", (file_path,))
            file_row = cursor.fetchone()
            if not file_row:
                return []
            f_id = file_row["id"]

            cursor.execute("SELECT embedding_id FROM chunks WHERE file_id = ?", (f_id,))
            chunk_rows = cursor.fetchall()
            emb_ids = [r["embedding_id"] for r in chunk_rows if r["embedding_id"] is not None]

            cursor.execute("DELETE FROM files WHERE id = ?", (f_id,))
            conn.commit()
            return emb_ids

    def get_statistics(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total_files FROM files")
            total_files = cursor.fetchone()["total_files"]

            cursor.execute("SELECT COUNT(*) as indexed_files FROM files WHERE status = 'indexed'")
            indexed_files = cursor.fetchone()["indexed_files"]

            cursor.execute("SELECT COUNT(*) as failed_files FROM files WHERE status = 'failed'")
            failed_files = cursor.fetchone()["failed_files"]

            cursor.execute("SELECT COUNT(*) as total_chunks FROM chunks")
            total_chunks = cursor.fetchone()["total_chunks"]

            cursor.execute("SELECT category, COUNT(*) as count FROM files GROUP BY category")
            categories = {r["category"]: r["count"] for r in cursor.fetchall()}

            cursor.execute("SELECT MAX(indexed_at) as last_index_time FROM files")
            last_index = cursor.fetchone()["last_index_time"]

            return {
                "total_files": total_files,
                "indexed_files": indexed_files,
                "failed_files": failed_files,
                "total_chunks": total_chunks,
                "categories": categories,
                "last_index_time": last_index
            }


_db_instance = None


def get_db() -> DatabaseManager:
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance


def reset_db():
    global _db_instance
    _db_instance = None
