import time
import logging
from typing import List, Dict, Any, Optional

from backend.embeddings.engine import get_embedding_engine
from backend.storage.db import get_db
from backend.storage.vector_store import get_vector_store
from backend.search.models import SearchResultItem, MatchingSnippet, SearchResponse

logger = logging.getLogger(__name__)


class SearchEngine:
    """
    Unified semantic search engine for LENS.
    Performs vector similarity search across indexed document chunks and ranks matching files.
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

        # Generate normalized query embedding
        query_vector = self.embedding_engine.encode_query(query)

        # Search FAISS vector store
        scores, ids = self.vector_store.search(query_vector, top_k=top_k * 3)
        if len(scores) == 0 or len(scores[0]) == 0:
            duration = (time.perf_counter() - start_time) * 1000
            return SearchResponse(query=query, total_results=0, results=[], duration_ms=duration)

        score_map = {int(chunk_id): float(score) for score, chunk_id in zip(scores[0], ids[0]) if chunk_id != -1}
        embedding_ids = list(score_map.keys())

        # Retrieve chunk data from database
        chunk_records = self.db.get_chunks_by_embedding_ids(embedding_ids)

        # Group chunks by file_path
        files_map: Dict[str, Dict[str, Any]] = {}
        for chunk in chunk_records:
            f_path = chunk["file_path"]
            emb_id = chunk["embedding_id"]
            c_score = score_map.get(emb_id, 0.0)

            # Category filter if specified
            if category and chunk["category"].lower() != category.lower():
                continue

            # Min score threshold
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
            # Primary score is best chunk's cosine similarity
            # Multi-chunk boost: slightly reward files with multiple relevant sections
            boost = min(len(chunks) - 1, 3) * 0.02
            final_score = min(best_chunk["score"] + boost, 1.0)

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


_search_engine_instance = None


def get_search_engine() -> SearchEngine:
    global _search_engine_instance
    if _search_engine_instance is None:
        _search_engine_instance = SearchEngine()
    return _search_engine_instance
