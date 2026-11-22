from pathlib import Path
import os
import json
import logging
from typing import List, Set

logger = logging.getLogger(__name__)

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "lens.db"
TEXT_INDEX_PATH = DATA_DIR / "lens_text.index"
VISUAL_INDEX_PATH = DATA_DIR / "lens_visual.index"
CONFIG_FILE = DATA_DIR / "config.json"
PREVIEWS_DIR = DATA_DIR / "previews"
PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)

# Performance & Chunking
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 60
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB


def get_default_scan_directories() -> List[str]:
    """
    Returns prioritized user directories on Windows (e.g., Documents, Desktop, Downloads),
    falling back to User Home or Project Root.
    """
    user_home = Path.home()
    candidates = [
        user_home / "Documents",
        user_home / "Desktop",
        user_home / "Downloads"
    ]
    existing = [str(p.resolve()) for p in candidates if p.exists() and p.is_dir()]
    if not existing:
        existing = [str(user_home.resolve())]
    return existing


class LensConfig:
    def __init__(self):
        self.config_path = CONFIG_FILE
        self.included_directories: List[str] = get_default_scan_directories()
        self.excluded_directories: List[str] = [
            "node_modules", ".git", ".venv", "venv", "__pycache__",
            "AppData", "Program Files", "Program Files (x86)", "Windows",
            "$Recycle.Bin", "System Volume Information", "cache", "temp", "tmp"
        ]
        self.max_file_size_bytes: int = MAX_FILE_SIZE_BYTES
        self.chunk_size: int = DEFAULT_CHUNK_SIZE
        self.chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
        self.enable_watchdog: bool = False
        self.load()

    def load(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.included_directories = data.get("included_directories", self.included_directories)
                    self.excluded_directories = data.get("excluded_directories", self.excluded_directories)
                    self.max_file_size_bytes = data.get("max_file_size_bytes", self.max_file_size_bytes)
                    self.chunk_size = data.get("chunk_size", self.chunk_size)
                    self.chunk_overlap = data.get("chunk_overlap", self.chunk_overlap)
                    self.enable_watchdog = data.get("enable_watchdog", self.enable_watchdog)
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}")

    def save(self):
        try:
            data = {
                "included_directories": self.included_directories,
                "excluded_directories": self.excluded_directories,
                "max_file_size_bytes": self.max_file_size_bytes,
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap,
                "enable_watchdog": self.enable_watchdog
            }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save config file: {e}")


config = LensConfig()
