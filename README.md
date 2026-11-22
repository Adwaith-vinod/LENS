# LENS: AI-Powered Intelligent Local File Discovery

> **Find files by what you remember about their content, not their names.**

---

## 🌟 Overview

**LENS** is a desktop-first intelligent file discovery and semantic retrieval application. Users frequently accumulate thousands of documents, presentations, spreadsheets, and files across multiple drives and folders, eventually forgetting exact filenames or storage paths.

Traditional file search engines rely strictly on filename keywords or brittle substring matching. LENS breaks this limitation by understanding natural language queries (e.g., *"Find the document containing details about database normalization"* or *"Find the presentation discussing containerization and Kubernetes"*) and retrieving the exact original files with citations (exact page number, slide number, spreadsheet sheet, or section).

### 🔒 100% Local-First & Privacy-Preserving
- **Local Embeddings**: Powered by local `sentence-transformers` models (`all-MiniLM-L6-v2`).
- **Hybrid Search**: Fuses dense FAISS vector embeddings with sparse SQLite FTS5 BM25 keyword matching via Reciprocal Rank Fusion ($k=60$).
- **Local Metadata**: Managed by a SQLite database in WAL mode (`data/lens.db`) with busy timeout protection.
- **Zero Cloud Leakage**: File contents and embeddings are never sent to any external server.
- **Safe & Non-Destructive**: LENS **never** modifies, renames, moves, or deletes your original files.

---

## 🏗️ Architecture

```
FRONTEND (React + Vite + Tailwind CSS + Lucide Icons)
   │
   │  REST API (JSON over HTTP with session token authentication)
   ▼
BACKEND (FastAPI + Uvicorn)
   ├── System Discovery (Fixed drives & OneDrive-aware user folder detection)
   ├── Recursive File Scanner (Reparse-safe, honors user & system exclusions, file size caps)
   ├── Multiformat Content Extractor
   │     ├── PDF: Page-by-page extraction via PyMuPDF with OCR fallback
   │     ├── Word: Document-order traversal of paragraphs & tables (DOCX) + LibreOffice (DOC)
   │     ├── PowerPoint: Recursive group shapes, slide titles & speaker notes (PPTX / PPT)
   │     ├── Spreadsheets: Workbooks, sheet names & tabular row streams (XLSX, XLS, CSV, ODS)
   │     ├── Plain Text: Safe multi-encoding ladder with 5MB cap (TXT, MD, RTF, ODF)
   │     └── Structured: Clean JSON & XML node formatting (with lockfile filtering)
   ├── Source-Aware Semantic Chunker (Preserves sentence boundaries + citation metadata)
   ├── Embedding Engine (Singleton sentence-transformers with context-enriched headers)
   ├── Persistent FAISS Vector Store (IndexIDMap2 + IndexFlatIP with batch disk saves)
   ├── SQLite FTS5 Full-Text Search (Kept in real-time sync with chunk lifecycle)
   ├── Hybrid Search Engine (Dense + Sparse Reciprocal Rank Fusion with category & filename boosts)
   └── OS File Service (Path-validated file opening & list-form Windows Explorer reveal)
```

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.10+** (Tested on Python 3.10, 3.11, 3.12, 3.13)
- **Node.js 18+** & **npm**

### One-Click Launch

#### Windows (PowerShell)
```powershell
.\scripts\run.ps1
```

#### Linux & macOS (Bash)
```bash
./scripts/run.sh
```

The script sets up the virtual environment, installs dependencies, builds the frontend if needed, launches the server, and opens **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your default browser.

---

## 💻 Manual Setup & Development

### 1. Backend Setup
```bash
# Create and activate virtual environment
python -m venv venv

# Windows
.\venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run build
```

### 3. Running in Development Mode

