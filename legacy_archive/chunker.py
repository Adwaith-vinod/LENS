"""
Backward-compatible wrapper for chunk_text.
"""
from backend.processing.chunker import split_text_into_sentences


def chunk_text(text, chunk_size=500):
    """
    Splits text into chunks of roughly chunk_size characters.
    Maintains compatibility with original prototype.
    """
    if not text:
        return []
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunk = text[i:i + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
    return chunks
