"""
Professional OCR Engine — Hi-Res Strategy for Major Publications
Author: GreenValue AI Team
Purpose: Enterprise-grade OCR with multi-strategy extraction, layout analysis,
         and publication-quality output for PropTech documents.

Strategies:
  - hi_res:  Unstructured API (tables, images, layout-aware) — primary
  - tesseract: Local Tesseract OCR (multi-language, scanned docs) — fallback
  - hybrid:  hi_res + Tesseract cross-validation for maximum accuracy
  - fast:    PyPDF2 text extraction only (no OCR, fastest)

Supported formats: PDF, JPEG, PNG, TIFF, HEIF, BMP, WebP
"""

import io
import logging
import os
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from PIL import Image

logger = logging.getLogger("greenvalue-ocr")


# ─── Data Models ──────────────────────────────────────────────


class OCRStrategy(str, Enum):
    """OCR processing strategies ordered by quality."""
    HI_RES = "hi_res"
    TESSERACT = "tesseract"
    HYBRID = "hybrid"
    FAST = "fast"


class PageElementType(str, Enum):
    """Types of elements extracted from a page."""
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    HEADER = "header"
    FOOTER = "footer"
    CAPTION = "caption"
    LIST = "list"
    FORMULA = "formula"
    PAGE_NUMBER = "page_number"


@dataclass
class BoundingBox:
    """Bounding box for a page element (coordinates in points)."""
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def area(self) -> float:
        return self.width * self.height

    def to_dict(self) -> Dict:
        return {"x1": self.x1, "y1": self.y1, "x2": self.x2, "y2": self.y2}


@dataclass
class PageElement:
    """A single element extracted from a document page."""
    element_type: PageElementType
    content: str
    page_number: int
    confidence: float = 1.0
    bbox: Optional[BoundingBox] = None
    metadata: Dict = field(default_factory=dict)
    html: Optional[str] = None  # For tables, HTML representation
    markdown: Optional[str] = None  # Markdown formatted content


@dataclass
class OCRPage:
    """Represents a fully processed page."""
    page_number: int
    elements: List[PageElement] = field(default_factory=list)
    full_text: str = ""
    tables: List[PageElement] = field(default_factory=list)
    images: List[PageElement] = field(default_factory=list)
    headers: List[PageElement] = field(default_factory=list)
    language: str = "en"
    confidence: float = 1.0
    width: float = 0.0
    height: float = 0.0

    @property
    def has_tables(self) -> bool:
        return len(self.tables) > 0

    @property
    def has_images(self) -> bool:
        return len(self.images) > 0

    def to_dict(self) -> Dict:
        return {
            "page_number": self.page_number,
            "full_text": self.full_text,
            "table_count": len(self.tables),
            "image_count": len(self.images),
            "header_count": len(self.headers),
            "language": self.language,
            "confidence": self.confidence,
            "element_count": len(self.elements),
        }


@dataclass
class OCRResult:
    """Complete OCR processing result for a document."""
    document_id: str
    filename: str
    strategy: OCRStrategy
    pages: List[OCRPage] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    processing_time_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None

    @property
    def total_pages(self) -> int:
        return len(self.pages)

    @property
    def total_tables(self) -> int:
        return sum(len(p.tables) for p in self.pages)

    @property
    def total_images(self) -> int:
        return sum(len(p.images) for p in self.pages)

    @property
    def total_characters(self) -> int:
        return sum(len(p.full_text) for p in self.pages)

    @property
    def avg_confidence(self) -> float:
        if not self.pages:
            return 0.0
        return sum(p.confidence for p in self.pages) / len(self.pages)

    def get_full_text(self) -> str:
        """Get complete document text with page separators."""
        parts = []
        for page in self.pages:
            parts.append(f"--- Page {page.page_number} ---")
            parts.append(page.full_text)
        return "\n\n".join(parts)

    def get_tables_markdown(self) -> List[Dict]:
        """Get all tables as markdown with metadata."""
        tables = []
        for page in self.pages:
            for table in page.tables:
                tables.append({
                    "page": page.page_number,
                    "content": table.content,
                    "markdown": table.markdown or table.content,
                    "html": table.html,
                    "confidence": table.confidence,
                })
        return tables

    def to_dict(self) -> Dict:
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "strategy": self.strategy.value,
            "total_pages": self.total_pages,
            "total_tables": self.total_tables,
            "total_images": self.total_images,
            "total_characters": self.total_characters,
            "avg_confidence": round(self.avg_confidence, 3),
            "processing_time_ms": round(self.processing_time_ms, 1),
            "success": self.success,
            "error": self.error,
            "pages": [p.to_dict() for p in self.pages],
        }


