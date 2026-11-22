import unittest
import tempfile
from pathlib import Path
import numpy as np

from backend.storage.db import DatabaseManager
from backend.storage.vector_store import PersistentVectorStore
from backend.processing.chunker import DocumentChunk


class TestStorage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.root = Path(self.temp_dir.name)
        self.db = DatabaseManager(self.root / "test.db")
        self.vector_store = PersistentVectorStore(self.root / "test.index", dimension=4)

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_database_upsert_and_chunks(self):
        file_id = self.db.upsert_file(
            file_path="C:/docs/test.pdf",
            file_name="test.pdf",
            extension=".pdf",
            category="documents",
            file_size_bytes=1024,
            modified_at="2026-01-01T00:00:00Z"
        )
        self.assertIsInstance(file_id, int)

        chunks = [
            DocumentChunk(
                chunk_id=None,
                file_path="C:/docs/test.pdf",
                file_name="test.pdf",
                category="documents",
                unit_type="page",
                unit_number=1,
                chunk_index=0,
                chunk_text="Artificial intelligence and machine learning overview.",
                source_info="Page 1"
            )
        ]
        chunk_ids = self.db.insert_chunks(chunks, file_id)
        self.assertEqual(len(chunk_ids), 1)

        retrieved = self.db.get_chunks_by_embedding_ids(chunk_ids)
        self.assertEqual(len(retrieved), 1)
        self.assertEqual(retrieved[0]["file_name"], "test.pdf")
        self.assertIn("machine learning", retrieved[0]["chunk_text"])

    def test_vector_store_persistence(self):
        vectors = np.array([
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0]
        ], dtype="float32")
        ids = [101, 102]

        self.vector_store.add_vectors(vectors, ids)
        self.assertEqual(self.vector_store.ntotal, 2)

        # Search
        query = np.array([[1.0, 0.0, 0.0, 0.0]], dtype="float32")
        scores, found_ids = self.vector_store.search(query, top_k=2)
        self.assertEqual(found_ids[0][0], 101)
        self.assertAlmostEqual(scores[0][0], 1.0, places=4)

        # Reload vector store from disk
        reloaded = PersistentVectorStore(self.root / "test.index", dimension=4)
        self.assertEqual(reloaded.ntotal, 2)
        scores2, found_ids2 = reloaded.search(query, top_k=2)
        self.assertEqual(found_ids2[0][0], 101)


if __name__ == "__main__":
    unittest.main()
