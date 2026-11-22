from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class ContentUnit:
    """
    A discrete unit of document content (e.g. a page, a slide, a sheet, or a section).
    """
    unit_type: str  # "page", "slide", "sheet", "section", "table", "image", "raw"
    unit_number: int  # 1-indexed number (page 1, slide 1, sheet 1)
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractionResult:
    """
    Standardized result from extracting any supported file type.
    """
    file_name: str
    file_path: str
    file_type: str
    category: str
    content_units: List[ContentUnit] = field(default_factory=list)
    success: bool = True
    error_message: Optional[str] = None
    has_visual_content: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_text(self) -> str:
        return "\n\n".join(u.text for u in self.content_units if u.text.strip())
