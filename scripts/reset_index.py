#!/usr/bin/env python
"""
LENS - Manual Index Reset Tool
Resets the SQLite database, FAISS indices, and previews cache.
Optionally initiates a full fresh re-indexing of configured directories.

Usage:
    python scripts/reset_index.py [--force] [--reindex]
"""
import sys
import os
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.config.settings import get_data_dir, config
from backend.storage.db import get_db, reset_db
from backend.storage.vector_store import get_vector_store, reset_vector_store
from backend.indexing.indexer import get_indexer, reset_indexer


def reset_lens_index(reindex: bool = False, force: bool = False):
    data_dir = get_data_dir()
    print(f"LENS Data Directory: {data_dir}")

    if not force:
        confirm = input("Are you sure you want to completely reset the index? (y/N): ").strip().lower()
        if confirm != "y":
            print("Operation cancelled.")
            return

    print("Resetting database connections and vector store...")
    reset_db()
    reset_vector_store()
    reset_indexer()

    # Files to clear
    db_file = data_dir / "lens.db"
    wal_file = data_dir / "lens.db-wal"
    shm_file = data_dir / "lens.db-shm"
    text_index = data_dir / "lens_text.index"
    visual_index = data_dir / "lens_visual.index"

    for f in [wal_file, shm_file, db_file, text_index, visual_index]:
        if f.exists():
            try:
                f.unlink()
                print(f"Removed: {f.name}")
            except Exception as e:
                print(f"Warning: could not delete {f.name}: {e}")

    # Re-initialize clean state
    db = get_db()
    vstore = get_vector_store()
    print(f"Initialized fresh database: {db.db_path.name}")
    print(f"Initialized fresh vector store: {vstore.index_path.name} (dimension={vstore.dimension})")

    if reindex:
        print("\nStarting full re-indexing of configured directories...")
        print(f"Scan directories: {config.included_directories}")
        indexer = get_indexer()
        status = indexer.start_indexing(background=False)
        print(f"Indexing finished: {status.get('message', 'Done')}")
    else:
        print("\nReset complete. You can start indexing anytime using the UI or 'python scripts/reset_index.py --reindex'.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reset LENS search index and database.")
    parser.add_argument("--force", "-f", action="store_true", help="Skip confirmation prompt")
    parser.add_argument("--reindex", "-r", action="store_true", help="Immediately run full re-indexing after reset")
    args = parser.parse_args()

    reset_lens_index(reindex=args.reindex, force=args.force)