# ─── Configuration ────────────────────────────────────────────


@dataclass
class OCRConfig:
    """Configuration for the OCR engine."""
    # Unstructured API
    unstructured_url: str = "http://greenvalue-unstructured:8000/general/v0/general"
    unstructured_api_key: str = os.getenv("UNSTRUCTURED_API_KEY", "")
    unstructured_timeout: int = 600  # seconds per batch

    # Tesseract
    tesseract_languages: List[str] = field(
        default_factory=lambda: ["eng", "tur", "deu", "fra"]
    )
    tesseract_psm: int = 3  # Page segmentation mode (auto)
    tesseract_oem: int = 3  # OCR engine mode (LSTM + legacy)

    # Processing
    page_batch_size: int = 15
    max_file_size_mb: float = 500.0
    default_strategy: OCRStrategy = OCRStrategy.HI_RES
    dpi: int = 300  # DPI for image conversion
    enable_deskew: bool = True
    enable_denoise: bool = True

    # Quality thresholds
    min_confidence_threshold: float = 0.60
    table_detection_threshold: float = 0.70
    hybrid_cross_validate: bool = True

    # Output
    preserve_layout: bool = True
    extract_images: bool = True
    output_format: str = "markdown"  # markdown, html, plain


# ─── OCR Engine ───────────────────────────────────────────────


