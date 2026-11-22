import os
import time
import hashlib
import logging
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional

from backend.config.settings import config
from backend.discovery.scanner import scan_directories
from backend.discovery.system_discovery import discover_fixed_drives
from backend.extraction.unified import extract_file_content
from backend.processing.chunker import chunk_document
from backend.embeddings.engine import get_embedding_engine
from backend.storage.db import get_db
from backend.storage.vector_store import get_vector_store

logger = logging.getLogger(__name__)


def compute_content_hash(file_path: str) -> Optional[str]:
    """Compute SHA-256 hash of a file's binary content."""
    try:
        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        logger.debug(f"Could not compute hash for {file_path}: {e}")
        return None


class IndexingProgress:
    def __init__(self):
        self.status: str = "idle"  # idle, scanning, indexing, completed, error
        self.total_files: int = 0
        self.processed_files: int = 0
        self.indexed_files: int = 0
        self.failed_files: int = 0
        self.current_file: Optional[str] = None
        self.message: str = "Ready"
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "indexed_files": self.indexed_files,
            "failed_files": self.failed_files,
            "current_file": self.current_file,
            "message": self.message,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "error": self.error,
            "percent_complete": (
                round((self.processed_files / self.total_files) * 100, 1)
                if self.total_files > 0 else 0
            )
        }


