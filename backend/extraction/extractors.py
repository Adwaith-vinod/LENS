import os
import csv
import json
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional

from backend.extraction.models import ContentUnit, ExtractionResult

logger = logging.getLogger(__name__)


def is_binary_content(raw_bytes: bytes) -> bool:
    """
    Detect if binary bytes are present, allowing UTF-16 text.
    """
    if not raw_bytes:
        return False
    # Check for standard Unicode BOMs
    if raw_bytes.startswith((b"\xff\xfe", b"\xfe\xff", b"\xef\xbb\xbf")):
        return False

    sample = raw_bytes[:4096]
    # Check if it looks like UTF-16 text without BOM (alternating NUL bytes)
    if len(sample) >= 4:
        even_zeros = sum(1 for b in sample[0::2] if b == 0)
        odd_zeros = sum(1 for b in sample[1::2] if b == 0)
        if odd_zeros > len(sample) * 0.35 or even_zeros > len(sample) * 0.35:
            # Alternating nulls indicate UTF-16 text stream
            return False

    if b"\x00" in sample:
        return True

    text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7F})
    non_text = sample.translate(None, text_chars)
    return (len(non_text) / max(len(sample), 1)) > 0.30


def read_text_file_safe(path: Path) -> str:
    """
    Read a text file safely; caps read at 5MB and rejects binary content.
    Uses a strict multi-encoding ladder with charset-normalizer fallback.
    """
    MAX_TEXT_BYTES = 5 * 1024 * 1024  # 5MB cap
    try:
        with open(path, "rb") as f:
            raw_bytes = f.read(MAX_TEXT_BYTES)
            if is_binary_content(raw_bytes):
                return ""
    except Exception as e:
        logger.debug(f"Could not read bytes from {path}: {e}")
        return ""

    # If BOM or null bytes indicate UTF-16, try UTF-16 encodings first
    if raw_bytes.startswith((b"\xff\xfe", b"\xfe\xff")) or b"\x00" in raw_bytes[:512]:
        encodings = ["utf-16", "utf-16-le", "utf-16-be", "utf-8", "cp1252", "latin-1"]
    else:
        encodings = ["utf-8", "utf-8-sig", "cp1252", "iso-8859-1", "latin-1"]

    for enc in encodings:
        try:
            decoded = raw_bytes.decode(enc)
            # If the decoded text contains NUL characters, it wasn't a valid single-byte text decode
            if "\x00" in decoded[:1024]:
                continue
            return decoded
        except (UnicodeDecodeError, LookupError):
            continue

    # Try charset_normalizer if installed
    try:
        import charset_normalizer
        match = charset_normalizer.from_bytes(raw_bytes).best()
        if match:
            return str(match)
    except Exception:
        pass

    return raw_bytes.decode("utf-8", errors="replace")


def extract_pdf(path: Path) -> List[ContentUnit]:
    """Extract PDF page-by-page using PyMuPDF with OCR fallback for scanned pages."""
    import pymupdf
    units = []
    doc = pymupdf.open(str(path))
    try:
        for page_idx, page in enumerate(doc):
            text = (page.get_text() or "").strip()
            images = page.get_images()
            metadata = {
                "page_index": page_idx,
                "has_images": len(images) > 0,
                "image_count": len(images)
            }

            # OCR fallback for scanned pages with minimal or no text
            if len(text) < 50 and len(images) > 0:
                metadata["scanned_page"] = True
                try:
                    import pytesseract
                    from PIL import Image
                    import io
                    pix = page.get_pixmap(dpi=150)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    ocr_text = pytesseract.image_to_string(img).strip()
                    if ocr_text:
                        text = ocr_text
                        metadata["ocr_applied"] = True
                except Exception:
                    pass

            units.append(ContentUnit(
                unit_type="page",
                unit_number=page_idx + 1,
                text=text,
                metadata=metadata
            ))
    finally:
        doc.close()
    return units