**Terminal 1 — Backend (with hot-reload):**
```bash
python -m uvicorn backend.api.app:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 — Frontend (with Vite HMR):**
```bash
cd frontend
npm run dev
```
Open **[http://localhost:5173](http://localhost:5173)** in your browser.

---

## 🔍 Supported File Formats

| Category | Supported Extensions | Extraction Details |
| :--- | :--- | :--- |
| **Documents** | `.pdf`, `.docx`, `.doc`, `.txt`, `.md`, `.rtf`, `.odt` | Page-by-page PDF extraction with OCR fallback; document-order paragraphs and tables for DOCX; LibreOffice conversion for DOC; safe multi-encoding text decoding. |
| **Presentations** | `.pptx`, `.ppt`, `.odp` | Slide-by-slide extraction; recursive group shape traversal; slide titles; tables; speaker notes. |
| **Spreadsheets** | `.xlsx`, `.xls`, `.csv`, `.ods` | Worksheets, sheet names, row headers, and clean structured tabular streams. |
| **Structured** | `.json`, `.xml` | Key-value hierarchy traversal and XML element text extraction (lockfiles like `package-lock.json` and build XMLs are automatically filtered). |
| **Images** | `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.tiff`, `.gif` | Format inspection and OCR text extraction (avoids indexing generic metadata strings). |

---

## 🛠️ Maintenance & Reset Tool

To manually clear the database and vector indices and optionally trigger a full re-index:
```bash
python scripts/reset_index.py --force --reindex
```

---

## 📡 API Endpoints

| Method | Endpoint | Description | Protected |
|:---|:---|:---|:---:|
| `GET` | `/api/health` | Service health, model status, indexed counts | No |
| `GET` | `/api/bootstrap` | Handshake providing local session auth token | No |
| `GET` | `/api/stats` | Overall statistics and counts grouped by category | No |
| `GET` | `/api/system/drives` | Discovered fixed drives on the OS | No |
| `POST` | `/api/index/start` | Start background directory indexing | Yes |
| `POST` | `/api/index/rescan` | Trigger incremental rescan of files | Yes |
| `POST` | `/api/index/cancel` | Request graceful cancellation of indexing | Yes |
| `GET` | `/api/index/status` | Live indexing progress, status, and current file | No |
| `POST` | `/api/search` | Natural-language hybrid semantic query search | No |
| `POST` | `/api/search/diagnostics` | Diagnostic search breakdown (dense vs sparse ranks) | No |
| `GET` | `/api/files/{id}` | File record details from database | No |
| `GET` | `/api/files/{id}/preview` | Extracted chunks & snippets for file preview | No |
| `POST` | `/api/files/open` | Open original file in host OS default app | Yes |
| `POST` | `/api/files/open-location` | Highlight containing folder in OS file manager | Yes |
| `GET` | `/api/config` | Read current indexing paths and chunk settings | No |
| `POST` | `/api/config` | Update scan paths and chunk settings | Yes |

*Protected endpoints require the `X-LENS-Token` header retrieved via `/api/bootstrap`.*

---

## 🧪 Automated Test Suite

All tests run in total isolation from your actual `./data` folder using dynamic test directories.

```bash
pytest tests -v
```

**All 64 tests passing across 14 test suites**:
1. `tests/test_api.py` — REST endpoints, config management, and stats
2. `tests/test_chunking.py` — Semantic chunking, boundary preservation, and source label citations
3. `tests/test_correctness_fixes.py` — WAL mode, vector pruning on re-index, incremental skip of failed files, cancel endpoint
4. `tests/test_discovery.py` — Scanner traversal, junction/reparse safety, extension filters
5. `tests/test_e2e_acceptance.py` — Complete end-to-end ingestion, retrieval, and open lifecycle
6. `tests/test_eval.py` — Synthetic multiformat retrieval benchmark suite (10/10 Top-1 accuracy)
7. `tests/test_extraction.py` — Multiformat extractors (PDF, DOCX, PPTX, XLSX, JSON, TXT)
8. `tests/test_extraction_upgrades.py` — Group shapes, slide titles, DOCX natural order, UTF-16 decoding
9. `tests/test_pptx_retrieval_regression.py` — Full PowerPoint retrieval pipeline verification
10. `tests/test_search.py` — Semantic query ranking and intent category boosts
11. `tests/test_search_quality.py` — SQLite FTS5 search, embedding text enrichment, and hybrid RRF fusion
12. `tests/test_security.py` — Local CORS restriction, token auth, path validation against arbitrary execution
13. `tests/test_settings_and_cleanup.py` — Configured exclusions, junk lockfile filtering, size caps
14. `tests/test_storage.py` — SQLite connection management and FAISS index persistence

---

## ❓ Troubleshooting

### 1. SQLite Database Lock (`database is locked`)
LENS sets SQLite to **WAL (Write-Ahead Logging)** mode with `PRAGMA busy_timeout = 20000` (20 seconds) and uses deterministic connection lifecycles to prevent stale locks. If you encounter lock issues after an abnormal termination:
```bash
python scripts/reset_index.py --force
```

### 2. Legacy `.doc`, `.ppt`, `.xls` Formats
- Legacy `.doc` files utilize LibreOffice in headless mode (`soffice --headless --convert-to docx`) if installed. Ensure `soffice` or `libreoffice` is in your system `PATH`.
- Modern `.docx`, `.pptx`, `.xlsx` files are extracted natively with zero external dependencies.

### 3. Port Already in Use (`Errno 10048` or `Address already in use`)
If port 8000 is occupied by another process, launch with a custom port:
```bash
python -m uvicorn backend.api.app:app --host 127.0.0.1 --port 8080
```
