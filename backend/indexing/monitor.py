import time
import logging
from pathlib import Path
from typing import List, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from backend.config.settings import config
from backend.discovery.file_filters import is_supported_file
from backend.discovery.scanner import get_file_metadata
from backend.indexing.indexer import get_indexer

logger = logging.getLogger(__name__)


class LensChangeHandler(FileSystemEventHandler):
    def __init__(self, indexer):
        super().__init__()
        self.indexer = indexer

    def on_modified(self, event):
        if not event.is_directory:
            p = Path(event.src_path)
            if is_supported_file(p):
                meta = get_file_metadata(p)
                if meta:
                    self.indexer._process_single_file(meta)

    def on_created(self, event):
        if not event.is_directory:
            p = Path(event.src_path)
            if is_supported_file(p):
                meta = get_file_metadata(p)
                if meta:
                    self.indexer._process_single_file(meta)

    def on_deleted(self, event):
        if not event.is_directory:
            removed = self.indexer.db.delete_file(event.src_path)
            if removed:
                self.indexer.vector_store.remove_vectors(removed)


class LensDirectoryWatcher:
    """
    Watches configured directories for file changes using watchdog.
    """

    def __init__(self):
        self.observer: Optional[Observer] = None
        self.indexer = get_indexer()
        self.running = False

    def start(self, directories: Optional[List[str]] = None):
        if self.running:
            return
        dirs = directories or config.included_directories
        self.observer = Observer()
        handler = LensChangeHandler(self.indexer)

        for d in dirs:
            p = Path(d)
            if p.exists() and p.is_dir():
                try:
                    self.observer.schedule(handler, str(p), recursive=True)
                    logger.info(f"Watching directory: {d}")
                except Exception as e:
                    logger.warning(f"Could not watch directory {d}: {e}")

        self.observer.start()
        self.running = True

    def stop(self):
        if self.observer and self.running:
            self.observer.stop()
            self.observer.join()
            self.running = False


_watcher_instance = None


def get_watcher() -> LensDirectoryWatcher:
    global _watcher_instance
    if _watcher_instance is None:
        _watcher_instance = LensDirectoryWatcher()
    return _watcher_instance
