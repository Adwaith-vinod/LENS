from pathlib import Path
import os
import json
import logging
from typing import List, Set

logger = logging.getLogger(__name__)

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def get_data_dir() -> Path:
    env_dir = os.environ.get("LENS_DATA_DIR")
    if env_dir:
        d = Path(env_dir).resolve()
    else:
        d = PROJECT_ROOT / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_db_path() -> Path:
    return get_data_dir() / "lens.db"


def get_text_index_path() -> Path:
    return get_data_dir() / "lens_text.index"


def get_visual_index_path() -> Path:
    return get_data_dir() / "lens_visual.index"


def get_config_file() -> Path:
    return get_data_dir() / "config.json"


def get_previews_dir() -> Path:
    p = get_data_dir() / "previews"
    p.mkdir(parents=True, exist_ok=True)
    return p


DATA_DIR = get_data_dir()
DB_PATH = get_db_path()
TEXT_INDEX_PATH = get_text_index_path()
VISUAL_INDEX_PATH = get_visual_index_path()
CONFIG_FILE = get_config_file()
PREVIEWS_DIR = get_previews_dir()

# Performance & Chunking
DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 60
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB


def get_default_scan_directories() -> List[str]:
    """
    Returns prioritized user directories on Windows (e.g., Documents, Desktop, Downloads),
    accounting for Microsoft OneDrive redirection on Windows 10/11.
    """
    user_home = Path.home()
    candidates = [
        user_home / "OneDrive" / "Desktop",
        user_home / "Desktop",
        user_home / "OneDrive" / "Documents",
        user_home / "Documents",
        user_home / "Downloads"
    ]
    seen = set()
    existing = []
    for p in candidates:
        if p.exists() and p.is_dir():
            norm = os.path.normcase(os.path.normpath(str(p.resolve())))
            if norm not in seen:
                seen.add(norm)
                existing.append(str(p.resolve()))

    if not existing:
        existing = [str(user_home.resolve())]
    return existing


class LensConfig:
    def __init__(self):
        self.config_path = get_config_file()
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
                    # Automatically ensure active user directories (e.g., Desktop/OneDrive) are included
                    existing_norm = {os.path.normcase(os.path.normpath(d)) for d in self.included_directories}
                    for default_dir in get_default_scan_directories():
                        if os.path.normcase(os.path.normpath(default_dir)) not in existing_norm:
                            self.included_directories.append(default_dir)
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


_config_instances = {}


def get_config() -> LensConfig:
    cfg_file = get_config_file()
    if cfg_file not in _config_instances:
        _config_instances[cfg_file] = LensConfig()
    return _config_instances[cfg_file]


class ConfigProxy:
    def __getattr__(self, name):
        return getattr(get_config(), name)

    def __setattr__(self, name, value):
        setattr(get_config(), name, value)


config = ConfigProxy()
