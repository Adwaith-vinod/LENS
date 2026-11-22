import os
import secrets
import logging
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks, Header, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.config.settings import config, get_data_dir
from backend.discovery.system_discovery import discover_fixed_drives
from backend.storage.db import get_db
from backend.indexing.indexer import get_indexer
from backend.search.engine import get_search_engine
from backend.services.file_service import get_file_service
from backend.embeddings.engine import get_embedding_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("lens.api")


def get_auth_token() -> str:
    """Read or create the local session token."""
    token_file = get_data_dir() / ".token"
    if token_file.exists():
        try:
            tok = token_file.read_text(encoding="utf-8").strip()
            if tok:
                return tok
        except Exception:
            pass
    token = secrets.token_hex(24)
    try:
        token_file.write_text(token, encoding="utf-8")
    except Exception as e:
        logger.warning(f"Could not persist auth token: {e}")
    return token


def require_token(request: Request, x_lens_token: Optional[str] = Header(None)):
    """Security check ensuring requests to mutating endpoints possess the local session token."""
    if os.environ.get("LENS_TEST_MODE") == "1":
        return True
    expected = get_auth_token()
    token = x_lens_token or request.cookies.get("lens_token")
    if not token or not secrets.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="Unauthorized: invalid or missing X-LENS-Token")
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Preload SentenceTransformer model on server startup
    try:
        logger.info("Lifespan: preloading embedding model...")
        get_embedding_engine().get_model()
        logger.info("Lifespan: embedding model ready.")
    except Exception as e:
        logger.warning(f"Lifespan: could not preload embedding model: {e}")
    yield


app = FastAPI(
    title="LENS API",
    description="Intelligent Local File Discovery & Semantic Search API",
    version="1.0.0",
    lifespan=lifespan
)

# Restrict CORS to local desktop origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = get_db()
indexer = get_indexer()
search_engine = get_search_engine()
file_service = get_file_service()


# Pydantic Schemas
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language search query")
    category: Optional[str] = Field(None, description="Optional category filter (e.g. documents, spreadsheets)")
    top_k: int = Field(20, ge=1, le=100)
    min_score: float = Field(0.15, ge=0.0, le=1.0)


class IndexStartRequest(BaseModel):
    directories: Optional[List[str]] = Field(None, description="Custom directory paths to index")
    rescan: bool = Field(False, description="Whether to perform a full rescan")


class ConfigUpdateRequest(BaseModel):
    included_directories: Optional[List[str]] = None
    excluded_directories: Optional[List[str]] = None
    max_file_size_bytes: Optional[int] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    enable_watchdog: Optional[bool] = None
    index_structured_data: Optional[bool] = None


class OpenFileRequest(BaseModel):
    file_id: Optional[int] = None
    file_path: Optional[str] = None


@app.get("/api/health")
def health_check():
    stats = get_db().get_statistics()
    model_loaded = False
    try:
        model_loaded = get_embedding_engine().model is not None
    except Exception:
        pass
    return {
        "status": "online",
        "app": "LENS",
        "version": "1.0.0",
        "model_loaded": model_loaded,
        "model_name": "all-MiniLM-L6-v2",
        "total_files": stats["total_files"],
        "total_chunks": stats["total_chunks"]
    }


@app.get("/api/bootstrap")
def bootstrap_session(response: Response):
    """Returns local session token for authorized frontend interactions and sets session cookie."""
    token = get_auth_token()
    response.set_cookie(
        key="lens_token",
        value=token,
        httponly=False,
        samesite="lax",
        path="/"
    )
    return {
        "token": token,
        "app": "LENS",
        "version": "1.0.0"
    }


@app.get("/api/stats")
def get_stats():
    return get_db().get_statistics()


@app.get("/api/system/drives")
def get_system_drives():
    drives = discover_fixed_drives()
    return {"drives": [str(d) for d in drives]}


@app.post("/api/index/start")
def start_indexing(req: IndexStartRequest = IndexStartRequest(), _token: bool = Depends(require_token)):
    res = get_indexer().start_indexing(custom_directories=req.directories, background=True)
    return res


@app.post("/api/index/rescan")
def rescan_files(_token: bool = Depends(require_token)):
    res = get_indexer().start_indexing(background=True)
    return res


@app.post("/api/index/cancel")
def cancel_indexing(_token: bool = Depends(require_token)):
    get_indexer().cancel_indexing()
    return {"status": "cancelling", "message": "Indexing cancellation requested."}


@app.get("/api/index/status")
def get_index_status():
    return get_indexer().get_status()


