"""
Table Extractor for OCR Pipeline
Author: GreenValue AI Team
Purpose: Detect and extract structured tables from documents,
         with special handling for financial and energy data.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("greenvalue-ocr")


class TableExtractor:
    """
    Extract and structure table data from OCR output.

    Handles:
        - Markdown pipe tables
        - Tab-separated data
        - Space-aligned columns
        - HTML tables (from Unstructured API)
        - Financial tables (€, $, kWh, W/m²K)
    """

    def __init__(self, confidence_threshold: float = 0.70):
        self.confidence_threshold = confidence_threshold

        # PropTech financial patterns
        self.financial_indicators = [
            r"cost|price|budget|fee|expense",
            r"roi|return\s+on\s+investment|npv|irr|payback",
            r"€|£|\$|USD|EUR|GBP|TRY",
            r"kWh|W/m²K|MJ|BTU",
            r"energy\s+(saving|consumption|cost|efficiency)",
            r"u[\-\s]?value|r[\-\s]?value|thermal",
            r"renovation|retrofit|upgrade\s+cost",
            r"carbon|CO2|emission",
        ]

    def is_table_content(self, text: str) -> Tuple[bool, float]:
        """
        Detect if text contains tabular data.

        Returns:
            (is_table, confidence) tuple
        """
        score = 0.0
        lines = text.strip().split("\n")

        if len(lines) < 2:
            return False, 0.0

        # Check for pipe-delimited tables
        pipe_lines = sum(1 for l in lines if "|" in l)
        if pipe_lines >= 2:
            score += 0.4

        # Check for tab-delimited data
        tab_lines = sum(1 for l in lines if "\t" in l)
        if tab_lines >= 2:
            score += 0.35

        # Check for aligned columns (multiple spaces between data)
        aligned = sum(1 for l in lines if re.search(r"\S\s{3,}\S", l))
        if aligned >= 2:
            score += 0.25

        # Financial content boost
        text_lower = text.lower()
        fin_matches = sum(
            1 for p in self.financial_indicators if re.search(p, text_lower)
        )
        if fin_matches >= 2:
            score += 0.2

        # Numeric density (tables have many numbers)
        numbers = re.findall(r"\d+[.,]?\d*", text)
        if len(numbers) > 5:
            score += 0.15

        is_table = score >= self.confidence_threshold
        return is_table, min(score, 1.0)

    def extract_table(self, text: str, html: Optional[str] = None) -> Dict:
        """
        Extract structured table data.

        Args:
            text: Raw text of the table
            html: Optional HTML representation (from Unstructured API)

        Returns:
            Dict with headers, rows, markdown, and metadata
        """
        result = {
            "headers": [],
            "rows": [],
            "markdown": "",
            "row_count": 0,
            "col_count": 0,
            "has_financial_data": False,
            "detected_metrics": [],
        }

        # Prefer HTML parsing if available
        if html:
            parsed = self._parse_html_table(html)
            if parsed:
                result.update(parsed)
                result["markdown"] = self._to_markdown(
                    result["headers"], result["rows"]
                )
                result["has_financial_data"] = self._detect_financial(text)
                result["detected_metrics"] = self._extract_metrics(text)
                return result

        # Parse pipe-delimited
        if "|" in text:
            parsed = self._parse_pipe_table(text)
            if parsed:
                result.update(parsed)
                result["markdown"] = self._to_markdown(
                    result["headers"], result["rows"]
                )
                result["has_financial_data"] = self._detect_financial(text)
                result["detected_metrics"] = self._extract_metrics(text)
                return result

        # Parse tab-delimited
        if "\t" in text:
            parsed = self._parse_tab_table(text)
            if parsed:
                result.update(parsed)
                result["markdown"] = self._to_markdown(
                    result["headers"], result["rows"]
                )
                result["has_financial_data"] = self._detect_financial(text)
                result["detected_metrics"] = self._extract_metrics(text)
                return result

        # Fallback: treat each line as a row
        lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
        if lines:
            result["headers"] = []
            result["rows"] = [[line] for line in lines]
            result["row_count"] = len(lines)
            result["col_count"] = 1
            result["markdown"] = text
            result["has_financial_data"] = self._detect_financial(text)

        return result

    def _parse_html_table(self, html: str) -> Optional[Dict]:
        """Parse HTML table into headers + rows."""
        try:
            from html.parser import HTMLParser

            class _Parser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.rows: List[List[str]] = []
                    self.current_row: List[str] = []
                    self.current_cell = ""
                    self.in_cell = False

                def handle_starttag(self, tag, attrs):
                    if tag in ("td", "th"):
                        self.in_cell = True
                        self.current_cell = ""
                    elif tag == "tr":
                        self.current_row = []

                def handle_endtag(self, tag):
                    if tag in ("td", "th"):
                        self.in_cell = False
                        self.current_row.append(self.current_cell.strip())
                    elif tag == "tr":
                        if self.current_row:
                            self.rows.append(self.current_row)

                def handle_data(self, data):
                    if self.in_cell:
                        self.current_cell += data

            parser = _Parser()
            parser.feed(html)

            if not parser.rows:
                return None

            headers = parser.rows[0] if parser.rows else []
            rows = parser.rows[1:] if len(parser.rows) > 1 else []

            return {
                "headers": headers,
                "rows": rows,
                "row_count": len(rows),
                "col_count": len(headers),
            }

        except Exception as e:
            logger.debug(f"HTML table parse failed: {e}")
            return None

    def _parse_pipe_table(self, text: str) -> Optional[Dict]:
        """Parse pipe-delimited markdown table."""
        lines = [l.strip() for l in text.strip().split("\n") if l.strip()]

        if len(lines) < 2:
            return None

        def split_row(line: str) -> List[str]:
            cells = [c.strip() for c in line.split("|")]
            # Remove empty first/last from leading/trailing pipes
            if cells and not cells[0]:
                cells = cells[1:]
            if cells and not cells[-1]:
                cells = cells[:-1]
            return cells

        headers = split_row(lines[0])

        # Skip separator line (---+---)
        start_idx = 1
        if len(lines) > 1 and re.match(r"^[\s|:\-]+$", lines[1]):
            start_idx = 2

        rows = [split_row(l) for l in lines[start_idx:] if "|" in l]

        return {
            "headers": headers,
            "rows": rows,
            "row_count": len(rows),
            "col_count": len(headers),
        }

    def _parse_tab_table(self, text: str) -> Optional[Dict]:
        """Parse tab-separated table."""
        lines = [l for l in text.strip().split("\n") if l.strip()]

        if len(lines) < 2:
            return None

        headers = [c.strip() for c in lines[0].split("\t")]
        rows = [[c.strip() for c in l.split("\t")] for l in lines[1:]]

        return {
            "headers": headers,
            "rows": rows,
            "row_count": len(rows),
            "col_count": len(headers),
        }

    def _to_markdown(self, headers: List[str], rows: List[List[str]]) -> str:
        """Convert headers + rows to a Markdown table."""
        if not headers and not rows:
            return ""

        if not headers and rows:
            col_count = max(len(r) for r in rows)
            headers = [f"Col {i+1}" for i in range(col_count)]

        col_count = len(headers)

        # Normalize row lengths
        norm_rows = []
        for row in rows:
            if len(row) < col_count:
                row = row + [""] * (col_count - len(row))
            elif len(row) > col_count:
                row = row[:col_count]
            norm_rows.append(row)

        lines = ["| " + " | ".join(headers) + " |"]
        lines.append("| " + " | ".join(["---"] * col_count) + " |")
        for row in norm_rows:
            lines.append("| " + " | ".join(row) + " |")

        return "\n".join(lines)

    def _detect_financial(self, text: str) -> bool:
        """Detect if table contains financial/energy data."""
        text_lower = text.lower()
        return any(
            re.search(p, text_lower) for p in self.financial_indicators[:4]
        )

    def _extract_metrics(self, text: str) -> List[Dict]:
        """Extract PropTech metrics from table text."""
        metrics = []

        patterns = {
            "u_value": (r"(\d+[.,]\d+)\s*W/m²K", "W/m²K"),
            "r_value": (r"R[\-\s]?value[:\s]*(\d+[.,]\d+)", "m²K/W"),
            "energy_consumption": (r"(\d+[.,]?\d*)\s*kWh", "kWh"),
            "cost_eur": (r"€\s*(\d+[.,]?\d*)", "EUR"),
            "cost_usd": (r"\$\s*(\d+[.,]?\d*)", "USD"),
            "co2_emission": (r"(\d+[.,]?\d*)\s*(?:kg\s*)?CO2", "kgCO2"),
            "roi_percent": (r"ROI[:\s]*(\d+[.,]?\d*)\s*%", "%"),
            "payback_years": (r"payback[:\s]*(\d+[.,]?\d*)\s*year", "years"),
        }

        for metric_name, (pattern, unit) in patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches[:3]:
                metrics.append({
                    "name": metric_name,
                    "value": m,
                    "unit": unit,
                })

        return metrics
