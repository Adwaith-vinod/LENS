import faiss
import numpy as np


def create_index(embeddings):

    embeddings = np.array(embeddings).astype("float32")

    dimension = embeddings.shape[1]

    index = faiss.IndexFlatL2(dimension)

    index.add(embeddings)

    return index

if __name__ == "__main__":

    embeddings = np.array([
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9],
        [1, 2, 3],
        [4, 5, 6],
        [7, 8, 9]
    ]).astype("float32")

    index = create_index(embeddings)

    print("Number of vectors:", index.ntotal)