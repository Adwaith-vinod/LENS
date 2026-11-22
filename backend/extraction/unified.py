import logging
from pathlib import Path
from typing import Optional, Dict, Any

from backend.discovery.file_filters import get_file_category
from backend.extraction.models import ContentUnit, ExtractionResult
from backend.extraction.extractors import (
    extract_pdf,
    extract_docx,
    extract_pptx,
    extract_ppt,
    extract_xlsx,
    extract_xls,
    extract_csv,
    extract_json,
    extract_xml,
    extract_rtf,
    extract_odf,
    read_text_file_safe,
    extract_image_metadata
)

logger = logging.getLogger(__name__)


def extract_file_content(file_path: str, category: Optional[str] = None) -> ExtractionResult:
    """
    Unified entry point for extracting content from any supported file.
    Always returns an ExtractionResult object and never raises an unhandled exception.
    """
    path = Path(file_path)
    extension = path.suffix.lower()
    
    if not category:
        category = get_file_category(path) or "unknown"

    result = ExtractionResult(
        file_name=path.name,
        file_path=str(path.resolve()),
        file_type=extension,
        category=category,
        content_units=[],
        success=False
    )

    if not path.exists():
        result.error_message = f"File does not exist: {file_path}"
        return result

    try:
        if extension == ".pdf":
            result.content_units = extract_pdf(path)
            result.has_visual_content = any(u.metadata.get("has_images") for u in result.content_units)
            result.success = True

        elif extension == ".docx":
            result.content_units = extract_docx(path)
            result.success = True

        elif extension == ".pptx":
            result.content_units = extract_pptx(path)
            result.has_visual_content = any(u.metadata.get("has_images") for u in result.content_units)
            result.success = True

        elif extension == ".ppt":
            result.content_units = extract_ppt(path)
            result.has_visual_content = any(u.metadata.get("has_images") for u in result.content_units)
            result.success = True

        elif extension in [".xlsx", ".xlsm"]:
            result.content_units = extract_xlsx(path)
            result.success = True

        elif extension == ".xls":
            result.content_units = extract_xls(path)
            result.success = True

        elif extension == ".csv":
            result.content_units = extract_csv(path)
            result.success = True

        elif extension in [".txt", ".md", ".markdown"]:
            text = read_text_file_safe(path)
            result.content_units = [ContentUnit(unit_type="section", unit_number=1, text=text.strip())]
            result.success = True

        elif extension == ".rtf":
            result.content_units = extract_rtf(path)
            result.success = True

        elif extension in [".odt", ".ods", ".odp"]:
            result.content_units = extract_odf(path, extension)
            result.success = True

        elif extension == ".json":
            result.content_units = extract_json(path)
            result.success = True

        elif extension == ".xml":
            result.content_units = extract_xml(path)
            result.success = True

        elif extension in [".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif"]:
            result.content_units = extract_image_metadata(path)
            result.has_visual_content = True
            result.success = True

        else:
            # Fallback for plain text readable
            text = read_text_file_safe(path)
            if text:
                result.content_units = [ContentUnit(unit_type="raw", unit_number=1, text=text[:10000].strip())]
                result.success = True
            else:
                result.error_message = f"Unsupported file extension: {extension}"

    except Exception as e:
        logger.warning(f"Error extracting content from {file_path}: {e}")
        result.success = False
        result.error_message = str(e)

    return result
