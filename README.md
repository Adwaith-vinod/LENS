# LENS: AI-Powered Intelligent Local File Discovery

> **Find files by what you remember about their content, not their names.**

---

## 🌟 Overview
**LENS** is a desktop-first intelligent file discovery and semantic retrieval application. Users frequently accumulate thousands of documents, presentations, spreadsheets, and files across multiple drives and folders, eventually forgetting exact filenames or storage paths.

Traditional file search engines rely strictly on keyword or filename matching. LENS breaks this limitation by understanding natural language queries (e.g., *"Find the document containing details about database normalization"* or *"Find the presentation discussing convolutional neural networks"*) and retrieving the exact original files with citations (exact page number, slide number, spreadsheet sheet, or section).

### 🔒 100% Local-First & Privacy-Preserving
- **Local Embeddings**: Powered by local `sentence-transformers` models (`all-MiniLM-L6-v2`).
- **Local Vectors**: Indexed via `faiss-cpu` stored directly on disk (`data/lens_text.index`).
- **Local Metadata**: Managed by SQLite WAL database (`data/lens.db`).
- **Zero Cloud Leakage**: File contents and embeddings are never uploaded to any external server.
- **Untouched User Files**: LENS **never** modifies, renames, moves, or deletes your original files.

---

## 🏗️ Architecture

```
FRONTEND (React + Vite + Tailwind CSS + Lucide)
   │
   │  REST API (JSON over HTTP)
   ▼
BACKEND (FastAPI + Uvicorn)
   ├── System Discovery (Fixed drives & user directory discovery)
   ├── Recursive File Scanner (Junction/reparse-safe, excludes OS junk)
   ├── Multiformat Content Extractor (PDF, DOCX, PPTX, XLSX, XLS, CSV, JSON, XML, MD, RTF)
   ├── Source-Aware Semantic Chunker (Sentence/boundary preserving + page/slide citations)
   ├── Embedding Engine (Singleton sentence-transformers, batch-normalized)
   ├── Persistent FAISS Vector Store (IndexIDMap2 + IndexFlatIP)
   ├── SQLite Metadata Manager (Files, chunks, indexing history)
   ├── Incremental Synchronization (Detects additions/modifications/deletions)
   └── OS File Service (Opens original files & highlights in Windows Explorer)
```

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.10+** (Tested on Python 3.13)
- **Node.js 18+** & **npm**

### 1. Environment Setup
```powershell
# Clone or navigate to repository root
cd C:\Users\adwai\OneDrive\Desktop\Projects\LENS

# Activate existing virtual environment (or create one)
.\venv\Scripts\activate

# Install Python backend dependencies
pip install -r requirements.txt
```

### 2. Frontend Setup
```powershell
# Navigate to frontend and install dependencies
cd frontend
npm install

# Build production bundle (or run Vite dev server)
npm run build
```

---

## 🖥️ Running LENS

### Option A: Standalone Desktop Mode (Single Server)
FastAPI automatically serves both the backend API and the compiled React application on port 8000:
```powershell
# In project root with venv activated:
python backend/main.py
```
Open **[http://127.0.0.1:8000](http://127.0.0.1:8000)** in your browser!

### Option B: Development Mode (Hot Reloading)

**Terminal 1 — Backend API:**
```powershell
.\venv\Scripts\python.exe -m uvicorn backend.api.app:app --host 127.0.0.1 --port 8000 --reload
```

**Terminal 2 — Frontend Dev Server:**
```powershell
cd frontend
npm run dev
```
Open **[http://localhost:5173](http://localhost:5173)** in your browser!

---

## 🔍 Supported File Formats

| Category | Supported Extensions | Extraction Details |
| :--- | :--- | :--- |
| **Documents** | `.pdf`, `.docx`, `.doc`, `.txt`, `.md`, `.rtf`, `.odt` | Page-by-page extraction (PDF), headings & tables (DOCX), formatting-stripped (RTF), encodings (TXT/MD) |
| **Presentations** | `.pptx`, `.ppt`, `.odp` | Slide-by-slide extraction, shapes, speaker notes, and embedded image flags |
| **Spreadsheets** | `.xlsx`, `.xls`, `.csv`, `.ods` | Sheet names, row headers, and clean structured tabular strings |
| **Structured** | `.json`, `.xml` | Key-value hierarchy traversal and XML element text extraction |
| **Images** | `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.tiff`, `.gif` | Dimensions, formats, standalone metadata, and visual embedding pipeline |

---

## 📡 API Endpoints

- `GET  /api/health` — Service health & indexed counts
- `GET  /api/stats` — Overall metrics & files by category
- `GET  /api/system/drives` — Discovered fixed drives on the OS
- `POST /api/index/start` — Start background directory indexing
- `POST /api/index/rescan` — Trigger incremental rescan
- `GET  /api/index/status` — Live indexing progress & current file
- `POST /api/search` — Natural-language semantic query search
- `GET  /api/files/{id}` — File record details
- `GET  /api/files/{id}/preview` — Extracted chunks & snippets
- `POST /api/files/{id}/open` — Open original file in host OS
- `POST /api/files/{id}/open-location` — Highlight file in Windows Explorer
- `GET  /api/config` / `POST /api/config` — Read/update scan paths and chunk settings

---

## 🧪 Testing

Run the automated test suite covering unit tests, integration tests, and the end-to-end acceptance workflow:
```powershell
# Run all tests with pytest
.\venv\Scripts\python.exe -m pytest tests -v
```

All **27/27 tests** pass:
- Drive discovery & exclusions (M1 baseline preserved)
- Multiformat extractors (PDF, DOCX, PPTX, XLSX, JSON, TXT)
- Sentence-aware semantic chunking
- SQLite transactions & persistence
- FAISS vector index reload and ID mapping
- Natural-language semantic query search
- FastAPI REST endpoints
- Full Acceptance Criteria lifecycle (Discovery -> Ingestion -> Semantic Search -> OS Open -> Index Persistence)
