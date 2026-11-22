import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.storage.db import get_db
from backend.storage.vector_store import get_vector_store
from backend.indexing.indexer import get_indexer
from backend.search.engine import get_search_engine
from backend.processing.chunker import DocumentChunk
from backend.api.app import app


def test_fts5_indexing_and_search(tmp_path):
    db = get_db()
    indexer = get_indexer()

    # Create dummy files
    f1 = tmp_path / "microservices.txt"
    f1.write_text("Docker containerization and Kubernetes cluster management orchestration.", encoding="utf-8")

    f2 = tmp_path / "cooking.txt"
    f2.write_text("Recipe for baking sourdough bread and pizza dough fermentation.", encoding="utf-8")

    indexer.start_indexing(custom_directories=[str(tmp_path)], background=False)

    # Test FTS5 search
    res = db.search_fts("Kubernetes Docker", limit=10)
    assert len(res) > 0
    # The chunk matching Kubernetes should be in res
    chunk_ids = [r["chunk_id"] for r in res]
    records = db.get_chunks_by_ids(chunk_ids)
    assert any("Kubernetes" in r["chunk_text"] for r in records)


def test_embedding_text_enrichment():
    chunk = DocumentChunk(
        chunk_id=1,
        file_path="C:/docs/AI.pdf",
        file_name="AI.pdf",
        category="documents",
        unit_type="page",
        unit_number=2,
        chunk_index=0,
        chunk_text="Deep convolutional neural network architecture.",
        source_info="Page 2"
    )
    assert chunk.embedding_text == "AI.pdf | Page 2 | Deep convolutional neural network architecture."


def test_hybrid_search_rrf_retrieval(tmp_path):
    indexer = get_indexer()
    searcher = get_search_engine()

    doc = tmp_path / "quantum_computing.txt"
    doc.write_text("Quantum superposition and qubit entanglement algorithms.", encoding="utf-8")

    indexer.start_indexing(custom_directories=[str(tmp_path)], background=False)

    # Hybrid search
    res = searcher.search("qubit entanglement")
    assert res.total_results >= 1
    assert res.results[0].file_name == "quantum_computing.txt"
    assert res.results[0].relevance_score > 0.3


def test_health_endpoint_model_state():
    client = TestClient(app)
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert "model_loaded" in data
    assert "model_name" in data
    assert data["model_name"] == "all-MiniLM-L6-v2"
