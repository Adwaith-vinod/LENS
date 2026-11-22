# Changelog

All notable changes to the LENS project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-11-22

### Added
- **Hybrid Search Engine**: Fuses dense vector similarity from FAISS with sparse BM25 keyword matching from SQLite FTS5 using Reciprocal Rank Fusion ($k=60$), delivering exact-token matching for identifiers and error codes while retaining semantic understanding.
- **SQLite FTS5 Full-Text Search**: Added `chunks_fts` virtual table kept in real-time synchronization with chunk insertion, modification, and file deletion.
- **Context-Enriched Embedding Text**: Prepended `{file_name} | {source_info} | ` to chunk texts for embedding generation, boosting title-to-topic association without polluting display snippets.
- **FastAPI Lifespan Preloading**: Preloads the `sentence-transformers` model during application startup, exposing `model_loaded` and `model_name` in `/api/health`.
- **Desktop Security Hardening**:
  - Restricted CORS from wildcard `*` to local desktop origins (`http://127.0.0.1:8000`, `http://localhost:5173`, etc.).
  - Added session token authentication (`X-LENS-Token`) with local handshake endpoint `/api/bootstrap`.
  - Added path containment and existence checks to prevent arbitrary file execution via `/api/files/open`.
  - Replaced shell string invocation of Windows Explorer with safe list-form arguments (`["explorer.exe", f"/select,{path}"]`).
- **Enhanced Extraction Pipeline**:
  - Recursive shape traversal for PPTX group shapes (`MSO_SHAPE_TYPE.GROUP`).
  - Explicit slide title extraction and prioritization for PowerPoint presentations.
  - Document-order XML body element traversal for DOCX files (interleaving paragraphs and tables in natural reading order) plus header/footer extraction.
  - Multi-encoding decoding ladder (UTF-8, UTF-8-sig, CP1252, ISO-8859-1, Latin-1, UTF-16) with NUL-byte binary rejection and a 5MB per-file cap.
  - PyMuPDF OCR fallback support for scanned PDF pages.
  - Binary rejection in plain-text fallback, and LibreOffice `soffice` conversion fallback for legacy `.doc` files.
- **Settings & Index Hygiene**:
  - Dynamic user-configured exclusions and file size limits in scanner.
  - Filtering for junk build descriptors (`package-lock.json`, `pom.xml`, `plugin.xml`, `build.xml`, `.metadata`, `META-INF`).
  - API validation ensuring `chunk_overlap < chunk_size` with `reindex_required: True` reporting.
  - Graceful cancellation endpoint `POST /api/index/cancel` with UI integration.
  - Database WAL mode (`PRAGMA journal_mode = WAL`) and busy timeout (`PRAGMA busy_timeout = 20000`).
  - Pruning of obsolete FAISS vector IDs upon re-indexing modified files.
  - Incremental scanning skip for unchanged files with status `"failed"`, `"empty"`, or `"unsupported"`.
  - Content hashing (SHA-256) and indexing run history logging in `indexing_runs`.
- **Scripts & Developer Tooling**:
  - `scripts/reset_index.py`: CLI tool for manual index and database reset.
  - `scripts/run.ps1` & `scripts/run.sh`: One-click startup scripts for Windows and Unix.
  - `.github/workflows/ci.yml`: GitHub Actions CI running pytest across Ubuntu and Windows.
  - `requirements-dev.txt`: Dedicated test dependencies (`pytest`, `httpx`).

### Changed
- **Test Isolation**: Added `tests/conftest.py` autouse fixture routing `LENS_DATA_DIR` to a temporary directory, ensuring tests never read, write, or corrupt the user's real `./data` folder.
- **Frontend Enhancements**:
  - Replaced raw cosine percentage displays with qualitative confidence badges (`Best Match`, `Strong Match`, `Possible Match`).
  - Added Cancel Indexing button in the dashboard.
  - Fixed category filter race condition by passing category directly to search handler without `setTimeout`.
  - Added search request sequence IDs to prevent stale search responses from overwriting newer queries.
  - Rebuilt production frontend assets in `frontend/dist`.

### Removed
- Archived legacy prototype root files (`backend/chunker.py`, `backend/embedder.py`, `backend/indexer.py`, `backend/scanner.py`, `backend/similiarity.py`, `backend/text_extractor.py`, `backend/vector_store.py`) to `legacy_archive/`.
