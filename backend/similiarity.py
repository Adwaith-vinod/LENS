"""
Backward-compatible similarity script.
"""
from backend.embeddings.engine import get_embedding_engine
import numpy as np

engine = get_embedding_engine()


def calculate_similarity(text1: str, text2: str) -> float:
    e1 = engine.encode_query(text1)
    e2 = engine.encode_query(text2)
    # Since vectors are normalized, dot product equals cosine similarity
    return float(np.dot(e1[0], e2[0]))


if __name__ == "__main__":
    t1 = "Python is used for machine learning"
    t2 = "The weather is very hot today"
    score = calculate_similarity(t1, t2)
    print("Similarity:", score)