def extract_docx(path: Path) -> List[ContentUnit]:
    """
    Extract DOCX in natural document order traversing body children
    (interleaved paragraphs and tables) plus headers and footers.
    """
    from docx import Document
    from docx.text.paragraph import Paragraph
    from docx.table import Table

    units = []
    doc = Document(str(path))

    # Headers & Footers
    header_footer_texts = []
    try:
        for section in doc.sections:
            if section.header:
                for p in section.header.paragraphs:
                    t = p.text.strip()
                    if t and t not in header_footer_texts:
                        header_footer_texts.append(t)
            if section.footer:
                for p in section.footer.paragraphs:
                    t = p.text.strip()
                    if t and t not in header_footer_texts:
                        header_footer_texts.append(t)
    except Exception:
        pass

    current_section = "Document"
    current_blocks = []
    if header_footer_texts:
        current_blocks.append(" | ".join(header_footer_texts))

    section_num = 1

    # Traverse body elements in natural document order
    for child in doc.element.body:
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag

        if tag == "p":
            p = Paragraph(child, doc)
            txt = p.text.strip()
            if not txt:
                continue
            if p.style and p.style.name and p.style.name.startswith("Heading"):
                if current_blocks:
                    units.append(ContentUnit(
                        unit_type="section",
                        unit_number=section_num,
                        text="\n".join(current_blocks),
                        metadata={"section_title": current_section}
                    ))
                    section_num += 1
                    current_blocks = []
                current_section = txt
            current_blocks.append(txt)

        elif tag == "tbl":
            table = Table(child, doc)
            table_rows = []
            for row in table.rows:
                cells = [c.text.strip() for c in row.cells if c.text.strip()]
                if cells:
                    table_rows.append(" | ".join(cells))
            if table_rows:
                current_blocks.append("\n".join(table_rows))

    if current_blocks:
        units.append(ContentUnit(
            unit_type="section",
            unit_number=section_num,
            text="\n".join(current_blocks),
            metadata={"section_title": current_section}
        ))

    if not units and not doc.paragraphs and not doc.tables:
        units.append(ContentUnit(unit_type="section", unit_number=1, text=""))

    return units


def extract_pptx(path: Path) -> List[ContentUnit]:
    """
    Extract PPTX slides with recursive group shape traversal,
    slide titles, tables, and speaker notes.
    """
    from pptx import Presentation
    prs = Presentation(str(path))
    units = []

    def extract_from_shape(shape, collector: List[str]):
        # Recursively handle group shapes
        if hasattr(shape, "shapes"):
            for child in shape.shapes:
                extract_from_shape(child, collector)
            return

        if shape.has_text_frame:
            for paragraph in shape.text_frame.paragraphs:
                line = paragraph.text.strip()
                if line and line not in collector:
                    collector.append(line)

        if shape.has_table:
            for row in shape.table.rows:
                row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_cells:
                    collector.append(" | ".join(row_cells))

    for slide_idx, slide in enumerate(prs.slides):
        slide_texts = []
        has_images = False

        # Extract title explicitly first if present
        slide_title = ""
        try:
            if slide.shapes.title and slide.shapes.title.has_text_frame:
                slide_title = slide.shapes.title.text_frame.text.strip()
                if slide_title:
                    slide_texts.append(f"Title: {slide_title}")
        except Exception:
            pass

        for shape in slide.shapes:
            if shape.shape_type == 13:  # MSO_SHAPE_TYPE.PICTURE
                has_images = True
            extract_from_shape(shape, slide_texts)

        # Speaker notes
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
            notes = slide.notes_slide.notes_text_frame.text.strip()
            if notes:
                slide_texts.append(f"[Speaker Notes: {notes}]")

        metadata = {
            "slide_number": slide_idx + 1,
            "has_images": has_images
        }
        if slide_title:
            metadata["slide_title"] = slide_title

        units.append(ContentUnit(
            unit_type="slide",
            unit_number=slide_idx + 1,
            text="\n".join(slide_texts),
            metadata=metadata
        ))

    return units


