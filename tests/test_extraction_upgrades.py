import pytest
from pathlib import Path

from backend.extraction.extractors import (
    extract_docx,
    extract_pptx,
    read_text_file_safe
)


def test_pptx_title_and_group_shape_extraction(tmp_path):
    from pptx import Presentation
    from pptx.util import Inches

    prs = Presentation()
    # Slide with title
    slide = prs.slides.add_slide(prs.slide_layouts[0])
    slide.shapes.title.text = "Microservices Architecture 2026"

    # Add a normal shape
    txBox = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(2), Inches(1))
    tf = txBox.text_frame
    tf.text = "Service mesh and sidecar proxies"

    pptx_path = tmp_path / "test_group.pptx"
    prs.save(str(pptx_path))

    units = extract_pptx(pptx_path)
    assert len(units) >= 1
    slide_text = units[0].text
    assert "Title: Microservices Architecture 2026" in slide_text
    assert "Service mesh and sidecar proxies" in slide_text
    assert units[0].metadata.get("slide_title") == "Microservices Architecture 2026"


def test_docx_document_order_traversal(tmp_path):
    from docx import Document

    doc = Document()
    doc.add_paragraph("Paragraph Alpha: Introduction to databases.")
    table = doc.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text = "Header1"
    table.rows[0].cells[1].text = "Header2"
    table.rows[1].cells[0].text = "Val1"
    table.rows[1].cells[1].text = "Val2"
    doc.add_paragraph("Paragraph Omega: Summary and conclusion.")

    docx_path = tmp_path / "ordered.docx"
    doc.save(str(docx_path))

    units = extract_docx(docx_path)
    assert len(units) >= 1
    full_text = "\n".join(u.text for u in units)

    # Verify document order: Alpha -> Table -> Omega
    alpha_idx = full_text.find("Paragraph Alpha")
    table_idx = full_text.find("Header1 | Header2")
    omega_idx = full_text.find("Paragraph Omega")

    assert alpha_idx != -1
    assert table_idx != -1
    assert omega_idx != -1
    assert alpha_idx < table_idx < omega_idx


def test_text_decoding_multi_encoding_and_cap(tmp_path):
    # Test UTF-16LE file
    utf16_file = tmp_path / "utf16.txt"
    utf16_content = "Special UTF-16 content with symbols € and äöü."
    utf16_file.write_bytes(utf16_content.encode("utf-16-le"))

    extracted = read_text_file_safe(utf16_file)
    assert "Special UTF-16 content" in extracted

    # Test file larger than 5MB gets capped
    large_file = tmp_path / "oversize.txt"
    # Write 6MB of ascii
    chunk = b"Hello world repeated line!\n" * 100
    with open(large_file, "wb") as f:
        for _ in range(3000):  # ~7.8 MB
            f.write(chunk)

    capped_text = read_text_file_safe(large_file)
    assert len(capped_text.encode("utf-8")) <= 5 * 1024 * 1024 + 1000