@app.post("/api/search")
def search_files(req: SearchRequest):
    try:
        response = get_search_engine().search(
            query=req.query,
            category=req.category,
            top_k=req.top_k,
            min_score=req.min_score
        )
        return response
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/search/diagnostics")
def search_diagnostics(req: SearchRequest):
    try:
        return get_search_engine().search_diagnostics(
            query=req.query,
            category=req.category
        )
    except Exception as e:
        logger.error(f"Diagnostics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/files/{file_id}")
def get_file_details(file_id: int):
    rec = get_db().get_file_by_id(file_id)
    if not rec:
        raise HTTPException(status_code=404, detail="File not found")
    return rec


@app.get("/api/files/{file_id}/preview")
def get_file_preview(file_id: int):
    preview_data = get_file_service().get_file_preview(file_id)
    if not preview_data.get("success"):
        raise HTTPException(status_code=404, detail=preview_data.get("error", "Not found"))
    return preview_data


@app.post("/api/files/open")
def open_file_by_body(req: OpenFileRequest, _token: bool = Depends(require_token)):
    target = req.file_id if req.file_id is not None else req.file_path
    if not target:
        raise HTTPException(status_code=400, detail="file_id or file_path is required")
    result = get_file_service().open_file(target)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@app.post("/api/files/open-location")
def open_location_by_body(req: OpenFileRequest, _token: bool = Depends(require_token)):
    target = req.file_id if req.file_id is not None else req.file_path
    if not target:
        raise HTTPException(status_code=400, detail="file_id or file_path is required")
    result = get_file_service().open_file_location(target)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@app.post("/api/files/{file_id}/open")
def open_file_endpoint(file_id: int, _token: bool = Depends(require_token)):
    result = get_file_service().open_file(file_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@app.post("/api/files/{file_id}/open-location")
def open_location_endpoint(file_id: int, _token: bool = Depends(require_token)):
    result = get_file_service().open_file_location(file_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@app.get("/api/config")
def get_config():
    return {
        "included_directories": config.included_directories,
        "excluded_directories": config.excluded_directories,
        "max_file_size_bytes": config.max_file_size_bytes,
        "chunk_size": config.chunk_size,
        "chunk_overlap": config.chunk_overlap,
        "enable_watchdog": config.enable_watchdog,
        "index_structured_data": getattr(config, "index_structured_data", True)
    }


@app.post("/api/config")
def update_config(req: ConfigUpdateRequest, _token: bool = Depends(require_token)):
    # Validate chunk_overlap < chunk_size
    new_size = req.chunk_size if req.chunk_size is not None else config.chunk_size
    new_overlap = req.chunk_overlap if req.chunk_overlap is not None else config.chunk_overlap
    if new_overlap >= new_size:
        raise HTTPException(status_code=400, detail="chunk_overlap must be strictly less than chunk_size")

    reindex_required = False
    if req.chunk_size is not None and req.chunk_size != config.chunk_size:
        reindex_required = True
    if req.chunk_overlap is not None and req.chunk_overlap != config.chunk_overlap:
        reindex_required = True
    if req.max_file_size_bytes is not None and req.max_file_size_bytes != config.max_file_size_bytes:
        reindex_required = True
    if req.included_directories is not None and req.included_directories != config.included_directories:
        reindex_required = True
    if req.excluded_directories is not None and req.excluded_directories != config.excluded_directories:
        reindex_required = True
    if req.index_structured_data is not None and req.index_structured_data != getattr(config, "index_structured_data", True):
        reindex_required = True

    if req.included_directories is not None:
        config.included_directories = req.included_directories
    if req.excluded_directories is not None:
        config.excluded_directories = req.excluded_directories
    if req.max_file_size_bytes is not None:
        config.max_file_size_bytes = req.max_file_size_bytes
    if req.chunk_size is not None:
        config.chunk_size = req.chunk_size
    if req.chunk_overlap is not None:
        config.chunk_overlap = req.chunk_overlap
    if req.index_structured_data is not None:
        config.index_structured_data = req.index_structured_data

    # Watchdog toggle
    if req.enable_watchdog is not None and req.enable_watchdog != config.enable_watchdog:
        config.enable_watchdog = req.enable_watchdog
        try:
            from backend.indexing.monitor import get_watcher
            watcher = get_watcher()
            if config.enable_watchdog and not watcher.running:
                watcher.start()
            elif not config.enable_watchdog and watcher.running:
                watcher.stop()
        except Exception as e:
            logger.warning(f"Could not update watchdog state: {e}")

    config.save()
    return {"success": True, "reindex_required": reindex_required, "config": get_config()}


# Mount Frontend Static Files if built
from fastapi.staticfiles import StaticFiles
from pathlib import Path
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="static")

