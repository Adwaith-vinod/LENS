import time
import re
import logging
from typing import List, Dict, Any, Optional

from backend.embeddings.engine import get_embedding_engine
from backend.storage.db import get_db
from backend.storage.vector_store import get_vector_store
from backend.search.models import SearchResultItem, MatchingSnippet, SearchResponse

logger = logging.getLogger(__name__)

# Intent keyword registry mapping to supported categories
INTENT_KEYWORDS = {
    "presentations": [
        "presentation", "presentations", "ppt", "pptx", "slide", "slides",
        "powerpoint", "slide deck", "deck"
    ],
    "spreadsheets": [
        "spreadsheet", "spreadsheets", "excel", "sheet", "sheets", "csv",
        "workbook", "workbooks", "xlsx", "xls"
    ],
    "documents": [
        "document", "documents", "doc", "docx", "pdf", "report", "paper",
        "article", "notes", "txt", "text file"
    ],
    "images": [
        "image", "images", "photo", "photos", "picture", "pictures",
        "png", "jpg", "jpeg", "diagram"
    ]
}


def detect_query_intent(query: str) -> Optional[str]:
    """
    Detect explicit file-type or category intent from the natural language query.
    For example: 'find me the presentation file about docker and kubernetes' -> 'presentations'.
    """
    lower_query = f" {query.lower()} "
    for category, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            # Match whole words or phrases
            pattern = r'\b' + re.escape(kw) + r'\b'
            if re.search(pattern, lower_query):
                return category
    return None


def extract_keywords(query: str) -> List[str]:
    """Extract significant keywords from a search query, stripping conversational filler."""
    stopwords = {
        "find", "me", "the", "a", "an", "about", "file", "files", "document",
        "presentation", "spreadsheet", "image", "containing", "where", "i",
        "wrote", "discussing", "details", "information", "with", "for", "in",
        "on", "at", "to", "and", "or", "of", "is", "are", "show", "get"
    }
    words = re.findall(r'[a-zA-Z0-9_\-\.]+', query.lower())
    return [w for w in words if w not in stopwords and len(w) >= 3]


