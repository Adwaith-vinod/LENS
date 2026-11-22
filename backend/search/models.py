from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class MatchingSnippet:
    chunk_id: int
    unit_type: str
    unit_number: int
    source_info: str
    text_snippet: str
    score: float


@dataclass
class SearchResultItem:
    file_id: int
    file_name: str
    file_path: str
    extension: str
    category: str
    file_size_bytes: int
    modified_at: str
    relevance_score: float  # 0.0 - 1.0
    primary_snippet: str
    primary_source: str  # e.g. "Page 4", "Slide 2"
    matching_snippets: List[MatchingSnippet] = field(default_factory=list)
    preview_url: Optional[str] = None


@dataclass
class SearchResponse:
    query: str
    total_results: int
    results: List[SearchResultItem]
    duration_ms: float
