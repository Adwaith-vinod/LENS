"""
Backward-compatible vector_store wrapper.
"""
import faiss
import numpy as np
from backend.storage.vector_store import get_vector_store


def create_index(embeddings):
    """
    Creates an in-memory L2 index from numpy embeddings.
    Retains prototype signature.
    """
    embeddings = np.array(embeddings).astype("float32")
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    return index
