"""
Backward-compatible wrapper for text extraction.
Integrates with the unified extraction engine.
"""
from pathlib import Path
from backend.extraction.unified import extract_file_content


def extract_text(path):
    """
    Extracts plain text string from supported file path.
    Preserves original prototype interface for backward compatibility.
    """
    res = extract_file_content(str(path))
    if not res.success or not res.content_units:
        return None
    return res.total_text
