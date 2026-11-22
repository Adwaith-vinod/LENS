import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from backend.config.settings import config
from backend.discovery.file_filters import is_supported_file, should_skip_directory
from backend.discovery.scanner import scan_directory
from backend.extraction.extractors import read_text_file_safe, is_binary_content
from backend.extraction.unified import extract_file_content
from backend.api.app import app
from scripts.reset_index import reset_lens_index


def test_scanner_honors_configured_exclusions(tmp_path):
    sub = tmp_path / "custom_excluded"
    sub.mkdir()
    (sub / "doc.txt").write_text("Secret content", encoding="utf-8")

    normal_dir = tmp_path / "normal_folder"
    normal_dir.mkdir()
    (normal_dir / "doc.txt").write_text("Normal content", encoding="utf-8")

    # When custom_excluded is in config.excluded_directories
    config.excluded_directories = ["custom_excluded"]
    files = scan_directory(tmp_path)
    file_names = [f["file_name"] for f in files]
    file_paths = [f["file_path"] for f in files]

    assert any("normal_folder" in p for p in file_paths)
    assert not any("custom_excluded" in p for p in file_paths)


def test_user_dataset_folder_scanned_if_not_in_user_exclusions(tmp_path):
    dataset_dir = tmp_path / "dataset"
    dataset_dir.mkdir()
    (dataset_dir / "data.txt").write_text("Dataset content", encoding="utf-8")

    # If user removes dataset from excluded_directories
    config.excluded_directories = []
    files = scan_directory(tmp_path)
    file_paths = [f["file_path"] for f in files]
    assert any("dataset" in p for p in file_paths)


def test_junk_files_and_directories_filtered_out(tmp_path):
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")
    (tmp_path / "pom.xml").write_text("<project></project>", encoding="utf-8")
    (tmp_path / "plugin.xml").write_text("<plugin></plugin>", encoding="utf-8")
    (tmp_path / "valid.txt").write_text("Keep me", encoding="utf-8")

    meta_inf = tmp_path / "META-INF"
    meta_inf.mkdir()
    (meta_inf / "manifest.txt").write_text("Manifest", encoding="utf-8")

    files = scan_directory(tmp_path)
    names = [f["file_name"] for f in files]
    assert "package-lock.json" not in names
    assert "pom.xml" not in names
    assert "plugin.xml" not in names
    assert "manifest.txt" not in names
    assert "valid.txt" in names


def test_max_file_size_limit(tmp_path):
    large_file = tmp_path / "huge.txt"
    large_file.write_text("A" * 2000, encoding="utf-8")

    # Set cap to 1000 bytes
    config.max_file_size_bytes = 1000
    assert not is_supported_file(large_file)

    # Set cap to 5000 bytes
    config.max_file_size_bytes = 5000
    assert is_supported_file(large_file)


def test_binary_rejection_in_text_extractor(tmp_path):
    binary_file = tmp_path / "sample.bin"
    binary_file.write_bytes(b"\x00\x01\x02\x03\xFF\xFE\x00\x00" * 100)

    assert is_binary_content(binary_file.read_bytes())
    assert read_text_file_safe(binary_file) == ""


def test_image_without_ocr_yields_no_bogus_text_embedding(tmp_path):
    img = tmp_path / "blank.png"
    # Create simple 10x10 png
    from PIL import Image
    i = Image.new("RGB", (10, 10), color="white")
    i.save(str(img))

    res = extract_file_content(str(img))
    assert res.has_visual_content is True
    # Should not have fake "Image file: ... width: 10" text units
    assert len(res.content_units) == 0


def test_config_validation_and_reindex_flag():
    client = TestClient(app)

    # Invalid: chunk_overlap >= chunk_size
    res = client.post("/api/config", json={"chunk_size": 200, "chunk_overlap": 200})
    assert res.status_code == 400
    assert "strictly less than" in res.json()["detail"]

    # Valid update that triggers reindex_required
    res = client.post("/api/config", json={"chunk_size": 450, "chunk_overlap": 50})
    assert res.status_code == 200
    assert res.json()["reindex_required"] is True
    assert res.json()["config"]["chunk_size"] == 450


def test_reset_index_script():
    # Test script executes safely with --force
    reset_lens_index(reindex=False, force=True)
    from backend.storage.db import get_db
    db = get_db()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM files")
        count = cursor.fetchone()[0]
    assert count == 0
