import os
import logging
from pathlib import Path
from typing import List, Tuple, Optional
import numpy as np
import faiss

from backend.config.settings import TEXT_INDEX_PATH, EMBEDDING_DIMENSION, get_text_index_path

logger = logging.getLogger(__name__)


class PersistentVectorStore:
    """
    Persistent FAISS vector store using IndexIDMap2 and IndexFlatIP (cosine similarity).
    Maps FAISS vector IDs directly to SQLite chunk embedding_ids.
    """

    def __init__(self, index_path: Optional[Path] = None, dimension: int = EMBEDDING_DIMENSION):
        self.index_path = index_path or get_text_index_path()
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.dimension = dimension
        self.index: Optional[faiss.IndexIDMap2] = None
        self.load_or_create()

    def load_or_create(self):
        """Load index from disk or create an empty IndexIDMap2(IndexFlatIP)."""
        if self.index_path.exists():
            try:
                logger.info(f"Loading FAISS index from {self.index_path}")
                self.index = faiss.read_index(str(self.index_path))
                logger.info(f"FAISS index loaded. Total vectors: {self.index.ntotal}")
                return
            except Exception as e:
                logger.error(f"Failed to load FAISS index from {self.index_path}: {e}. Recreating.")

        flat_index = faiss.IndexFlatIP(self.dimension)
        self.index = faiss.IndexIDMap2(flat_index)
        logger.info(f"Created new empty FAISS IndexIDMap2(IndexFlatIP({self.dimension}))")

    def add_vectors(self, vectors: np.ndarray, ids: List[int]):
        """
        Add normalized vectors with specific integer IDs to the index.
        """
        if len(vectors) == 0 or len(ids) == 0:
            return

        vectors = np.ascontiguousarray(vectors, dtype="float32")
        ids_arr = np.array(ids, dtype="int64")

        # In case IDs already exist, remove them first to prevent duplicates
        try:
            self.index.remove_ids(ids_arr)
        except Exception:
            pass

        self.index.add_with_ids(vectors, ids_arr)
        self.save()

    def remove_vectors(self, ids: List[int]):
        """Remove specific vector IDs from the index."""
        if not ids or self.index.ntotal == 0:
            return
        ids_arr = np.array(ids, dtype="int64")
        try:
            self.index.remove_ids(ids_arr)
            self.save()
        except Exception as e:
            logger.warning(f"Error removing IDs from FAISS index: {e}")

    def search(self, query_vector: np.ndarray, top_k: int = 20) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for top_k nearest vectors.
        Returns:
            scores: array of cosine similarity scores [-1.0, 1.0]
            ids: array of chunk IDs
        """
        if self.index.ntotal == 0:
            return np.empty((1, 0), dtype="float32"), np.empty((1, 0), dtype="int64")

        query_vector = np.ascontiguousarray(query_vector, dtype="float32")
        if len(query_vector.shape) == 1:
            query_vector = query_vector.reshape(1, -1)

        actual_k = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(query_vector, actual_k)
        return scores, indices

    def save(self):
        """Save the index to disk."""
        try:
            faiss.write_index(self.index, str(self.index_path))
        except Exception as e:
            logger.error(f"Failed to save FAISS index: {e}")

    def clear(self):
        """Clear all vectors from the index."""
        flat_index = faiss.IndexFlatIP(self.dimension)
        self.index = faiss.IndexIDMap2(flat_index)
        self.save()

    @property
    def ntotal(self) -> int:
        return self.index.ntotal if self.index else 0


_vector_store_instance = None


def get_vector_store() -> PersistentVectorStore:
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = PersistentVectorStore()
    return _vector_store_instance


def reset_vector_store():
    global _vector_store_instance
    _vector_store_instance = None