class SearchEngine:
    """
    Unified semantic search engine for LENS.
    Performs vector similarity search across indexed document chunks and ranks matching files
    using content relevance, multi-chunk support, filename signals, and user intent.
    """

    def __init__(self):
        self.db = get_db()
        self.vector_store = get_vector_store()
        self.embedding_engine = get_embedding_engine()

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        top_k: int = 20,
        min_score: float = 0.15
    ) -> SearchResponse:
        start_time = time.perf_counter()
        query = query.strip()
        if not query:
            return SearchResponse(query="", total_results=0, results=[], duration_ms=0.0)

        # Detect user intent (e.g. asking for a presentation, spreadsheet, etc.)
        detected_intent = detect_query_intent(query)
        effective_category = category or (detected_intent if category else None)
        query_keywords = extract_keywords(query)

        # 1. Retrieve Dense Candidates from FAISS (top 50)
        query_vector = self.embedding_engine.encode_query(query)
        dense_scores_raw, dense_ids_raw = self.vector_store.search(query_vector, top_k=50)

        dense_ranks: Dict[int, int] = {}
        dense_scores: Dict[int, float] = {}
        if len(dense_scores_raw) > 0 and len(dense_scores_raw[0]) > 0:
            for rank_idx, (score, chunk_id) in enumerate(zip(dense_scores_raw[0], dense_ids_raw[0]), start=1):
                if chunk_id != -1:
                    cid = int(chunk_id)
                    dense_ranks[cid] = rank_idx
                    dense_scores[cid] = float(score)

        # 2. Retrieve Sparse Candidates from SQLite FTS5 (top 50)
        fts_matches = self.db.search_fts(query, limit=50)
        sparse_ranks: Dict[int, int] = {}
        for rank_idx, match in enumerate(fts_matches, start=1):
            sparse_ranks[match["chunk_id"]] = rank_idx

        # 3. Reciprocal Rank Fusion (k=60)
        candidate_ids = set(dense_ranks.keys()) | set(sparse_ranks.keys())
        if not candidate_ids:
            duration = (time.perf_counter() - start_time) * 1000
            return SearchResponse(query=query, total_results=0, results=[], duration_ms=duration)

        score_map: Dict[int, float] = {}
        max_rrf = 2.0 / 61.0  # max theoretical RRF score for k=60 across 2 lists
        for cid in candidate_ids:
            rrf = 0.0
            if cid in dense_ranks:
                rrf += 1.0 / (60.0 + dense_ranks[cid])
            if cid in sparse_ranks:
                rrf += 1.0 / (60.0 + sparse_ranks[cid])

            rrf_norm = min(rrf / max_rrf, 1.0)
            if cid in dense_scores:
                dense_cos = max(dense_scores[cid], 0.0)
                # Dense similarity carries baseline; RRF rank provides boost
                fused = 0.65 * dense_cos + 0.35 * rrf_norm
            else:
                # Sparse keyword only match
                fused = 0.45 * rrf_norm + 0.20

            score_map[cid] = round(fused, 4)

        # 4. Retrieve chunk data from database
        chunk_records = self.db.get_chunks_by_ids(list(candidate_ids))

        # Group chunks by file_path
        files_map: Dict[str, Dict[str, Any]] = {}
        for chunk in chunk_records:
            f_path = chunk["file_path"]
            cid = chunk["id"]
            c_score = score_map.get(cid, 0.0)

            # Strict category filter if user clicked a specific category tab
            if category and chunk["category"].lower() != category.lower():
                continue

            # Minimum score threshold
            if c_score < min_score:
                continue

            if f_path not in files_map:
                files_map[f_path] = {
                    "file_id": chunk["file_id"],
                    "file_name": chunk["file_name"],
                    "file_path": f_path,
                    "extension": chunk["extension"],
                    "category": chunk["category"],
                    "file_size_bytes": chunk["file_size_bytes"],
                    "modified_at": chunk["modified_at"],
                    "chunks": []
                }

            files_map[f_path]["chunks"].append({
                "chunk_id": chunk["id"],
                "unit_type": chunk["unit_type"],
                "unit_number": chunk["unit_number"],
                "source_info": chunk["source_info"] or f"{chunk['unit_type']} {chunk['unit_number']}",
                "text": chunk["chunk_text"],
                "score": c_score
            })

        # Score aggregation and ranking
        results: List[SearchResultItem] = []
        for f_path, f_data in files_map.items():
            chunks = sorted(f_data["chunks"], key=lambda c: c["score"], reverse=True)
            if not chunks:
                continue

            best_chunk = chunks[0]
            base_score = best_chunk["score"]

            # 1. Multi-chunk contextual boost (up to +0.06)
            multi_chunk_boost = min(len(chunks) - 1, 3) * 0.02

            # 2. Filename keyword match bonus (up to +0.08)
            f_name_lower = f_data["file_name"].lower()
            keyword_matches = sum(1 for kw in query_keywords if kw in f_name_lower)
            filename_boost = min(keyword_matches * 0.04, 0.08)

            # 3. Intent category alignment boost
            # If user explicitly asked for a presentation and this file is a presentation with solid content relevance
            intent_boost = 0.0
            if detected_intent and f_data["category"].lower() == detected_intent.lower() and base_score >= 0.25:
                intent_boost = 0.12

            final_score = min(base_score + multi_chunk_boost + filename_boost + intent_boost, 1.0)

            matching_snippets = [
                MatchingSnippet(
                    chunk_id=c["chunk_id"],
                    unit_type=c["unit_type"],
                    unit_number=c["unit_number"],
                    source_info=c["source_info"],
                    text_snippet=c["text"][:300] + ("..." if len(c["text"]) > 300 else ""),
                    score=round(c["score"], 4)
                )
                for c in chunks[:3]
            ]

            results.append(SearchResultItem(
                file_id=f_data["file_id"],
                file_name=f_data["file_name"],
                file_path=f_data["file_path"],
                extension=f_data["extension"],
                category=f_data["category"],
                file_size_bytes=f_data["file_size_bytes"],
                modified_at=f_data["modified_at"],
                relevance_score=round(final_score, 4),
                primary_snippet=best_chunk["text"][:350] + ("..." if len(best_chunk["text"]) > 350 else ""),
                primary_source=best_chunk["source_info"],
                matching_snippets=matching_snippets,
                preview_url=f"/api/files/{f_data['file_id']}/preview"
            ))

        # Sort files by relevance score descending
        results.sort(key=lambda item: item.relevance_score, reverse=True)
        results = results[:top_k]

        duration = (time.perf_counter() - start_time) * 1000
        return SearchResponse(
            query=query,
            total_results=len(results),
            results=results,
            duration_ms=round(duration, 2)
        )

    def search_diagnostics(self, query: str, category: Optional[str] = None) -> Dict[str, Any]:
        """
        Step 9 Diagnostic Mode: Provides full retrieval pipeline diagnostics for debugging.
        """
        start_time = time.perf_counter()
        detected_intent = detect_query_intent(query)
        keywords = extract_keywords(query)
        stats = self.db.get_statistics()

        query_vector = self.embedding_engine.encode_query(query)
        scores, ids = self.vector_store.search(query_vector, top_k=150)
        raw_candidates_count = len(scores[0]) if len(scores) > 0 else 0

        search_res = self.search(query=query, category=category, top_k=20)
        duration = (time.perf_counter() - start_time) * 1000

        return {
            "query": query,
            "detected_intent": detected_intent,
            "extracted_keywords": keywords,
            "total_indexed_files": stats["total_files"],
            "total_indexed_chunks": stats["total_chunks"],
            "files_by_category": stats.get("categories", {}),
            "faiss_candidates_retrieved": raw_candidates_count,
            "final_results_count": search_res.total_results,
            "top_matching_files": [
                {
                    "rank": idx + 1,
                    "file_name": r.file_name,
                    "category": r.category,
                    "relevance_score": r.relevance_score,
                    "primary_source": r.primary_source,
                    "file_path": r.file_path
                }
                for idx, r in enumerate(search_res.results[:10])
            ],
            "duration_ms": round(duration, 2)
        }


_search_engine_instance = None


def get_search_engine() -> SearchEngine:
    global _search_engine_instance
    if _search_engine_instance is None:
        _search_engine_instance = SearchEngine()
    return _search_engine_instance


def reset_search_engine():
    global _search_engine_instance
    _search_engine_instance = None
