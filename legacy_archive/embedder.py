"""
Backward-compatible wrapper for embedder.
"""
from backend.embeddings.engine import get_embedding_engine

engine = get_embedding_engine()
model = engine.text_model


def get_embedding(text):
    return engine.encode_query(text)[0]
