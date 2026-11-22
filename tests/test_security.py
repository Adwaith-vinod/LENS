import os
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.config.settings import config, get_data_dir
from backend.storage.db import get_db
from backend.services.file_service import get_file_service
from backend.api.app import app, get_auth_token


def test_cors_origins_restricted():
    # CORS middleware inspects allowed origins
    for middleware in app.user_middleware:
        if "CORSMiddleware" in str(middleware):
            origins = middleware.kwargs.get("allow_origins", [])
            assert "*" not in origins
            assert any("127.0.0.1" in o or "localhost" in o for o in origins)


def test_token_auth_protection(monkeypatch):
    client = TestClient(app)

    # Disable test mode bypass
    monkeypatch.delenv("LENS_TEST_MODE", raising=False)

    # Bootstrap endpoint is accessible without token
    res = client.get("/api/bootstrap")
    assert res.status_code == 200
    token = res.json()["token"]
    assert len(token) > 20

    # Request to mutating route without token fails with 401
    res = client.post("/api/index/cancel")
    assert res.status_code == 401
    assert "Unauthorized" in res.json()["detail"]

    # Request with invalid token fails with 401
    res = client.post("/api/index/cancel", headers={"X-LENS-Token": "invalid-token-1234"})
    assert res.status_code == 401

    # Request with valid token succeeds
    res = client.post("/api/index/cancel", headers={"X-LENS-Token": token})
    assert res.status_code == 200


def test_arbitrary_file_execution_prevention(tmp_path):
    client = TestClient(app)
    file_service = get_file_service()

    # Create an arbitrary file outside configured search directories
    outside_dir = tmp_path / "outside_root"
    outside_dir.mkdir()
    outside_file = outside_dir / "calc.exe"
    outside_file.write_text("dummy binary", encoding="utf-8")

    # Ensure outside_dir is NOT in config.included_directories
    config.included_directories = [str(tmp_path / "allowed_root")]

    # Attempt to open outside file directly
    res = file_service.open_file(str(outside_file))
    assert res["success"] is False
    assert "outside configured search paths" in res["error"] or "Access denied" in res["error"]

    # Attempt to open location of outside file directly
    res = file_service.open_file_location(str(outside_file))
    assert res["success"] is False
    assert "outside configured search paths" in res["error"] or "Access denied" in res["error"]
