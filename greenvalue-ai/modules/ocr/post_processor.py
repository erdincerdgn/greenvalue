"""
OCR Post-Processor
Author: GreenValue AI Team
Purpose: Clean, validate, and enhance OCR output for publication quality.
"""

import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger("greenvalue-ocr")


class OCRPostProcessor:
    """
    Post-process OCR output for maximum quality.

    Pipeline:
        1. Remove OCR artifacts (broken characters, noise)
        2. Fix common OCR errors (0/O, 1/l, etc.)
        3. Merge hyphenated line breaks
        4. Clean whitespace and formatting
        5. Validate confidence thresholds
        6. PropTech-specific corrections (units, abbreviations)
    """

    def __init__(self, min_confidence: float = 0.60):
        self.min_confidence = min_confidence

        # Common OCR substitution errors
        self.ocr_fixes = {
            "ﬁ": "fi",
            "ﬂ": "fl",
            "ﬀ": "ff",
            "ﬃ": "ffi",
            "ﬄ": "ffl",
            "\u2018": "'",
            "\u2019": "'",
            "\u201c": '"',
            "\u201d": '"',
            "\u2013": "-",
            "\u2014": "--",
            "\u2026": "...",
            "\u00a0": " ",  # Non-breaking space
            "\u200b": "",   # Zero-width space
        }

        # PropTech-specific unit corrections
        self.unit_corrections = {
            r"W\s*/\s*m\s*2\s*K": "W/m²K",
            r"W\s*/\s*m²\s*K": "W/m²K",
            r"W\s*/\s*\(m²·K\)": "W/m²K",
            r"m\s*2\s*K\s*/\s*W": "m²K/W",
            r"kWh\s*/\s*m\s*2": "kWh/m²",
            r"kWh\s*/\s*m²": "kWh/m²",
            r"kg\s*CO\s*2": "kg CO₂",
            r"kg\s*co2": "kg CO₂",
        }

        # Abbreviation expansions for PropTech domain
        self.abbreviation_map = {
            "U-val": "U-value",
            "R-val": "R-value",
            "bldg": "building",
            "temp": "temperature",
            "insul": "insulation",
            "eff": "efficiency",
        }

    def process_page(self, page) -> "OCRPage":
        """
        Post-process a single OCR page.

        Args:
            page: OCRPage object

        Returns:
            Cleaned OCRPage
        """
        # Process full text
        if page.full_text:
            page.full_text = self.clean_text(page.full_text)

        # Process each element
        for elem in page.elements:
            elem.content = self.clean_text(elem.content)

            # Convert table content to markdown if not already
            if elem.element_type.value == "table" and not elem.markdown:
                elem.markdown = self._format_table_markdown(elem.content)

        # Re-calculate page confidence
        if page.elements:
            confs = [e.confidence for e in page.elements if e.confidence > 0]
            page.confidence = sum(confs) / len(confs) if confs else 0.0

        return page

    def clean_text(self, text: str) -> str:
        """
        Clean OCR text output.

        Steps:
            1. Fix ligatures and special characters
            2. Fix PropTech units
            3. Merge hyphenated line breaks
            4. Normalize whitespace
            5. Remove OCR artifacts
        """
        if not text or not text.strip():
            return ""

        # Step 1: Fix ligatures and unicode oddities
        for old, new in self.ocr_fixes.items():
            text = text.replace(old, new)

        # Step 2: Fix PropTech units
        for pattern, replacement in self.unit_corrections.items():
            text = re.sub(pattern, replacement, text)

        # Step 3: Merge hyphenated line breaks
        # "insu-\nlation" → "insulation"
        text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

        # Step 4: Normalize whitespace
        # Collapse multiple spaces (but preserve newlines for structure)
        text = re.sub(r"[^\S\n]+", " ", text)
        # Remove lines that are only whitespace
        lines = text.split("\n")
        lines = [l.rstrip() for l in lines]
        text = "\n".join(lines)
        # Collapse 3+ newlines to 2
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Step 5: Remove common OCR noise
        # Remove isolated single characters surrounded by spaces
        text = re.sub(r" [^\w\s€$£%°] ", " ", text)
        # Remove control characters
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

        return text.strip()

    def fix_numbers(self, text: str) -> str:
        """Fix common number OCR errors in financial data."""
        # Fix O (letter) → 0 (zero) in numeric contexts
        text = re.sub(r"(?<=\d)O(?=\d)", "0", text)
        # Fix l (lowercase L) → 1 in numeric contexts
        text = re.sub(r"(?<=\d)l(?=\d)", "1", text)
        # Fix S → 5 in numeric contexts
        text = re.sub(r"(?<=\d)S(?=\d)", "5", text)
        # Fix B → 8 in numeric contexts
        text = re.sub(r"(?<=\d)B(?=\d)", "8", text)

        return text

    def _format_table_markdown(self, text: str) -> str:
        """Convert raw table text to markdown format."""
        lines = text.strip().split("\n")

        # Already markdown?
        if any("|" in l for l in lines[:3]):
            return text

        # Try tab-separated
        if any("\t" in l for l in lines):
            md_lines = []
            for i, line in enumerate(lines):
                cells = [c.strip() for c in line.split("\t")]
                md_lines.append("| " + " | ".join(cells) + " |")
                if i == 0:
                    md_lines.append("| " + " | ".join(["---"] * len(cells)) + " |")
            return "\n".join(md_lines)

        # Return as-is if no clear structure
        return text

    def validate_confidence(self, text: str, confidence: float) -> bool:
        """Check if OCR output meets minimum confidence threshold."""
        if confidence < self.min_confidence:
            return False

        # Additional heuristic: if text is mostly non-printable, reject
        if text:
            printable_ratio = sum(1 for c in text if c.isprintable()) / len(text)
            if printable_ratio < 0.70:
                return False

        return True

    def merge_columns(self, left_text: str, right_text: str) -> str:
        """Merge two-column layout text into reading order."""
        left_lines = left_text.strip().split("\n")
        right_lines = right_text.strip().split("\n")

        # Interleave: all left lines first, then right
        merged = "\n".join(left_lines) + "\n\n" + "\n".join(right_lines)
        return merged.strip()
