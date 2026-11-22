import os
import sys
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from backend.storage.db import get_db

logger = logging.getLogger(__name__)


class FileService:
    def __init__(self):
        self.db = get_db()

    def _is_path_allowed(self, path: Path) -> bool:
        """Verify that the target path is an indexed file or within configured scan directories."""
        # 1. Check if file is in SQLite database
        if self.db.get_file_by_path(str(path)) or self.db.get_file_by_path(str(path.resolve())):
            return True

        # 2. Check if file is within configured included scan directories
        from backend.config.settings import config
        try:
            resolved_path = path.resolve()
            for inc_dir in config.included_directories:
                inc_path = Path(inc_dir).resolve()
                if resolved_path == inc_path or inc_path in resolved_path.parents:
                    return True
        except Exception:
            pass

        return False

    def open_file(self, file_path_or_id) -> Dict[str, Any]:
        """
        Open the original file using the operating system's default application.
        Never modifies, deletes, or moves the file.
        Validates target is within allowed/indexed paths to prevent arbitrary execution.
        """
        path_str = self._resolve_path(file_path_or_id)
        if not path_str:
            return {"success": False, "error": "File record not found."}

        path = Path(path_str)
        if not path.exists():
            return {"success": False, "error": f"File no longer exists at: {path_str}"}

        if not self._is_path_allowed(path):
            return {"success": False, "error": f"Access denied: file '{path.name}' is outside configured search paths."}

        try:
            if sys.platform == "win32":
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
            return {"success": True, "message": f"Opened {path.name}"}
        except Exception as e:
            logger.error(f"Failed to open file {path}: {e}")
            return {"success": False, "error": str(e)}

    def open_file_location(self, file_path_or_id) -> Dict[str, Any]:
        """
        Open the folder containing the file and select/highlight the file.
        Uses list-form subprocess arguments without shell string execution.
        """
        path_str = self._resolve_path(file_path_or_id)
        if not path_str:
            return {"success": False, "error": "File record not found."}

        path = Path(path_str)
        if not path.exists():
            return {"success": False, "error": f"File no longer exists at: {path_str}"}

        if not self._is_path_allowed(path):
            return {"success": False, "error": f"Access denied: file '{path.name}' is outside configured search paths."}

        try:
            if sys.platform == "win32":
                # Select file in Windows Explorer without shell injection
                subprocess.Popen(["explorer.exe", f"/select,{path}"])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path.parent)])
            return {"success": True, "message": f"Opened containing folder for {path.name}"}
        except Exception as e:
            logger.error(f"Failed to open folder for {path}: {e}")
            return {"success": False, "error": str(e)}

    def get_file_preview(self, file_id: int) -> Dict[str, Any]:
        """
        Get structured preview data for a file including its indexed chunks and metadata.
        """
        file_rec = self.db.get_file_by_id(file_id)
        if not file_rec:
            return {"success": False, "error": "File not found"}

        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM chunks WHERE file_id = ? ORDER BY unit_number, chunk_index LIMIT 20",
                (file_id,)
            )
            chunks = [dict(r) for r in cursor.fetchall()]

        return {
            "success": True,
            "file": file_rec,
            "chunks": chunks
        }

    def _resolve_path(self, file_path_or_id) -> Optional[str]:
        if isinstance(file_path_or_id, int) or (isinstance(file_path_or_id, str) and file_path_or_id.isdigit()):
            file_rec = self.db.get_file_by_id(int(file_path_or_id))
            return file_rec["file_path"] if file_rec else None
        return str(file_path_or_id)


_file_service = None


def get_file_service() -> FileService:
    global _file_service
    if _file_service is None:
        _file_service = FileService()
    return _file_service
