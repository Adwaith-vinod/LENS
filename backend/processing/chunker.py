import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from backend.extraction.models import ExtractionResult, ContentUnit


@dataclass
class DocumentChunk:
    chunk_id: Optional[int]
    file_path: str
    file_name: str
    category: str
    unit_type: str  # "page", "slide", "sheet", "section", etc.
    unit_number: int  # 1-indexed page/slide/sheet number
    chunk_index: int  # 0, 1, 2... within file or unit
    chunk_text: str
    source_info: str  # e.g., "Page 3", "Slide 2", "Sheet: Financials"
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def embedding_text(self) -> str:
        """Context-enriched text representation for dense embedding generation."""
        prefix = f"{self.file_name} | {self.source_info} | " if self.source_info else f"{self.file_name} | "
        return f"{prefix}{self.chunk_text}"


def split_text_into_sentences(text: str) -> List[str]:
    """
    Split text into sentences while respecting common punctuation and line breaks.
    """
    # Normalize double linebreaks
    paragraphs = text.split("\n\n")
    sentences = []
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # Regex to split on sentence ends followed by whitespace or line break
        parts = re.split(r'(?<=[.!?])\s+|\n', para)
        for part in parts:
            cleaned = part.strip()
            if cleaned:
                sentences.append(cleaned)
                
    return sentences


def chunk_content_unit(
    unit: ContentUnit,
    file_path: str,
    file_name: str,
    category: str,
    chunk_size: int = 500,
    chunk_overlap: int = 60,
    start_chunk_idx: int = 0
) -> List[DocumentChunk]:
    """
    Intelligently splits a single ContentUnit into chunks preserving sentence boundaries.
    """
    text = unit.text.strip()
    if not text:
        return []

    # If text fits easily into a single chunk, return it directly
    if len(text) <= chunk_size:
        source_label = format_source_label(unit)
        return [DocumentChunk(
            chunk_id=None,
            file_path=file_path,
            file_name=file_name,
            category=category,
            unit_type=unit.unit_type,
            unit_number=unit.unit_number,
            chunk_index=start_chunk_idx,
            chunk_text=text,
            source_info=source_label,
            metadata=unit.metadata
        )]

    sentences = split_text_into_sentences(text)
    if not sentences:
        # Fallback to direct character slicing if no clear sentence boundaries
        sentences = [text]

    chunks = []
    current_sentences: List[str] = []
    current_len = 0
    chunk_idx = start_chunk_idx
    source_label = format_source_label(unit)

    for sentence in sentences:
        sentence_len = len(sentence)

        # If a single sentence is longer than chunk_size, slice it
        if sentence_len > chunk_size:
            if current_sentences:
                chunk_str = " ".join(current_sentences).strip()
                if chunk_str:
                    chunks.append(DocumentChunk(
                        chunk_id=None,
                        file_path=file_path,
                        file_name=file_name,
                        category=category,
                        unit_type=unit.unit_type,
                        unit_number=unit.unit_number,
                        chunk_index=chunk_idx,
                        chunk_text=chunk_str,
                        source_info=source_label,
                        metadata=unit.metadata
                    ))
                    chunk_idx += 1
                current_sentences = []
                current_len = 0

            # Break long sentence by words
            words = sentence.split()
            word_buf = []
            word_len = 0
            for word in words:
                if word_len + len(word) + 1 > chunk_size and word_buf:
                    chunks.append(DocumentChunk(
                        chunk_id=None,
                        file_path=file_path,
                        file_name=file_name,
                        category=category,
                        unit_type=unit.unit_type,
                        unit_number=unit.unit_number,
                        chunk_index=chunk_idx,
                        chunk_text=" ".join(word_buf),
                        source_info=source_label,
                        metadata=unit.metadata
                    ))
                    chunk_idx += 1
                    # Overlap
                    word_buf = word_buf[-3:] if len(word_buf) >= 3 else word_buf
                    word_len = sum(len(w) + 1 for w in word_buf)

                word_buf.append(word)
                word_len += len(word) + 1

            if word_buf:
                current_sentences = [" ".join(word_buf)]
                current_len = word_len
            continue

        if current_len + sentence_len + 1 > chunk_size and current_sentences:
            chunk_str = " ".join(current_sentences).strip()
            chunks.append(DocumentChunk(
                chunk_id=None,
                file_path=file_path,
                file_name=file_name,
                category=category,
                unit_type=unit.unit_type,
                unit_number=unit.unit_number,
                chunk_index=chunk_idx,
                chunk_text=chunk_str,
                source_info=source_label,
                metadata=unit.metadata
            ))
            chunk_idx += 1

            # Keep last sentence for overlap if appropriate
            overlap_sentences = []
            overlap_len = 0
            for s in reversed(current_sentences):
                if overlap_len + len(s) + 1 <= chunk_overlap:
                    overlap_sentences.insert(0, s)
                    overlap_len += len(s) + 1
                else:
                    break
            current_sentences = overlap_sentences
            current_len = overlap_len

        current_sentences.append(sentence)
        current_len += sentence_len + 1

    if current_sentences:
        chunk_str = " ".join(current_sentences).strip()
        if chunk_str:
            chunks.append(DocumentChunk(
                chunk_id=None,
                file_path=file_path,
                file_name=file_name,
                category=category,
                unit_type=unit.unit_type,
                unit_number=unit.unit_number,
                chunk_index=chunk_idx,
                chunk_text=chunk_str,
                source_info=source_label,
                metadata=unit.metadata
            ))

    return chunks


def format_source_label(unit: ContentUnit) -> str:
    """Format human-readable source label (e.g. Page 3, Slide 5, Sheet: Data)."""
    if unit.unit_type == "page":
        return f"Page {unit.unit_number}"
    elif unit.unit_type == "slide":
        return f"Slide {unit.unit_number}"
    elif unit.unit_type == "sheet":
        sheet_name = unit.metadata.get("sheet_name", f"Sheet {unit.unit_number}")
        return f"Sheet: {sheet_name}"
    elif unit.unit_type == "section":
        sec_title = unit.metadata.get("section_title")
        return f"Section: {sec_title}" if sec_title else f"Section {unit.unit_number}"
    elif unit.unit_type == "table":
        return f"Table {unit.unit_number}"
    elif unit.unit_type == "image":
        return "Image"
    return f"{unit.unit_type.capitalize()} {unit.unit_number}"


def chunk_document(
    extraction_result: ExtractionResult,
    chunk_size: int = 500,
    chunk_overlap: int = 60
) -> List[DocumentChunk]:
    """
    Splits all ContentUnits in an ExtractionResult into source-annotated DocumentChunks.
    """
    all_chunks = []
    chunk_idx = 0

    for unit in extraction_result.content_units:
        unit_chunks = chunk_content_unit(
            unit=unit,
            file_path=extraction_result.file_path,
            file_name=extraction_result.file_name,
            category=extraction_result.category,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            start_chunk_idx=chunk_idx
        )
        all_chunks.extend(unit_chunks)
        chunk_idx += len(unit_chunks)

    return all_chunks
