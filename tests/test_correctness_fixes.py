from datetime import datetime
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.config.settings import get_data_dir
from backend.storage.db import get_db
from backend.storage.vector_store import get_vector_store
from backend.indexing.indexer import get_indexer
from backend.processing.chunker import DocumentChunk
from backend.api.app import app


def test_wal_and_busy_timeout():
    db = get_db()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        cursor.execute("PRAGMA busy_timeout")
        timeout = cursor.fetchone()[0]
    assert mode.lower() in ("wal", "memory")
    assert timeout >= 20000


def test_reindex_prunes_faiss_vectors(tmp_path):
    db = get_db()
    vstore = get_vector_store()
    indexer = get_indexer()

    # Create a test document
    doc_path = tmp_path / "test_doc.txt"
    doc_path.write_text("Sentence one about machine learning. " * 30, encoding="utf-8")

    # Initial indexing
    indexer.start_indexing(custom_directories=[str(tmp_path)], background=False)
    file_rec = db.get_file_by_path(str(doc_path))
    assert file_rec is not None
    assert file_rec["status"] == "indexed"
    assert file_rec["content_hash"] is not None
    initial_chunks = len(db.get_chunks_for_file(file_rec["id"]))
    assert initial_chunks > 0
    assert vstore.ntotal == initial_chunks

    # Modify the document to have different content and length
    doc_path.write_text("A completely new topic about database indexing and SQL engines. " * 50, encoding="utf-8")

    # Force re-index by running indexing again (mtime has changed)
    indexer.start_indexing(custom_directories=[str(tmp_path)], background=False)
    new_chunks = len(db.get_chunks_for_file(file_rec["id"]))
    assert new_chunks > 0
    # Old vectors must be pruned: total vectors in FAISS must equal new_chunks, not initial_chunks + new_chunks
    assert vstore.ntotal == new_chunks


def test_empty_or_failed_files_skipped_if_unchanged(tmp_path, monkeypatch):
    db = get_db()
    indexer = get_indexer()

    bad_file = tmp_path / "bad_file.txt"
    bad_file.write_text("Temporary bad content", encoding="utf-8")
    stat = bad_file.stat()
    mtime_iso = datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat()

    # Upsert with failed status
    db.upsert_file(
        file_path=str(bad_file.resolve()),
        file_name=bad_file.name,
        extension=".txt",
        category="documents",
        file_size_bytes=stat.st_size,
        modified_at=mtime_iso,
        status="failed",
        error_message="Simulated corrupt file"
    )

    # Track calls to _process_single_file
    call_count = 0
    original_process = indexer._process_single_file

    def mock_process(file_info):
        nonlocal call_count
        call_count += 1
        return original_process(file_info)

    monkeypatch.setattr(indexer, "_process_single_file", mock_process)

    # Run indexing pipeline
    indexer.start_indexing(custom_directories=[str(tmp_path)], background=False)

    # Since file is unchanged and status is 'failed', it must be skipped
    assert call_count == 0


def test_content_hash_and_indexing_runs(tmp_path):
    db = get_db()
    indexer = get_indexer()

    f = tmp_path / "sample.txt"
    f.write_text("Hello world testing hash", encoding="utf-8")

    indexer.start_indexing(custom_directories=[str(tmp_path)], background=False)

    file_rec = db.get_file_by_path(str(f))
    assert file_rec is not None
    assert file_rec["content_hash"] is not None
    assert len(file_rec["content_hash"]) == 64  # SHA-256 hex string

    # Verify indexing_runs record
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM indexing_runs ORDER BY id DESC LIMIT 1")
        run = cursor.fetchone()
        assert run is not None
        assert run["status"] == "completed"
        assert run["total_files"] >= 1


def test_cancel_indexing():
    indexer = get_indexer()
    indexer.cancel_indexing()
    status = indexer.get_status()
    assert status["status"] in ("cancelling", "cancelled")


def test_open_endpoints_body_support():
    client = TestClient(app)

    # Test open by body with nonexistent file returns 400
    res = client.post("/api/files/open", json={"file_path": "C:\\nonexistent\\file.txt"})
    assert res.status_code == 400
    assert "File no longer exists" in res.json()["detail"] or "record not found" in res.json()["detail"]

    # Test open-location by body with nonexistent file returns 400
    res = client.post("/api/files/open-location", json={"file_path": "C:\\nonexistent\\file.txt"})
    assert res.status_code == 400

    # Test cancel endpoint
    res = client.post("/api/index/cancel")
    assert res.status_code == 200
    assert res.json()["status"] == "cancelling"
