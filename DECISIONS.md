# Architectural & Engineering Decisions (DECISIONS.md)

This log records design decisions, trade-offs, and disambiguations made during development.

---

### D1: Test Isolation Strategy (`LENS_DATA_DIR`)
- **Context**: Checklist item T1 requires tests to never modify or write to `./data` (such as `data/lens.db` or `data/config.json`).
- **Decision**: Read `LENS_DATA_DIR` from `os.environ` in `backend/config/settings.py`. If set, all persistence (SQLite, FAISS, config, previews) points to that directory. In `tests/conftest.py`, an autouse fixture creates an isolated temporary directory per session/test, protecting `./data`.

### D2: Legacy Root Files (`T3`)
- **Context**: The root of `backend/` had older prototype scripts (`indexer.py`, `scanner.py`, `similiarity.py`, `chunker.py`, `embedder.py`, `vector_store.py`, `text_extractor.py`).
- **Decision**: Verified that all modern production code uses the package structure (`backend.indexing`, `backend.extraction`, `backend.processing`, `backend.embeddings`, `backend.storage`, `backend.search`). Deprecated root prototype scripts were audited: anything not imported by external harnesses is cleaned up safely, while keeping all modern modular packages intact.

### D3: Structured Data (.json / .xml) Indexing Default
- **Context**: Checklist item S3 calls for structured data (.json/.xml) to be opt-in, as codebases and package managers generate thousands of JSON/XML files (e.g. `package-lock.json`).
- **Decision**: Add `index_structured_data: bool = False` to `LensConfig`. When false, `.json` and `.xml` are skipped during scanning. The UI Settings view exposes a toggle to enable it when explicitly desired.

### D4: Hybrid Search Fusion (RRF vs Weighted Sum)
- **Context**: Checklist item Q2 requires combining SQLite FTS5 BM25 with FAISS vector similarity.
- **Decision**: Use standard Reciprocal Rank Fusion (RRF) with constant $k=60$: $\text{score} = \frac{w_{\text{vec}}}{60 + r_{\text{vec}}} + \frac{w_{\text{fts}}}{60 + r_{\text{fts}}}$. This is robust against score distribution differences between cosine similarity and BM25.

### D5: Local API Authentication (`X-LENS-Token`)
- **Context**: Checklist item X2 requires an API token protecting `/api` routes (except `/api/health`).
- **Decision**: When backend starts, it generates a cryptographically secure random token in `DATA_DIR / ".token"` (if not already present). It exposes `/api/bootstrap` accessible only from same-origin localhost, which hands the token to the local React frontend. Frontend sends `X-LENS-Token` in API headers. Test clients automatically supply this token via fixtures.
