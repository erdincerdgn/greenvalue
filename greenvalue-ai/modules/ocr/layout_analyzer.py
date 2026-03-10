"""
Document Layout Analyzer
Author: GreenValue AI Team
Purpose: Detect document layout structure — columns, headers, footers,
         reading order — for publication-quality OCR.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("greenvalue-ocr")


class LayoutRegion(str, Enum):
    """Semantic regions detected in a document page."""
    HEADER = "header"
    FOOTER = "footer"
    BODY = "body"
    SIDEBAR = "sidebar"
    TABLE = "table"
    FIGURE = "figure"
    CAPTION = "caption"
    PAGE_NUMBER = "page_number"
    FOOTNOTE = "footnote"
    TITLE = "title"
    ABSTRACT = "abstract"
    BIBLIOGRAPHY = "bibliography"


@dataclass
class LayoutBlock:
    """A detected block in the document layout."""
    region: LayoutRegion
    text: str
    x1: float = 0.0
    y1: float = 0.0
    x2: float = 0.0
    y2: float = 0.0
    reading_order: int = 0
    confidence: float = 0.8
    metadata: Dict = field(default_factory=dict)

    @property
    def area(self) -> float:
        return (self.x2 - self.x1) * (self.y2 - self.y1)


@dataclass
class PageLayout:
    """Complete layout analysis of a page."""
    page_number: int
    width: float
    height: float
    blocks: List[LayoutBlock] = field(default_factory=list)
    num_columns: int = 1
    has_header: bool = False
    has_footer: bool = False
    has_tables: bool = False
    has_figures: bool = False
    reading_order: List[int] = field(default_factory=list)

    def get_body_text(self) -> str:
        """Get body text in reading order."""
        body_blocks = [
            b for b in self.blocks
            if b.region in {LayoutRegion.BODY, LayoutRegion.TITLE, LayoutRegion.ABSTRACT}
        ]
        body_blocks.sort(key=lambda b: b.reading_order)
        return "\n\n".join(b.text for b in body_blocks)


class LayoutAnalyzer:
    """
    Analyze document page layout for optimal text extraction ordering.

    Uses heuristic rules to detect:
        - Headers and footers (top/bottom 10% of page)
        - Multi-column layouts (horizontal text distribution)
        - Tables (pipe/tab patterns, grid indicators)
        - Figures (image regions)
        - Reading order (top-to-bottom, left-to-right, column-aware)
    """

    # Page region thresholds (as fraction of page height/width)
    HEADER_ZONE = 0.10   # Top 10%
    FOOTER_ZONE = 0.90   # Bottom 10%
    SIDEBAR_ZONE = 0.15  # Left/right 15%

    # Publication patterns
    TITLE_PATTERNS = [
        r"^chapter\s+\d+",
        r"^section\s+\d+",
        r"^\d+\.\s+[A-Z]",
        r"^abstract$",
        r"^introduction$",
        r"^conclusion",
        r"^references$",
        r"^bibliography$",
        r"^appendix",
    ]

    def analyze(
        self,
        elements: List[Dict],
        page_width: float = 612.0,
        page_height: float = 792.0,
    ) -> PageLayout:
        """
        Analyze page layout from extracted elements.

        Args:
            elements: List of element dicts with 'text', 'type', and optional
                      'coordinates' (from Unstructured API or OCR)
            page_width: Page width in points (default: US Letter)
            page_height: Page height in points

        Returns:
            PageLayout with classified blocks and reading order
        """
        layout = PageLayout(
            page_number=1,
            width=page_width,
            height=page_height,
        )

        blocks: List[LayoutBlock] = []

        for elem in elements:
            text = elem.get("text", "").strip()
            if not text:
                continue

            elem_type = elem.get("type", "NarrativeText")
            coords = elem.get("coordinates", {})
            points = coords.get("points", [])

            x1, y1, x2, y2 = 0, 0, page_width, 0
            if points and len(points) >= 4:
                xs = [p[0] for p in points]
                ys = [p[1] for p in points]
                x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)

            # Classify region
            region = self._classify_region(
                text, elem_type, x1, y1, x2, y2, page_width, page_height
            )

            block = LayoutBlock(
                region=region,
                text=text,
                x1=x1, y1=y1, x2=x2, y2=y2,
                confidence=0.85,
            )
            blocks.append(block)

        # Detect column count
        layout.num_columns = self._detect_columns(blocks, page_width)

        # Assign reading order
        self._assign_reading_order(blocks, layout.num_columns, page_width)

        # Set layout flags
        layout.blocks = blocks
        layout.has_header = any(b.region == LayoutRegion.HEADER for b in blocks)
        layout.has_footer = any(b.region == LayoutRegion.FOOTER for b in blocks)
        layout.has_tables = any(b.region == LayoutRegion.TABLE for b in blocks)
        layout.has_figures = any(b.region == LayoutRegion.FIGURE for b in blocks)
        layout.reading_order = [b.reading_order for b in blocks]

        return layout

    def _classify_region(
        self,
        text: str,
        elem_type: str,
        x1: float, y1: float, x2: float, y2: float,
        page_width: float, page_height: float,
    ) -> LayoutRegion:
        """Classify a block into a layout region."""

        # Map Unstructured element types first
        type_map = {
            "Table": LayoutRegion.TABLE,
            "Image": LayoutRegion.FIGURE,
            "FigureCaption": LayoutRegion.CAPTION,
            "Header": LayoutRegion.HEADER,
            "Footer": LayoutRegion.FOOTER,
            "PageNumber": LayoutRegion.PAGE_NUMBER,
            "Title": LayoutRegion.TITLE,
        }
        if elem_type in type_map:
            return type_map[elem_type]

        # Position-based classification
        if page_height > 0:
            y_frac = y1 / page_height

            # Header zone
            if y_frac < self.HEADER_ZONE:
                return LayoutRegion.HEADER

            # Footer zone
            if y_frac > self.FOOTER_ZONE:
                # Check if it's a page number
                if re.match(r"^\s*\d+\s*$", text):
                    return LayoutRegion.PAGE_NUMBER
                return LayoutRegion.FOOTER

        # Content-based classification
        text_lower = text.lower().strip()

        # Title/section patterns
        for pattern in self.TITLE_PATTERNS:
            if re.match(pattern, text_lower, re.IGNORECASE):
                return LayoutRegion.TITLE

        # Bibliography
        if text_lower.startswith("references") or text_lower.startswith("bibliography"):
            return LayoutRegion.BIBLIOGRAPHY

        # Abstract
        if text_lower.startswith("abstract"):
            return LayoutRegion.ABSTRACT

        # Footnote (small text at bottom, starts with number or *)
        if page_height > 0 and y1 / page_height > 0.80:
            if re.match(r"^[\d*†‡§]", text):
                return LayoutRegion.FOOTNOTE

        # Caption (short text near figure/table markers)
        if len(text) < 200 and re.match(r"^(fig(ure)?|table|chart)\s*[\d.]", text_lower):
            return LayoutRegion.CAPTION

        # Sidebar (narrow blocks on the side)
        if page_width > 0:
            block_width = x2 - x1
            x_center = (x1 + x2) / 2
            if block_width < page_width * 0.25:
                if x_center < page_width * self.SIDEBAR_ZONE:
                    return LayoutRegion.SIDEBAR
                if x_center > page_width * (1 - self.SIDEBAR_ZONE):
                    return LayoutRegion.SIDEBAR

        return LayoutRegion.BODY

    def _detect_columns(
        self, blocks: List[LayoutBlock], page_width: float
    ) -> int:
        """Detect number of text columns on the page."""
        if not blocks or page_width == 0:
            return 1

        body_blocks = [
            b for b in blocks if b.region == LayoutRegion.BODY
        ]
        if len(body_blocks) < 4:
            return 1

        # Check x-coordinate distribution
        x_centers = [(b.x1 + b.x2) / 2 for b in body_blocks]
        if not x_centers:
            return 1

        # Simple heuristic: if x-centers cluster into 2 groups → 2 columns
        mid = page_width / 2
        left_count = sum(1 for x in x_centers if x < mid * 0.8)
        right_count = sum(1 for x in x_centers if x > mid * 1.2)

        total = len(x_centers)
        if left_count > total * 0.3 and right_count > total * 0.3:
            return 2

        return 1

    def _assign_reading_order(
        self, blocks: List[LayoutBlock], num_columns: int, page_width: float
    ):
        """Assign reading order to blocks based on layout."""
        if num_columns == 1:
            # Single column: top to bottom
            sorted_blocks = sorted(blocks, key=lambda b: (b.y1, b.x1))
        else:
            # Multi-column: column by column, top to bottom within each
            mid = page_width / 2

            left_blocks = [b for b in blocks if (b.x1 + b.x2) / 2 < mid]
            right_blocks = [b for b in blocks if (b.x1 + b.x2) / 2 >= mid]

            left_blocks.sort(key=lambda b: b.y1)
            right_blocks.sort(key=lambda b: b.y1)

            sorted_blocks = left_blocks + right_blocks

        for i, block in enumerate(sorted_blocks):
            block.reading_order = i