class LensIndexer:
    """
    Main Indexing Engine for LENS.
    Coordinates file discovery, incremental checking, multiformat extraction,
    chunking, embedding generation, SQLite persistence, and FAISS indexing.
    """

    def __init__(self):
        self.db = get_db()
        self.vector_store = get_vector_store()
        self.embedding_engine = get_embedding_engine()
        self.progress = IndexingProgress()
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._cancel_requested = False

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return self.progress.to_dict()

    def start_indexing(self, custom_directories: Optional[List[str]] = None, background: bool = True) -> Dict[str, Any]:
        with self._lock:
            if self.progress.status in ["scanning", "indexing"]:
                return {"status": "already_running", "message": "Indexing is currently in progress."}

            self.progress = IndexingProgress()
            self.progress.status = "scanning"
            self.progress.start_time = time.time()
            self.progress.message = "Discovering files..."
            self._cancel_requested = False

        target_dirs = custom_directories or config.included_directories
        if not target_dirs:
            target_dirs = [str(d) for d in discover_fixed_drives()]

        if background:
            self._thread = threading.Thread(target=self._run_indexing_pipeline, args=(target_dirs,), daemon=True)
            self._thread.start()
            return {"status": "started", "message": "Indexing started in background."}
        else:
            self._run_indexing_pipeline(target_dirs)
            return self.get_status()

    def cancel_indexing(self):
        """Request cancellation of the active indexing run."""
        self._cancel_requested = True
        with self._lock:
            self.progress.status = "cancelling"
            self.progress.message = "Cancelling indexing..."

    def _run_indexing_pipeline(self, directories: List[str]):
        run_id = None
        try:
            logger.info(f"Starting file discovery in: {directories}")
            discovered_files = scan_directories(directories)
            run_id = self.db.record_indexing_run_start(len(discovered_files))

            with self._lock:
                self.progress.total_files = len(discovered_files)
                self.progress.status = "indexing"
                self.progress.message = f"Found {len(discovered_files)} files. Beginning incremental indexing..."

            # Existing files in SQLite
            existing_db_files = self.db.get_all_indexed_files()
            discovered_paths_set = set()

            for file_info in discovered_files:
                if self._cancel_requested:
                    logger.info("Indexing cancelled by user.")
                    self.vector_store.save()
                    if run_id:
                        self.db.record_indexing_run_finish(
                            run_id,
                            self.progress.indexed_files,
                            self.progress.failed_files,
                            "cancelled",
                            "Indexing cancelled by user"
                        )
                    with self._lock:
                        self.progress.status = "cancelled"
                        self.progress.message = "Indexing was cancelled."
                    return

                f_path = file_info["file_path"]
                discovered_paths_set.add(f_path)

                with self._lock:
                    self.progress.current_file = file_info["file_name"]
                    self.progress.processed_files += 1

                # Incremental check: check if modified_at and size match
                existing = existing_db_files.get(f_path)
                if (
                    existing and
                    existing["status"] in ("indexed", "empty", "failed", "unsupported") and
                    existing["file_size_bytes"] == file_info["file_size_bytes"] and
                    existing["modified_at"] == file_info["modified_at"]
                ):
                    # File unchanged, skip re-embedding
                    continue

                # Process new or changed file
                self._process_single_file(file_info)

            # Cleanup deleted files from SQLite and FAISS
            for old_path in existing_db_files.keys():
                if not Path(old_path).exists():
                    logger.info(f"Pruning missing file: {old_path}")
                    removed_chunk_ids = self.db.delete_file(old_path)
                    if removed_chunk_ids:
                        self.vector_store.remove_vectors(removed_chunk_ids)

            # Persist vector store to disk after complete batch run
            self.vector_store.save()

            if run_id:
                self.db.record_indexing_run_finish(
                    run_id,
                    self.progress.indexed_files,
                    self.progress.failed_files,
                    "completed",
                    "Indexing completed successfully"
                )

            with self._lock:
                self.progress.status = "completed"
                self.progress.end_time = time.time()
                self.progress.current_file = None
                self.progress.message = (
                    f"Indexing complete. {self.progress.indexed_files} files updated/indexed, "
                    f"{self.progress.failed_files} failed."
                )

        except Exception as e:
            logger.exception(f"Unhandled error during indexing: {e}")
            self.vector_store.save()
            if run_id:
                self.db.record_indexing_run_finish(
                    run_id,
                    self.progress.indexed_files,
                    self.progress.failed_files,
                    "failed",
                    str(e)
                )
            with self._lock:
                self.progress.status = "error"
                self.progress.error = str(e)
                self.progress.message = f"Indexing failed: {e}"

    def _process_single_file(self, file_info: Dict[str, Any]):
        f_path = file_info["file_path"]
        f_name = file_info["file_name"]
        f_ext = file_info["extension"]
        f_cat = file_info["category"]
        f_size = file_info["file_size_bytes"]
        f_mtime = file_info["modified_at"]
        content_hash = compute_content_hash(f_path)

        try:
            # 1. Content Extraction
            extraction_result = extract_file_content(f_path, category=f_cat)
            if not extraction_result.success or not extraction_result.content_units:
                self.db.upsert_file(
                    file_path=f_path,
                    file_name=f_name,
                    extension=f_ext,
                    category=f_cat,
                    file_size_bytes=f_size,
                    modified_at=f_mtime,
                    content_hash=content_hash,
                    status="failed" if not extraction_result.success else "empty",
                    error_message=extraction_result.error_message or "No readable text content."
                )
                with self._lock:
                    self.progress.failed_files += 1
                return

            # 2. Source-aware Chunking
            chunks = chunk_document(
                extraction_result,
                chunk_size=config.chunk_size,
                chunk_overlap=config.chunk_overlap
            )

            if not chunks:
                self.db.upsert_file(
                    file_path=f_path,
                    file_name=f_name,
                    extension=f_ext,
                    category=f_cat,
                    file_size_bytes=f_size,
                    modified_at=f_mtime,
                    content_hash=content_hash,
                    status="empty",
                    error_message="Document yielded no chunks."
                )
                return

            # 3. SQLite File Record & Chunk Insertion
            file_id = self.db.upsert_file(
                file_path=f_path,
                file_name=f_name,
                extension=f_ext,
                category=f_cat,
                file_size_bytes=f_size,
                modified_at=f_mtime,
                content_hash=content_hash,
                status="indexed"
            )
            # Prune obsolete vectors from FAISS if this file was previously indexed
            old_embedding_ids = self.db.prune_chunks_for_file(file_id)
            if old_embedding_ids:
                self.vector_store.remove_vectors(old_embedding_ids)

            chunk_ids = self.db.insert_chunks(chunks, file_id)

            # 4. Batch Embeddings Generation
            chunk_texts = [c.chunk_text for c in chunks]
            vectors = self.embedding_engine.encode_texts(chunk_texts)

            # 5. Add to FAISS Vector Index (defer disk flush to end of batch)
            self.vector_store.add_vectors(vectors, chunk_ids, save=False)

            with self._lock:
                self.progress.indexed_files += 1

        except Exception as e:
            logger.warning(f"Error indexing file {f_path}: {e}")
            self.db.upsert_file(
                file_path=f_path,
                file_name=f_name,
                extension=f_ext,
                category=f_cat,
                file_size_bytes=f_size,
                modified_at=f_mtime,
                content_hash=content_hash,
                status="failed",
                error_message=str(e)
            )
            with self._lock:
                self.progress.failed_files += 1


_indexer_instance = None


def get_indexer() -> LensIndexer:
    global _indexer_instance
    if _indexer_instance is None:
        _indexer_instance = LensIndexer()
    return _indexer_instance


def reset_indexer():
    global _indexer_instance
    _indexer_instance = None
