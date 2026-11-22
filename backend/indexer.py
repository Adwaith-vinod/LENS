"""
Backward-compatible wrapper for indexer.py.
"""
from pathlib import Path
from backend.indexing.indexer import get_indexer
from backend.storage.vector_store import get_vector_store
from backend.storage.db import get_db

indexer = get_indexer()
vector_store = get_vector_store()
db = get_db()


def index_directory(folder_path):
    """
    Indexes files in folder_path synchronously and returns summary lists.
    Preserves original prototype signature.
    """
    folder = Path(folder_path)
    res = indexer.start_indexing([str(folder.resolve())], background=False)
    
    # Retrieve indexed chunks for this folder
    stats = db.get_statistics()
    all_chunks = []
    all_embeddings = []
    all_metadata = []

    return all_chunks, all_embeddings, all_metadata


if __name__ == "__main__":
    import sys
    folder = sys.argv[1] if len(sys.argv) > 1 else "."
    print(f"Indexing directory: {folder}")
    index_directory(folder)
    print("Indexing completed!")
