import os
import shutil
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.config import settings
from backend.storage.db import DatabaseManager, reset_db, get_db
from backend.storage.vector_store import PersistentVectorStore, reset_vector_store, get_vector_store
from backend.indexing.indexer import LensIndexer, reset_indexer, get_indexer
from backend.search.engine import SearchEngine, reset_search_engine, get_search_engine
from backend.services.file_service import FileService
from backend.api.app import app


@pytest.fixture(autouse=True)
def isolate_lens_environment(tmp_path, monkeypatch):
    """
    Autouse fixture that runs for every test.
    Forces LENS_DATA_DIR to a temporary directory so real ./data is NEVER touched.
    """
    test_data_dir = tmp_path / "lens_test_data"
    test_data_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("LENS_DATA_DIR", str(test_data_dir))
    monkeypatch.setenv("LENS_TEST_MODE", "1")

    # Reset singletons before test
    reset_db()
    reset_vector_store()
    reset_indexer()
    reset_search_engine()

    yield test_data_dir

    # Reset singletons after test
    reset_db()
    reset_vector_store()
    reset_indexer()
    reset_search_engine()


@pytest.fixture
def clean_db(isolate_lens_environment):
    return get_db()


@pytest.fixture
def clean_vector_store(isolate_lens_environment):
    return get_vector_store()


@pytest.fixture
def clean_indexer(clean_db, clean_vector_store):
    indexer = get_indexer()
    indexer.db = clean_db
    indexer.vector_store = clean_vector_store
    return indexer


@pytest.fixture
def clean_search_engine(clean_db, clean_vector_store):
    engine = get_search_engine()
    engine.db = clean_db
    engine.vector_store = clean_vector_store
    return engine


@pytest.fixture
def test_client(isolate_lens_environment):
    return TestClient(app)
