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

    def open_file(self, file_path_or_id) -> Dict[str, Any]:
        """
        Open the original file using the operating system's default application.
        Never modifies, deletes, or moves the file.
        """
        path_str = self._resolve_path(file_path_or_id)
        if not path_str:
            return {"success": False, "error": "File record not found."}

        path = Path(path_str)
        if not path.exists():
            return {"success": False, "error": f"File no longer exists at: {path_str}"}

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
        """
        path_str = self._resolve_path(file_path_or_id)
        if not path_str:
            return {"success": False, "error": "File record not found."}

        path = Path(path_str)
        if not path.exists():
            return {"success": False, "error": f"File no longer exists at: {path_str}"}

        try:
            if sys.platform == "win32":
                # Select file in Windows Explorer
                subprocess.Popen(f'explorer /select,"{path}"')
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