def extract_ppt(path: Path) -> List[ContentUnit]:
    """Extract legacy PPT files using python-pptx or binary string stream extraction."""
    try:
        from pptx import Presentation
        prs = Presentation(str(path))
        return extract_pptx(path)
    except Exception:
        pass

    import re
    units = []
    try:
        with open(path, "rb") as f:
            content = f.read()
        ascii_strings = re.findall(b"[\x20-\x7E]{4,}", content)
        utf16_strings = re.findall(b"(?:[\x20-\x7E]\x00){4,}", content)

        extracted = []
        for s in ascii_strings:
            try:
                decoded = s.decode("latin-1", errors="ignore").strip()
                if len(decoded) > 3 and not decoded.startswith(("<?xml", "urn:", "http")):
                    extracted.append(decoded)
            except Exception:
                continue
        for s in utf16_strings:
            try:
                decoded = s.decode("utf-16le", errors="ignore").strip()
                if len(decoded) > 3:
                    extracted.append(decoded)
            except Exception:
                continue

        chunk_size = 15
        slide_idx = 1
        for i in range(0, len(extracted), chunk_size):
            block = extracted[i:i + chunk_size]
            units.append(ContentUnit(
                unit_type="slide",
                unit_number=slide_idx,
                text="\n".join(block),
                metadata={"slide_number": slide_idx}
            ))
            slide_idx += 1
    except Exception as e:
        logger.warning(f"Failed to extract text from PPT {path}: {e}")

    return units or [ContentUnit(unit_type="slide", unit_number=1, text="")]


def extract_xlsx(path: Path) -> List[ContentUnit]:
    """Extract XLSX workbook sheet by sheet using openpyxl."""
    import openpyxl
    wb = openpyxl.load_workbook(str(path), data_only=True, read_only=True)
    units = []

    try:
        for sheet_idx, sheet_name in enumerate(wb.sheetnames):
            sheet = wb[sheet_name]
            rows_data = []
            row_count = 0

            for row in sheet.iter_rows(values_only=True):
                # Filter out completely empty rows
                non_empty = [str(c).strip() for c in row if c is not None and str(c).strip() != ""]
                if non_empty:
                    rows_data.append(" | ".join(non_empty))
                    row_count += 1
                if row_count >= 1000:  # Reasonable cap per sheet to avoid blowing memory
                    rows_data.append("... [Additional rows truncated]")
                    break

            sheet_text = f"Sheet: {sheet_name}\n" + "\n".join(rows_data)
            units.append(ContentUnit(
                unit_type="sheet",
                unit_number=sheet_idx + 1,
                text=sheet_text.strip(),
                metadata={"sheet_name": sheet_name, "row_count": row_count}
            ))
    finally:
        wb.close()

    return units


def extract_xls(path: Path) -> List[ContentUnit]:
    """Extract legacy XLS files using xlrd."""
    import xlrd
    wb = xlrd.open_workbook(str(path))
    units = []

    for sheet_idx in range(wb.nsheets):
        sheet = wb.sheet_by_index(sheet_idx)
        rows_data = []
        for r in range(min(sheet.nrows, 1000)):
            row_vals = [str(sheet.cell_value(r, c)).strip() for c in range(sheet.ncols)]
            non_empty = [v for v in row_vals if v]
            if non_empty:
                rows_data.append(" | ".join(non_empty))

        sheet_text = f"Sheet: {sheet.name}\n" + "\n".join(rows_data)
        units.append(ContentUnit(
            unit_type="sheet",
            unit_number=sheet_idx + 1,
            text=sheet_text.strip(),
            metadata={"sheet_name": sheet.name, "row_count": sheet.nrows}
        ))
    return units


def extract_csv(path: Path) -> List[ContentUnit]:
    """Extract CSV preserving tabular context."""
    raw_text = read_text_file_safe(path)
    lines = raw_text.splitlines()
    if not lines:
        return [ContentUnit(unit_type="sheet", unit_number=1, text="")]

    rows_data = []
    # Use csv.reader
    reader = csv.reader(lines[:1000])
    for row in reader:
        non_empty = [c.strip() for c in row if c.strip()]
        if non_empty:
            rows_data.append(" | ".join(non_empty))

    return [ContentUnit(
        unit_type="sheet",
        unit_number=1,
        text="\n".join(rows_data),
        metadata={"total_lines": len(lines)}
    )]