class OCREngine:
    """
    Professional OCR Engine with hi_res strategy for major publications.

    Architecture:
        1. ImagePreprocessor → deskew, denoise, enhance
        2. LayoutAnalyzer → detect columns, headers, footers
        3. Strategy Router → hi_res / tesseract / hybrid / fast
        4. TableExtractor → structured table extraction
        5. PostProcessor → spell-check, formatting, confidence
        6. Output Formatter → markdown / html / plain

    Usage:
        engine = OCREngine()
        engine.initialize()
        result = engine.process("document.pdf", strategy=OCRStrategy.HI_RES)
    """

    def __init__(self, config: Optional[OCRConfig] = None):
        self.config = config or OCRConfig()
        self._initialized = False
        self._unstructured_available = False
        self._tesseract_available = False

        # Component instances (lazy-loaded)
        self._preprocessor = None
        self._table_extractor = None
        self._layout_analyzer = None
        self._post_processor = None

    def initialize(self) -> bool:
        """Initialize OCR engine and check available backends."""
        if self._initialized:
            return True

        try:
            logger.info("🔬 Initializing Professional OCR Engine...")

            # Check Unstructured API
            self._unstructured_available = self._check_unstructured()
            if self._unstructured_available:
                logger.info("  ✅ Unstructured API (hi_res) — available")
            else:
                logger.warning("  ⚠️ Unstructured API — not available")

            # Check Tesseract
            self._tesseract_available = self._check_tesseract()
            if self._tesseract_available:
                logger.info("  ✅ Tesseract OCR — available")
            else:
                logger.warning("  ⚠️ Tesseract OCR — not available")

            # Initialize sub-components
            from .preprocessor import ImagePreprocessor
            from .table_extractor import TableExtractor
            from .layout_analyzer import LayoutAnalyzer
            from .post_processor import OCRPostProcessor

            self._preprocessor = ImagePreprocessor(
                dpi=self.config.dpi,
                enable_deskew=self.config.enable_deskew,
                enable_denoise=self.config.enable_denoise,
            )

            self._table_extractor = TableExtractor(
                confidence_threshold=self.config.table_detection_threshold,
            )

            self._layout_analyzer = LayoutAnalyzer()

            self._post_processor = OCRPostProcessor(
                min_confidence=self.config.min_confidence_threshold,
            )

            self._initialized = True
            logger.info("✅ Professional OCR Engine initialized")
            return True

        except Exception as e:
            logger.error(f"OCR Engine initialization failed: {e}", exc_info=True)
            return False

    # ── Public API ────────────────────────────────────────────

    def process(
        self,
        file_path: str,
        strategy: Optional[OCRStrategy] = None,
        languages: Optional[List[str]] = None,
        page_range: Optional[Tuple[int, int]] = None,
    ) -> OCRResult:
        """
        Process a document with the specified OCR strategy.

        Args:
            file_path: Path to the document (PDF, image, etc.)
            strategy: OCR strategy to use (default from config)
            languages: Language codes for Tesseract (default from config)
            page_range: Optional (start, end) page range (1-indexed, inclusive)

        Returns:
            OCRResult with extracted text, tables, images
        """
        if not self._initialized:
            self.initialize()

        start_time = time.time()
        strategy = strategy or self.config.default_strategy
        languages = languages or self.config.tesseract_languages
        doc_id = str(uuid.uuid4())

        path = Path(file_path)
        filename = path.name
        file_size_mb = path.stat().st_size / (1024 * 1024)

        logger.info(
            f"📄 OCR Processing: {filename} ({file_size_mb:.1f} MB) "
            f"strategy={strategy.value}"
        )

        # Validate file
        if not path.exists():
            return OCRResult(
                document_id=doc_id,
                filename=filename,
                strategy=strategy,
                success=False,
                error=f"File not found: {file_path}",
            )

        if file_size_mb > self.config.max_file_size_mb:
            return OCRResult(
                document_id=doc_id,
                filename=filename,
                strategy=strategy,
                success=False,
                error=f"File too large: {file_size_mb:.1f} MB (max: {self.config.max_file_size_mb} MB)",
            )

        try:
            # Route to appropriate strategy
            suffix = path.suffix.lower()
            is_pdf = suffix == ".pdf"
            is_image = suffix in {".jpg", ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".webp", ".heif", ".heic"}

            if strategy == OCRStrategy.HI_RES:
                pages = self._process_hires(file_path, is_pdf, page_range)
            elif strategy == OCRStrategy.TESSERACT:
                pages = self._process_tesseract(file_path, is_pdf, languages, page_range)
            elif strategy == OCRStrategy.HYBRID:
                pages = self._process_hybrid(file_path, is_pdf, languages, page_range)
            elif strategy == OCRStrategy.FAST:
                pages = self._process_fast(file_path, is_pdf, page_range)
            else:
                pages = self._process_hires(file_path, is_pdf, page_range)

            # Post-process all pages
            processed_pages = []
            for page in pages:
                processed = self._post_processor.process_page(page)
                processed_pages.append(processed)

            processing_time = (time.time() - start_time) * 1000

            result = OCRResult(
                document_id=doc_id,
                filename=filename,
                strategy=strategy,
                pages=processed_pages,
                processing_time_ms=processing_time,
                metadata={
                    "file_size_mb": round(file_size_mb, 2),
                    "is_pdf": is_pdf,
                    "languages": languages,
                    "unstructured_available": self._unstructured_available,
                    "tesseract_available": self._tesseract_available,
                    "page_range": page_range,
                },
            )

            logger.info(
                f"✅ OCR complete: {result.total_pages} pages, "
                f"{result.total_tables} tables, {result.total_images} images, "
                f"{result.total_characters:,} chars ({processing_time:.0f}ms)"
            )
            return result

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            logger.error(f"OCR processing failed: {e}", exc_info=True)
            return OCRResult(
                document_id=doc_id,
                filename=filename,
                strategy=strategy,
                success=False,
                error=str(e),
                processing_time_ms=processing_time,
            )

    def process_image(
        self,
        image: Image.Image,
        languages: Optional[List[str]] = None,
        strategy: Optional[OCRStrategy] = None,
    ) -> OCRResult:
        """
        Process a PIL Image directly (no file path needed).

        Args:
            image: PIL Image
            languages: OCR languages
            strategy: OCR strategy

        Returns:
            OCRResult with a single page
        """
        if not self._initialized:
            self.initialize()

        # Save to temp file and process
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            image.save(tmp, format="PNG")
            tmp_path = tmp.name

        try:
            result = self.process(
                tmp_path,
                strategy=strategy or OCRStrategy.TESSERACT,
                languages=languages,
            )
            return result
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def get_status(self) -> Dict:
        """Get OCR engine status."""
        return {
            "initialized": self._initialized,
            "unstructured_available": self._unstructured_available,
            "tesseract_available": self._tesseract_available,
            "default_strategy": self.config.default_strategy.value,
            "supported_languages": self.config.tesseract_languages,
            "supported_formats": [
                "pdf", "jpg", "jpeg", "png", "tiff", "tif",
                "bmp", "webp", "heif", "heic",
            ],
            "config": {
                "page_batch_size": self.config.page_batch_size,
                "dpi": self.config.dpi,
                "max_file_size_mb": self.config.max_file_size_mb,
                "min_confidence": self.config.min_confidence_threshold,
            },
        }

    # ── Strategy Implementations ──────────────────────────────

    def _process_hires(
        self, file_path: str, is_pdf: bool, page_range: Optional[Tuple[int, int]]
    ) -> List[OCRPage]:
        """
        Hi-Res strategy via Unstructured API.
        Best for: publications, reports, documents with tables/figures.
        """
        if not self._unstructured_available:
            logger.warning("Unstructured API unavailable, falling back to Tesseract")
            return self._process_tesseract(file_path, is_pdf, self.config.tesseract_languages, page_range)

        if is_pdf:
            return self._hires_pdf(file_path, page_range)
        else:
            return self._hires_image(file_path)

    def _hires_pdf(
        self, file_path: str, page_range: Optional[Tuple[int, int]]
    ) -> List[OCRPage]:
        """Hi-res extraction for PDF documents using batched API calls."""
        from PyPDF2 import PdfReader, PdfWriter

        reader = PdfReader(file_path)
        total_pages = len(reader.pages)
        filename = Path(file_path).name

        # Apply page range
        start_page = (page_range[0] - 1) if page_range else 0
        end_page = page_range[1] if page_range else total_pages
        end_page = min(end_page, total_pages)

        logger.info(
            f"  📖 Hi-res PDF: pages {start_page + 1}–{end_page} "
            f"(batch_size={self.config.page_batch_size})"
        )

        all_pages: List[OCRPage] = []
        batch_size = self.config.page_batch_size

        for batch_start in range(start_page, end_page, batch_size):
            batch_end = min(batch_start + batch_size, end_page)
            batch_num = (batch_start - start_page) // batch_size + 1
            total_batches = ((end_page - start_page) + batch_size - 1) // batch_size

            logger.info(f"  Batch {batch_num}/{total_batches}: pages {batch_start + 1}–{batch_end}")

            # Extract batch pages into temp PDF
            writer = PdfWriter()
            for idx in range(batch_start, batch_end):
                writer.add_page(reader.pages[idx])

            pdf_buffer = io.BytesIO()
            writer.write(pdf_buffer)
            pdf_bytes = pdf_buffer.getvalue()

            try:
                elements = self._send_to_unstructured(
                    pdf_bytes,
                    f"{filename}_batch{batch_num}.pdf",
                    strategy="hi_res",
                )
                batch_pages = self._elements_to_pages(
                    elements, batch_start
                )
                all_pages.extend(batch_pages)

            except Exception as e:
                logger.warning(f"  ⚠️ Batch {batch_num} failed: {e} — PyPDF2 fallback")
                for idx in range(batch_start, batch_end):
                    text = reader.pages[idx].extract_text() or ""
                    if text.strip():
                        page = OCRPage(
                            page_number=idx + 1,
                            full_text=text,
                            confidence=0.6,
                        )
                        page.elements = [
                            PageElement(
                                element_type=PageElementType.TEXT,
                                content=text,
                                page_number=idx + 1,
                                confidence=0.6,
                            )
                        ]
                        all_pages.append(page)

        return all_pages

    def _hires_image(self, file_path: str) -> List[OCRPage]:
        """Hi-res extraction for a single image file."""
        with open(file_path, "rb") as f:
            img_bytes = f.read()

        suffix = Path(file_path).suffix.lower()
        mime_map = {
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".png": "image/png", ".tiff": "image/tiff",
            ".tif": "image/tiff", ".bmp": "image/bmp",
            ".webp": "image/webp",
        }
        mime = mime_map.get(suffix, "application/octet-stream")

        # HEIF needs conversion
        if suffix in {".heif", ".heic"}:
            from pillow_heif import register_heif_opener
            register_heif_opener()
            img = Image.open(file_path)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            img_bytes = buf.getvalue()
            mime = "image/png"

        elements = self._send_to_unstructured(
            img_bytes,
            Path(file_path).name,
            strategy="hi_res",
            content_type=mime,
        )
        return self._elements_to_pages(elements, page_offset=0)

    def _process_tesseract(
        self,
        file_path: str,
        is_pdf: bool,
        languages: List[str],
        page_range: Optional[Tuple[int, int]],
    ) -> List[OCRPage]:
        """
        Tesseract OCR strategy.
        Best for: scanned documents, handwriting, multi-language.
        """
        import pytesseract

        if is_pdf:
            return self._tesseract_pdf(file_path, languages, page_range)
        else:
            return self._tesseract_image(file_path, languages)

    def _tesseract_pdf(
        self,
        file_path: str,
        languages: List[str],
        page_range: Optional[Tuple[int, int]],
    ) -> List[OCRPage]:
        """Process PDF with Tesseract (convert pages to images first)."""
        import pytesseract
        from pdf2image import convert_from_path

        lang_str = "+".join(languages)

        # Determine page range
        first_page = page_range[0] if page_range else None
        last_page = page_range[1] if page_range else None

        images = convert_from_path(
            file_path,
            dpi=self.config.dpi,
            first_page=first_page,
            last_page=last_page,
        )

        pages: List[OCRPage] = []
        start_num = first_page or 1

        for i, img in enumerate(images):
            page_num = start_num + i

            # Preprocess
            processed_img = self._preprocessor.preprocess(img)

            # OCR with full data
            ocr_data = pytesseract.image_to_data(
                processed_img, lang=lang_str, output_type=pytesseract.Output.DICT
            )

            # Build elements from word-level data
            elements = []
            full_text_parts = []
            current_block = -1
            block_text = []

            for j in range(len(ocr_data["text"])):
                word = ocr_data["text"][j].strip()
                conf = int(ocr_data["conf"][j])
                block_num = ocr_data["block_num"][j]

                if block_num != current_block:
                    if block_text:
                        text = " ".join(block_text)
                        full_text_parts.append(text)
                        elements.append(
                            PageElement(
                                element_type=PageElementType.TEXT,
                                content=text,
                                page_number=page_num,
                                confidence=sum(
                                    int(ocr_data["conf"][k])
                                    for k in range(max(0, j - len(block_text)), j)
                                    if int(ocr_data["conf"][k]) > 0
                                ) / max(len(block_text), 1) / 100.0,
                            )
                        )
                        block_text = []
                    current_block = block_num

                if word and conf > 0:
                    block_text.append(word)

            # Flush last block
            if block_text:
                text = " ".join(block_text)
                full_text_parts.append(text)
                elements.append(
                    PageElement(
                        element_type=PageElementType.TEXT,
                        content=text,
                        page_number=page_num,
                        confidence=0.8,
                    )
                )

            full_text = "\n\n".join(full_text_parts)

            # Calculate average confidence
            valid_confs = [int(c) for c in ocr_data["conf"] if int(c) > 0]
            avg_conf = (sum(valid_confs) / len(valid_confs) / 100.0) if valid_confs else 0.0

            page = OCRPage(
                page_number=page_num,
                elements=elements,
                full_text=full_text,
                language=languages[0] if languages else "en",
                confidence=avg_conf,
                width=img.width,
                height=img.height,
            )
            pages.append(page)

        return pages

    def _tesseract_image(
        self, file_path: str, languages: List[str]
    ) -> List[OCRPage]:
        """Process a single image with Tesseract."""
        import pytesseract

        lang_str = "+".join(languages)
        img = Image.open(file_path)

        # Handle HEIF
        suffix = Path(file_path).suffix.lower()
        if suffix in {".heif", ".heic"}:
            from pillow_heif import register_heif_opener
            register_heif_opener()
            img = Image.open(file_path)

        # Preprocess
        processed_img = self._preprocessor.preprocess(img)

        # Full OCR
        text = pytesseract.image_to_string(processed_img, lang=lang_str)
        ocr_data = pytesseract.image_to_data(
            processed_img, lang=lang_str, output_type=pytesseract.Output.DICT
        )

        valid_confs = [int(c) for c in ocr_data["conf"] if int(c) > 0]
        avg_conf = (sum(valid_confs) / len(valid_confs) / 100.0) if valid_confs else 0.0

        page = OCRPage(
            page_number=1,
            full_text=text.strip(),
            language=languages[0] if languages else "en",
            confidence=avg_conf,
            width=img.width,
            height=img.height,
        )
        page.elements = [
            PageElement(
                element_type=PageElementType.TEXT,
                content=text.strip(),
                page_number=1,
                confidence=avg_conf,
            )
        ]

        return [page]

    def _process_hybrid(
        self,
        file_path: str,
        is_pdf: bool,
        languages: List[str],
        page_range: Optional[Tuple[int, int]],
    ) -> List[OCRPage]:
        """
        Hybrid strategy: combine hi_res + Tesseract for max accuracy.
        Cross-validates results and picks the higher-confidence output per page.
        """
        # Run both strategies
        hires_pages = self._process_hires(file_path, is_pdf, page_range)
        tess_pages = self._process_tesseract(file_path, is_pdf, languages, page_range)

        # Build lookup
        tess_map = {p.page_number: p for p in tess_pages}
        merged_pages: List[OCRPage] = []

        for hr_page in hires_pages:
            tess_page = tess_map.get(hr_page.page_number)

            if not tess_page:
                merged_pages.append(hr_page)
                continue

            # Cross-validate: prefer hi_res for layout/tables, Tesseract for raw text
            merged = OCRPage(
                page_number=hr_page.page_number,
                language=hr_page.language or tess_page.language,
                width=hr_page.width or tess_page.width,
                height=hr_page.height or tess_page.height,
            )

            # Use hi_res tables and images (better at structured data)
            merged.tables = hr_page.tables
            merged.images = hr_page.images
            merged.headers = hr_page.headers

            # Use whichever has better confidence for text
            if hr_page.confidence >= tess_page.confidence:
                merged.full_text = hr_page.full_text
                merged.elements = hr_page.elements
                merged.confidence = hr_page.confidence
            else:
                # Merge: keep hi_res tables, use Tesseract text
                text_elements = [
                    e for e in tess_page.elements
                    if e.element_type == PageElementType.TEXT
                ]
                table_elements = [
                    e for e in hr_page.elements
                    if e.element_type == PageElementType.TABLE
                ]
                merged.elements = table_elements + text_elements
                merged.full_text = tess_page.full_text
                merged.confidence = (hr_page.confidence + tess_page.confidence) / 2

            merged_pages.append(merged)

        # Add any Tesseract-only pages
        hr_page_nums = {p.page_number for p in hires_pages}
        for tess_page in tess_pages:
            if tess_page.page_number not in hr_page_nums:
                merged_pages.append(tess_page)

        merged_pages.sort(key=lambda p: p.page_number)
        return merged_pages

    def _process_fast(
        self, file_path: str, is_pdf: bool, page_range: Optional[Tuple[int, int]]
    ) -> List[OCRPage]:
        """
        Fast strategy: PyPDF2 text-only extraction (no OCR).
        Best for: digitally-created PDFs with embedded text.
        """
        if not is_pdf:
            # For images, fall back to Tesseract
            return self._process_tesseract(
                file_path, is_pdf, self.config.tesseract_languages, page_range
            )

        from PyPDF2 import PdfReader

        reader = PdfReader(file_path)
        total_pages = len(reader.pages)
        start = (page_range[0] - 1) if page_range else 0
        end = page_range[1] if page_range else total_pages

        pages: List[OCRPage] = []
        for idx in range(start, min(end, total_pages)):
            text = reader.pages[idx].extract_text() or ""
            if text.strip():
                page = OCRPage(
                    page_number=idx + 1,
                    full_text=text.strip(),
                    confidence=0.9,  # Digital PDF = high confidence
                )
                page.elements = [
                    PageElement(
                        element_type=PageElementType.TEXT,
                        content=text.strip(),
                        page_number=idx + 1,
                        confidence=0.9,
                    )
                ]
                pages.append(page)

        return pages

    # ── Unstructured API Helpers ──────────────────────────────

    def _send_to_unstructured(
        self,
        file_bytes: bytes,
        filename: str,
        strategy: str = "hi_res",
        content_type: str = "application/pdf",
    ) -> List[Dict]:
        """Send file to Unstructured API and return parsed elements."""
        files = {"files": (filename, io.BytesIO(file_bytes), content_type)}
        data = {
            "strategy": strategy,
            "pdf_infer_table_structure": "true",
            "extract_image_block_types": '["Image", "Table"]'
            if self.config.extract_images
            else "[]",
        }

        headers = {}
        if self.config.unstructured_api_key:
            headers["unstructured-api-key"] = self.config.unstructured_api_key

        resp = httpx.post(
            self.config.unstructured_url,
            files=files,
            data=data,
            headers=headers,
            timeout=float(self.config.unstructured_timeout),
        )
        resp.raise_for_status()
        return resp.json()

    def _elements_to_pages(
        self, elements: List[Dict], page_offset: int = 0
    ) -> List[OCRPage]:
        """Convert Unstructured API elements into OCRPage objects."""
        page_map: Dict[int, List[Dict]] = {}
        for elem in elements:
            meta = elem.get("metadata", {})
            batch_page = meta.get("page_number", 1)
            abs_page = page_offset + batch_page
            page_map.setdefault(abs_page, []).append(elem)

        pages: List[OCRPage] = []
        for page_num in sorted(page_map.keys()):
            elems = page_map[page_num]
            ocr_elements: List[PageElement] = []
            text_parts: List[str] = []
            tables: List[PageElement] = []
            images: List[PageElement] = []
            headers: List[PageElement] = []

            for elem in elems:
                elem_type = elem.get("type", "")
                text = elem.get("text", "")
                meta = elem.get("metadata", {})

                # Parse bounding box if available
                coords = meta.get("coordinates", {})
                bbox = None
                if coords and "points" in coords:
                    pts = coords["points"]
                    if len(pts) >= 4:
                        xs = [p[0] for p in pts]
                        ys = [p[1] for p in pts]
                        bbox = BoundingBox(min(xs), min(ys), max(xs), max(ys))

                if elem_type == "Table":
                    html = meta.get("text_as_html", "")
                    pe = PageElement(
                        element_type=PageElementType.TABLE,
                        content=text,
                        page_number=page_num,
                        confidence=0.85,
                        bbox=bbox,
                        html=html,
                        markdown=self._table_html_to_markdown(html) if html else text,
                    )
                    tables.append(pe)
                    ocr_elements.append(pe)
                    text_parts.append(f"[TABLE]\n{text}\n[/TABLE]")

                elif elem_type == "Image":
                    img_text = text or "[Image]"
                    pe = PageElement(
                        element_type=PageElementType.IMAGE,
                        content=img_text,
                        page_number=page_num,
                        confidence=0.7,
                        bbox=bbox,
                    )
                    images.append(pe)
                    ocr_elements.append(pe)
                    if text.strip():
                        text_parts.append(f"[IMAGE: {text}]")

                elif elem_type in {"Header", "Title"}:
                    pe = PageElement(
                        element_type=PageElementType.HEADER,
                        content=text,
                        page_number=page_num,
                        confidence=0.9,
                        bbox=bbox,
                    )
                    headers.append(pe)
                    ocr_elements.append(pe)
                    text_parts.append(f"## {text}")

                elif elem_type == "ListItem":
                    pe = PageElement(
                        element_type=PageElementType.LIST,
                        content=text,
                        page_number=page_num,
                        confidence=0.85,
                        bbox=bbox,
                    )
                    ocr_elements.append(pe)
                    text_parts.append(f"  - {text}")

                elif elem_type == "Formula":
                    pe = PageElement(
                        element_type=PageElementType.FORMULA,
                        content=text,
                        page_number=page_num,
                        confidence=0.75,
                        bbox=bbox,
                    )
                    ocr_elements.append(pe)
                    text_parts.append(f"$$ {text} $$")

                elif elem_type == "PageNumber":
                    pass  # Skip page numbers

                elif text.strip():
                    pe = PageElement(
                        element_type=PageElementType.TEXT,
                        content=text,
                        page_number=page_num,
                        confidence=0.85,
                        bbox=bbox,
                    )
                    ocr_elements.append(pe)
                    text_parts.append(text)

            full_text = "\n\n".join(text_parts)

            # Get page dimensions from metadata if available
            w = h = 0.0
            if elems:
                first_meta = elems[0].get("metadata", {})
                coords = first_meta.get("coordinates", {})
                layout_w = coords.get("layout_width", 0)
                layout_h = coords.get("layout_height", 0)
                if layout_w and layout_h:
                    w, h = float(layout_w), float(layout_h)

            page = OCRPage(
                page_number=page_num,
                elements=ocr_elements,
                full_text=full_text,
                tables=tables,
                images=images,
                headers=headers,
                confidence=0.85,
                width=w,
                height=h,
            )
            pages.append(page)

        return pages

    @staticmethod
    def _table_html_to_markdown(html: str) -> str:
        """Convert HTML table to Markdown format."""
        try:
            from markdownify import markdownify
            return markdownify(html, strip=["img"]).strip()
        except Exception:
            return html

    # ── Health Checks ─────────────────────────────────────────

    def _check_unstructured(self) -> bool:
        """Check if Unstructured API is reachable."""
        try:
            base = self.config.unstructured_url.split("/general/v0")[0]
            resp = httpx.get(f"{base}/healthcheck", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    def _check_tesseract(self) -> bool:
        """Check if Tesseract is installed."""
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False
