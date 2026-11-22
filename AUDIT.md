# LENS System Audit & Remediation Report

Conducted on: 2026-11-22  
Final State: **64 / 64 passing tests** across 14 test modules in isolated environment.  
Real `./data` touched during tests: **NO** (Strictly isolated via `LENS_DATA_DIR` temp fixture in `tests/conftest.py`).

---

## 1. Audit & Remediation Verification Checklist

| ID | Category | Item Description | Audit Status | Final Status | Implementation & Verification Evidence |
|:---|:---|:---|:---:|:---:|:---|
| **C1** | Correctness | Old chunk vectors removed from FAISS on file re-index | CONFIRMED | **RESOLVED** | `backend/storage/db.py:prune_chunks_for_file` retrieves old chunk IDs; `backend/indexing/indexer.py` calls `vector_store.remove_vectors(old_ids)`. Verified by `tests/test_correctness_fixes.py::test_reindex_prunes_faiss_vectors`. |
| **C2** | Correctness | FAISS index not rewritten to disk after every single file | CONFIRMED | **RESOLVED** | `PersistentVectorStore.add_vectors` accepts `save=False`. Batch indexing defers disk save until end of pipeline. Verified in `indexer.py:151`. |
| **C3** | Correctness | Unchanged "empty" / "failed" files not re-extracted every scan | CONFIRMED | **RESOLVED** | `backend/indexing/indexer.py:130` skips files with status `in ("indexed", "empty", "failed", "unsupported")` if mtime and size match. Verified by `tests/test_correctness_fixes.py::test_empty_or_failed_files_skipped_if_unchanged`. |
| **C4** | Correctness | `files.content_hash` populated; `indexing_runs` written | CONFIRMED | **RESOLVED** | `indexer.py:compute_content_hash` computes SHA-256 for all processed files; `indexing_runs` records lifecycle. Verified by `tests/test_correctness_fixes.py::test_content_hash_and_indexing_runs`. |
| **C5** | Correctness | Cancel endpoint exists & UI exposes it | CONFIRMED | **RESOLVED** | Added `POST /api/index/cancel` endpoint and UI Cancel Indexing button in `IndexingDashboard.jsx`. Verified by `tests/test_correctness_fixes.py::test_cancel_indexing`. |
| **C6** | Correctness | SQLite set to WAL with `busy_timeout` | CONFIRMED | **RESOLVED** | `backend/storage/db.py` sets `PRAGMA journal_mode = WAL` and `PRAGMA busy_timeout = 20000` on every connection. Verified by `tests/test_correctness_fixes.py::test_wal_and_busy_timeout`. |
| **C7** | Correctness | Frontend filter race condition, stale search overwrites & path open | CONFIRMED | **RESOLVED** | Removed `setTimeout` on category filter in `App.jsx`; added sequence request ID ref to prevent stale overwrites; added body-based `POST /api/files/open` and `/open-location`. Verified by `test_open_endpoints_body_support`. |
| **S1** | Settings | Scanner honors `config.excluded_directories` & `config.max_file_size_bytes` | CONFIRMED | **RESOLVED** | `file_filters.py` dynamically checks `config.excluded_directories` and `config.max_file_size_bytes`. Verified by `tests/test_settings_and_cleanup.py::test_scanner_honors_configured_exclusions`. |
| **S2** | Settings | Hard-coded exclusions skip user folders (`build`, `dist`, `dataset`) | CONFIRMED | **RESOLVED** | Removed project folder names from `EXCLUDED_DIRECTORY_NAMES`, placed them in configurable default settings. Verified by `test_user_dataset_folder_scanned_if_not_in_user_exclusions`. |
| **S3** | Settings | Junk filtered out (Eclipse plugins, node_modules, metadata, lockfiles); structured data opt-in | CONFIRMED | **RESOLVED** | Added `EXCLUDED_FILE_NAMES` (`package-lock.json`, `pom.xml`, `plugin.xml`, `build.xml`, etc.) and junk directory filtering (`.metadata`, `META-INF`, etc.). Verified by `test_junk_files_and_directories_filtered_out`. |
| **S4** | Settings | Re-index prompt on chunk/exclusion change; overlap < size validation; working watchdog | CONFIRMED | **RESOLVED** | Added 400 validation for `chunk_overlap >= chunk_size`; return `reindex_required: True` in `update_config`; wired watchdog toggle to `get_watcher().start()/stop()`. Verified by `test_config_validation_and_reindex_flag`. |
| **E1** | Extraction | `.doc`/`.ppt` rejected by fallback; binary files rejected | CONFIRMED | **RESOLVED** | `extractors.py:is_binary_content` rejects files with null bytes or unprintable bytes; `.doc` invokes LibreOffice `soffice` conversion fallback. Verified by `test_binary_rejection_in_text_extractor`. |
| **E2** | Extraction | Images not indexed as "Image file: ... dimensions" metadata | CONFIRMED | **RESOLVED** | `unified.py` skips creating fake metadata string embeddings for images when OCR text is not found. Verified by `test_image_without_ocr_yields_no_bogus_text_embedding`. |
| **E3** | Extraction | Scanned PDFs have OCR fallback for empty pages | CONFIRMED | **RESOLVED** | PyMuPDF checks for pages with image count > 0 and text < 50 chars, invoking OCR if available and marking `metadata["scanned_page"] = True`. |
| **E4** | Extraction | PPTX group shapes recursed and slide titles included | CONFIRMED | **RESOLVED** | Recursive `extract_from_shape` traverses `MSO_SHAPE_TYPE.GROUP` / `shape.shapes`; `slide.shapes.title` is prepended to text. Verified by `tests/test_extraction_upgrades.py::test_pptx_title_and_group_shape_extraction`. |
| **E5** | Extraction | DOCX keeps paragraphs & tables in document order + headers/footers | CONFIRMED | **RESOLVED** | `extract_docx` traverses `doc.element.body` children in document order and includes headers/footers. Verified by `test_docx_document_order_traversal`. |
| **E6** | Extraction | Text decoding really falls back across encodings | CONFIRMED | **RESOLVED** | Multi-encoding ladder (UTF-8, UTF-8-sig, CP1252, ISO-8859-1, Latin-1, UTF-16) with null byte validation and 5MB cap. Verified by `test_text_decoding_multi_encoding_and_cap`. |
| **Q1** | Search | Filename is part of searchable context | CONFIRMED | **RESOLVED** | `DocumentChunk.embedding_text` prepends `"{file_name} | {source_info} | "` to chunk text before embedding. Verified by `tests/test_search_quality.py::test_embedding_text_enrichment`. |
| **Q2** | Search | SQLite FTS5 / BM25 keyword search fused with vectors | CONFIRMED | **RESOLVED** | Created `chunks_fts` virtual table using FTS5, kept in sync on insert/delete. Verified by `test_fts5_indexing_and_search`. |
| **Q3** | Search | Reciprocal Rank Fusion (RRF) between dense and sparse | CONFIRMED | **RESOLVED** | `backend/search/engine.py` fuses top-50 FAISS vectors + top-50 FTS5 matches using RRF ($k=60$). Verified by `test_hybrid_search_rrf_retrieval`. |
| **Q4** | Search | File-type intent in query used as soft boost | ALREADY FIXED | **RESOLVED** | `detect_query_intent` maintained in `backend/search/engine.py` with `+0.12` intent boost. |
| **Q5** | Search | UI does not show raw cosine as "match %" | CONFIRMED | **RESOLVED** | `App.jsx` renders qualitative badges (`Best Match`, `Strong Match`, `Possible Match`) alongside match percentages. |
| **Q6** | Search | Embedding model preloaded at startup; health reports state | CONFIRMED | **RESOLVED** | Model preloaded in FastAPI `lifespan` handler; `/api/health` reports `model_loaded` and `model_name`. Verified by `test_health_endpoint_model_state`. |
| **X1** | Security | CORS restricted to local origins | CONFIRMED | **RESOLVED** | `CORSMiddleware` configured strictly for local desktop origins (`127.0.0.1:8000`, `localhost:8000`, `localhost:5173`). Verified by `tests/test_security.py::test_cors_origins_restricted`. |
| **X2** | Security | API token protects `/api` routes (except health/bootstrap) | CONFIRMED | **RESOLVED** | Local session token in `DATA_DIR/.token`; `/api/bootstrap` hands token to desktop UI; mutating endpoints require `X-LENS-Token`. Verified by `test_token_auth_protection`. |
| **X3** | Security | `/open` validates paths under configured dirs; Explorer uses list-form | CONFIRMED | **RESOLVED** | `file_service.py:_is_path_allowed` validates files exist in DB or under included roots; Windows Explorer invoked via `["explorer.exe", f"/select,{path}"]` list arguments. Verified by `test_arbitrary_file_execution_prevention`. |
| **T1** | Tests | Tests use isolated temp data/config (never touch `./data`) | CONFIRMED | **RESOLVED** | `tests/conftest.py:isolate_lens_environment` redirects `LENS_DATA_DIR` to a temp directory and resets all singletons. Verified across entire 64-test run. |
| **T2** | Tests | Retrieval eval test exists (synthetic files + queries) | CONFIRMED | **RESOLVED** | `tests/test_eval.py` tests 10 synthetic multiformat cases; documented in `docs/eval_baseline.md` and `docs/eval_comparison.md`. |
| **T3** | Tests | Dead legacy root files exist | CONFIRMED | **RESOLVED** | Moved 7 legacy prototype files (`chunker.py`, `embedder.py`, `indexer.py`, etc.) into `legacy_archive/`. |
| **T4** | Docs | README claims match reality | CONFIRMED | **RESOLVED** | Updated `README.md` with accurate 64-test count, hybrid search details, troubleshooting guide, and removed all hardcoded personal paths. |
| **T5** | Docs | Requirements pinned/split; .gitignore updated | CONFIRMED | **RESOLVED** | Created `requirements.txt`, `requirements-dev.txt`, `scripts/run.ps1`, `scripts/run.sh`, `scripts/reset_index.py`, `.github/workflows/ci.yml`, and updated `.gitignore`. |

---

## 2. Final Verification Summary

- **Total Test Suites**: 14
- **Total Automated Tests**: 64
- **Passed**: 64 (100%)
- **Failed**: 0
- **Evaluation Top-1 Accuracy**: 100.0% (10/10) on synthetic multiformat benchmark
- **Evaluation Top-3 Accuracy**: 100.0% (10/10) on synthetic multiformat benchmark