def extract_json(path: Path) -> List[ContentUnit]:
    """Extract JSON producing readable structured text representation."""
    raw = read_text_file_safe(path)
    try:
        data = json.loads(raw)
        
        def format_json_node(obj, depth=0, max_depth=3) -> List[str]:
            if depth > max_depth:
                return ["..."]
            lines = []
            if isinstance(obj, dict):
                for k, v in list(obj.items())[:50]:
                    if isinstance(v, (dict, list)):
                        lines.append(f"{'  '*depth}{k}:")
                        lines.extend(format_json_node(v, depth+1, max_depth))
                    else:
                        lines.append(f"{'  '*depth}{k}: {v}")
            elif isinstance(obj, list):
                for item in obj[:50]:
                    lines.extend(format_json_node(item, depth, max_depth))
            else:
                lines.append(f"{'  '*depth}{obj}")
            return lines

        lines = format_json_node(data)
        formatted_text = "\n".join(lines)
        return [ContentUnit(unit_type="section", unit_number=1, text=formatted_text)]
    except Exception:
        return [ContentUnit(unit_type="section", unit_number=1, text=raw[:20000])]


def extract_xml(path: Path) -> List[ContentUnit]:
    """Extract XML tags and textual values."""
    raw = read_text_file_safe(path)
    try:
        root = ET.fromstring(raw)
        lines = []
        for elem in root.iter():
            txt = (elem.text or "").strip()
            if txt:
                lines.append(f"{elem.tag}: {txt}")
        return [ContentUnit(unit_type="section", unit_number=1, text="\n".join(lines[:2000]))]
    except Exception:
        # Fallback to BeautifulSoup or raw text
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(raw, "html.parser")
        return [ContentUnit(unit_type="section", unit_number=1, text=soup.get_text()[:20000])]


def extract_rtf(path: Path) -> List[ContentUnit]:
    """Extract Rich Text Format using striprtf."""
    from striprtf.striprtf import rtf_to_text
    raw = read_text_file_safe(path)
    plain_text = rtf_to_text(raw)
    return [ContentUnit(unit_type="section", unit_number=1, text=plain_text.strip())]


def extract_odf(path: Path, extension: str) -> List[ContentUnit]:
    """Extract ODT, ODS, or ODP using odfpy."""
    from odf import opendocument, teletype
    from odf.text import P, H
    
    doc = opendocument.load(str(path))
    elements = doc.getElementsByType(H) + doc.getElementsByType(P)
    texts = [teletype.extractText(e).strip() for e in elements]
    full_text = "\n".join(t for t in texts if t)
    
    unit_type = "slide" if extension == ".odp" else ("sheet" if extension == ".ods" else "section")
    return [ContentUnit(unit_type=unit_type, unit_number=1, text=full_text)]


def extract_doc(path: Path) -> List[ContentUnit]:
    """Extract legacy Word .doc files via LibreOffice soffice headless conversion if installed."""
    import shutil
    import subprocess
    import tempfile
    soffice_bin = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice_bin:
        logger.info(f"soffice not found in PATH; cannot convert legacy doc: {path}")
        return []

    with tempfile.TemporaryDirectory() as tmp_dir:
        try:
            subprocess.run(
                [soffice_bin, "--headless", "--convert-to", "docx", str(path), "--outdir", tmp_dir],
                check=True,
                timeout=30,
                capture_output=True
            )
            converted = Path(tmp_dir) / f"{path.stem}.docx"
            if converted.exists():
                return extract_docx(converted)
        except Exception as e:
            logger.warning(f"LibreOffice conversion failed for {path}: {e}")
    return []


def extract_image_ocr(path: Path) -> List[ContentUnit]:
    """Extract text from an image using OCR if pytesseract is available."""
    try:
        import pytesseract
        from PIL import Image
        with Image.open(str(path)) as img:
            text = pytesseract.image_to_string(img).strip()
            if text:
                return [ContentUnit(
                    unit_type="image",
                    unit_number=1,
                    text=text,
                    metadata={"ocr": True, "dimensions": f"{img.width}x{img.height}"}
                )]
    except Exception:
        pass
    return []


def extract_image_metadata(path: Path) -> List[ContentUnit]:
    """Extract standalone image information and descriptive metadata."""
    from PIL import Image
    with Image.open(str(path)) as img:
        desc = f"Image file: {path.name}, format: {img.format}, dimensions: {img.width}x{img.height}, mode: {img.mode}"
        return [ContentUnit(
            unit_type="image",
            unit_number=1,
            text=desc,
            metadata={"width": img.width, "height": img.height, "format": img.format}
        )]
