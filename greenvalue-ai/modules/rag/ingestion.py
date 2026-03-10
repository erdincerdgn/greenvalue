"""
Enhanced Document Ingestion Pipeline - Hi-Res for All Books
Author: GreenValue AI Team
Purpose: Table-aware, image-aware document processing with batched hi_res
         strategy for PDFs of any size via the Unstructured API.
         Now integrated with the Professional OCR Module for multi-strategy extraction.
"""

import logging
import os
import re
import uuid
import io
import tempfile
import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .config import RAGConfig
from .store import GreenValueDocumentStore

logger = logging.getLogger("greenvalue-rag")

# Suppress noisy PyPDF2 color space warnings
warnings.filterwarnings("ignore", message="Cannot set.*stroke color.*")
logging.getLogger("PyPDF2").setLevel(logging.ERROR)

# Pages per batch when sending large PDFs to Unstructured API
PAGE_BATCH_SIZE = 15

# ─── OCR Module Integration ─────────────────────────────────

_ocr_engine = None


def get_ocr_engine():
    """Lazy-load the OCR engine singleton."""
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from modules.ocr import OCREngine, OCRStrategy
            _ocr_engine = OCREngine()
            _ocr_engine.initialize()
            logger.info("✅ OCR Engine loaded for ingestion pipeline")
        except Exception as e:
            logger.warning(f"OCR Engine not available: {e}")
            _ocr_engine = None
    return _ocr_engine


class TableAwareChunker:
    """
    Advanced chunker that preserves financial tables and construction data.
    Specifically designed for PropTech documents with ROI calculations.
    Supports per-book table extraction rules for the 8-book RAG library.
    """
    
    def __init__(self, config: RAGConfig):
        self.config = config
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.child_chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # Financial table patterns for PropTech (base patterns)
        self.financial_patterns = [
            r'cost.*table|table.*cost',
            r'roi.*calculation|return.*investment',
            r'energy.*saving|efficiency.*cost',
            r'renovation.*budget|retrofit.*cost',
            r'payback.*period|break.*even',
            r'u-value|r-value|thermal.*performance',
            r'kwh.*year|energy.*consumption',
            r'carbon.*emission|co2.*reduction'
        ]

        # ── Per-book specialised table patterns ──────────────
        self.book_table_patterns: Dict[str, List[str]] = {
            # J. Scott — cost tables ($/sqft, cost breakdowns)
            "book_06_costs": [
                r'\$\s*\d+[\.,]\d+.*(?:per|/)\s*(?:sq\s*ft|sf|sqft)',
                r'(?:rehab|renovation|repair)\s+(?:cost|budget)',
                r'(?:contractor|labor|material)\s+(?:cost|estimate)',
                r'(?:scope\s+of\s+(?:work|rehab))',
                r'(?:after[\s-]repair[\s-]value|arv)',
                r'(?:line\s*item|bid\s*sheet|budget\s*template)',
            ],
            # IVS-2025 — appendix tables, standard references
            "book_01_ivs": [
                r'(?:ivs\s*\d{3})',
                r'(?:scope\s+of\s+work|bases?\s+of\s+value)',
                r'(?:market\s+value\s+definition)',
                r'(?:valuation\s+approach(?:es)?)',
                r'(?:adjustment\s+grid|comparable\s+(?:sale|transaction))',
            ],
            # Appraisal 15th — comparable grids, adjustment tables
            "book_02_appraisal": [
                r'(?:comparable|comp)\s+(?:sale|property|adjustment)',
                r'(?:sales?\s+comparison\s+grid)',
                r'(?:cost\s+approach|depreciation\s+schedule)',
                r'(?:income\s+(?:capitali[sz]ation|approach))',
                r'(?:gross\s+rent\s+multiplier|grm)',
                r'(?:highest\s+(?:and|&)\s+best\s+use)',
            ],
            # Sustainable Home Refurbishment — thermal data tables
            "book_03_thermal": [
                r'(?:u[\s-]?value|r[\s-]?value)\s*[\(:]?\s*[\d\.]',
                r'(?:thermal\s+(?:conductivity|resistance|bridging))',
                r'(?:heat\s+loss|heat\s+transfer)',
                r'(?:insulation\s+(?:thickness|material|type))',
                r'(?:energy\s+performance\s+certificate|epc)',
                r'(?:building\s+(?:fabric|envelope))',
                r'w\s*/\s*m\s*[²2]\s*k',
            ],
            # Green Building Illustrated — design specifications
            "book_04_architecture": [
                r'(?:passive\s+design|daylighting)',
                r'(?:solar\s+(?:panel|gain|orientation))',
                r'(?:hvac|ventilation\s+rate)',
                r'(?:building\s+envelope)',
                r'(?:leed|breeam)\s+(?:credit|point)',
            ],
            # Sustainable Construction — LCA / materials data
            "book_05_materials": [
                r'(?:embodied\s+(?:energy|carbon))',
                r'(?:life\s+cycle\s+(?:analysis|assessment|cost)|lca)',
                r'(?:carbon\s+footprint)',
                r'(?:thermal\s+conductivity)\s*[\(:]?\s*[\d\.]',
                r'(?:rock\s*wool|eps|xps|aerogel|cellulose)',
            ],
            # RE Investor — financial formulas, cap rate tables
            "book_07_finance": [
                r'(?:cap\s*(?:itali[sz]ation)?\s*rate)',
                r'(?:noi|net\s+operating\s+income)',
                r'(?:dcf|discounted\s+cash\s+flow)',
                r'(?:irr|internal\s+rate\s+of\s+return)',
                r'(?:npv|net\s+present\s+value)',
                r'(?:cash[\s-]on[\s-]cash\s+return)',
                r'(?:debt\s+service\s+coverage|dscr)',
                r'(?:gross\s+potential\s+income|gpi)',
            ],
            # REALES — glossary definitions
            "book_08_glossary": [
                r'(?:definition|glossary|terminology)',
                r'(?:easement|zoning|lien|title)',
                r'(?:deed|mortgage|encumbrance)',
            ],
        }
    
    def detect_table_content(self, text: str, book_id: Optional[str] = None) -> bool:
        """Detect if text contains tabular financial/construction data.
        
        When a book_id is provided, also checks book-specific patterns.
        """
        table_indicators = [
            '|', '\t', '€', '$', '£',
            'kWh', 'W/m²K', 'ROI', 'NPV', 'IRR',
        ]
        
        indicator_count = sum(1 for indicator in table_indicators if indicator in text)
        
        # Base financial pattern match
        financial_match = any(
            re.search(pattern, text.lower()) 
            for pattern in self.financial_patterns
        )
        
        # Book-specific pattern match
        book_match = False
        if book_id and book_id in self.book_table_patterns:
            book_match = any(
                re.search(pattern, text.lower())
                for pattern in self.book_table_patterns[book_id]
            )
        
        lines = text.split('\n')
        structured_lines = sum(
            1 for line in lines 
            if '|' in line or '\t' in line or any(curr in line for curr in ['€', '$', '£'])
        )
        
        return (
            indicator_count >= 2 or 
            financial_match or 
            book_match or
            structured_lines >= 3
        )
    
    def preserve_table_as_markdown(self, text: str) -> str:
        """Convert detected tables to clean Markdown format."""
        lines = text.split('\n')
        markdown_lines = []
        
        for line in lines:
            if '|' in line:
                cells = [cell.strip() for cell in line.split('|')]
                clean_line = '| ' + ' | '.join(cells) + ' |'
                markdown_lines.append(clean_line)
            elif '\t' in line:
                cells = [cell.strip() for cell in line.split('\t')]
                markdown_line = '| ' + ' | '.join(cells) + ' |'
                markdown_lines.append(markdown_line)
            else:
                markdown_lines.append(line)
        
        return '\n'.join(markdown_lines)
    
    def chunk_with_table_preservation(self, text: str, metadata: Dict) -> List[Document]:
        """Chunk text while preserving financial tables intact.
        
        Uses book_id from metadata (if present) for book-specific
        table detection heuristics.
        """
        book_id = metadata.get("book_id")
        sections = re.split(r'\n\s*\n', text)
        chunks = []
        
        for i, section in enumerate(sections):
            if not section.strip():
                continue
            
            if self.detect_table_content(section, book_id=book_id):
                table_markdown = self.preserve_table_as_markdown(section)
                
                table_metadata = metadata.copy()
                table_metadata.update({
                    'chunk_type': 'table',
                    'contains_financial_data': True,
                    'section_index': i
                })
                
                chunks.append(Document(
                    page_content=table_markdown,
                    metadata=table_metadata
                ))
            
            else:
                text_chunks = self.text_splitter.split_text(section)
                
                for j, chunk_text in enumerate(text_chunks):
                    chunk_metadata = metadata.copy()
                    chunk_metadata.update({
                        'chunk_type': 'text',
                        'section_index': i,
                        'chunk_index': j
                    })
                    
                    chunks.append(Document(
                        page_content=chunk_text,
                        metadata=chunk_metadata
                    ))
        
        return chunks


# ─── Extraction Strategies ────────────────────────────────────


def _check_unstructured_api(api_url: str) -> bool:
    """Check if Unstructured API is reachable."""
    try:
        import httpx
        base = api_url.split("/general/v0")[0]
        resp = httpx.get(f"{base}/healthcheck", timeout=5.0)
        return resp.status_code == 200
    except Exception:
        return False


def _send_pdf_to_api(
    pdf_bytes: bytes,
    filename: str,
    api_url: str,
    strategy: str = "hi_res",
    extract_images: bool = True,
) -> List[Dict]:
    """
    Send a PDF (as bytes) to the Unstructured API and return parsed elements.

    Args:
        pdf_bytes: Raw PDF file content
        filename: Display filename
        api_url: Full API URL (http://host:port/general/v0/general)
        strategy: 'hi_res' or 'fast'
        extract_images: Whether to extract embedded images

    Returns:
        List of element dicts from the API response
    """
    import httpx

    files = {"files": (filename, io.BytesIO(pdf_bytes), "application/pdf")}
    data = {
        "strategy": strategy,
        "pdf_infer_table_structure": "true",
        "extract_image_block_types": '["Image", "Table"]' if extract_images else "[]",
    }

    headers = {}
    api_key = os.getenv("UNSTRUCTURED_API_KEY", "")
    if api_key:
        headers["unstructured-api-key"] = api_key

    resp = httpx.post(api_url, files=files, data=data, headers=headers, timeout=600.0)
    resp.raise_for_status()
    return resp.json()


def _extract_hires_batched(file_path: str, api_url: str) -> List[Dict]:
    """
    Hi-res extraction for any PDF size.

    For large books, splits the PDF into page batches and sends each batch
    to the Unstructured API individually. This prevents OOM and timeout
    issues while still extracting tables and images with hi_res quality.

    Returns:
        List of page dicts with 'text', 'page_number', 'has_tables',
        'tables', and 'images'.
    """
    from PyPDF2 import PdfReader, PdfWriter

    reader = PdfReader(file_path)
    total_pages = len(reader.pages)
    filename = Path(file_path).name
    file_size_mb = Path(file_path).stat().st_size / 1024 / 1024

    logger.info(
        f"  📖 Hi-res batched extraction: {total_pages} pages, "
        f"{file_size_mb:.1f} MB, batch_size={PAGE_BATCH_SIZE}"
    )

    all_pages: List[Dict] = []

    for batch_start in range(0, total_pages, PAGE_BATCH_SIZE):
        batch_end = min(batch_start + PAGE_BATCH_SIZE, total_pages)
        batch_num = batch_start // PAGE_BATCH_SIZE + 1
        total_batches = (total_pages + PAGE_BATCH_SIZE - 1) // PAGE_BATCH_SIZE

        logger.info(
            f"  Batch {batch_num}/{total_batches}: "
            f"pages {batch_start + 1}–{batch_end}"
        )

        # Extract batch pages into a temp PDF
        writer = PdfWriter()
        for page_idx in range(batch_start, batch_end):
            writer.add_page(reader.pages[page_idx])

        pdf_buffer = io.BytesIO()
        writer.write(pdf_buffer)
        pdf_bytes = pdf_buffer.getvalue()

        try:
            # Send batch to Unstructured API with hi_res
            elements = _send_pdf_to_api(
                pdf_bytes=pdf_bytes,
                filename=f"{filename}_batch{batch_num}.pdf",
                api_url=api_url,
                strategy="hi_res",
                extract_images=True,
            )

            # Group elements by page (relative to batch)
            page_map: Dict[int, List] = {}
            for elem in elements:
                meta = elem.get("metadata", {})
                # Page number within the batch (1-indexed)
                batch_page = meta.get("page_number", 1)
                # Convert to absolute page number
                abs_page = batch_start + batch_page
                if abs_page not in page_map:
                    page_map[abs_page] = []
                page_map[abs_page].append(elem)

            # Process each page
            for page_num in sorted(page_map.keys()):
                elems = page_map[page_num]
                texts = []
                tables = []
                images = []
                has_tables = False

                for elem in elems:
                    elem_type = elem.get("type", "")
                    text = elem.get("text", "")
                    metadata = elem.get("metadata", {})

                    if elem_type == "Table":
                        has_tables = True
                        # Get HTML table if available
                        html = metadata.get("text_as_html", "")
                        tables.append({
                            "text": text,
                            "html": html,
                            "page": page_num,
                        })
                        texts.append(f"[TABLE]\n{text}\n[/TABLE]")

                    elif elem_type == "Image":
                        # Image element — store description/caption
                        img_text = text or "[Image: building/diagram]"
                        images.append({
                            "description": img_text,
                            "page": page_num,
                        })
                        if text.strip():
                            texts.append(f"[IMAGE: {text}]")

                    elif text.strip():
                        texts.append(text)

                full_text = "\n\n".join(texts)
                if full_text.strip():
                    all_pages.append({
                        "text": full_text,
                        "page_number": page_num,
                        "has_tables": has_tables,
                        "tables": tables,
                        "images": images,
                    })

        except Exception as e:
            logger.warning(
                f"  ⚠️ Batch {batch_num} API failed: {e}. "
                f"Falling back to PyPDF2 for pages {batch_start+1}–{batch_end}"
            )
            # Fallback: extract text with PyPDF2 for this batch
            for page_idx in range(batch_start, batch_end):
                text = reader.pages[page_idx].extract_text() or ""
                if text.strip():
                    all_pages.append({
                        "text": text,
                        "page_number": page_idx + 1,
                        "has_tables": False,
                        "tables": [],
                        "images": [],
                    })

    logger.info(
        f"  ✅ Extracted {len(all_pages)} pages "
        f"({sum(len(p.get('tables', [])) for p in all_pages)} tables, "
        f"{sum(len(p.get('images', [])) for p in all_pages)} images)"
    )
    return all_pages


def _extract_text_pypdf2(file_path: str) -> List[Dict]:
    """
    Fallback: Extract text page-by-page using PyPDF2.
    No table/image extraction, but always works.
    """
    from PyPDF2 import PdfReader

    reader = PdfReader(file_path)
    total_pages = len(reader.pages)
    logger.info(f"  PyPDF2 fallback: {total_pages} pages")

    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages.append({
                "text": text,
                "page_number": i + 1,
                "has_tables": False,
                "tables": [],
                "images": [],
            })

    return pages


# ─── OCR Result → Page Dict Converter ─────────────────────────


def _ocr_result_to_pages(ocr_result) -> List[Dict]:
    """
    Convert OCRResult (from Professional OCR Module) into the page-dict
    format expected by the rest of the ingestion pipeline.

    Each dict contains:
      text, page_number, has_tables, tables, images
    """
    pages: List[Dict] = []

    for ocr_page in ocr_result.pages:
        tables = []
        images = []

        for table_elem in ocr_page.tables:
            tables.append({
                "text": table_elem.content,
                "html": table_elem.html or "",
                "markdown": table_elem.markdown or table_elem.content,
                "page": ocr_page.page_number,
                "confidence": table_elem.confidence,
            })

        for image_elem in ocr_page.images:
            images.append({
                "description": image_elem.content or "[Image: building/diagram]",
                "page": ocr_page.page_number,
            })

        if ocr_page.full_text.strip():
            pages.append({
                "text": ocr_page.full_text,
                "page_number": ocr_page.page_number,
                "has_tables": ocr_page.has_tables,
                "tables": tables,
                "images": images,
                "confidence": ocr_page.confidence,
            })

    return pages


# ─── Main Ingestion Pipeline ─────────────────────────────────


class EnhancedDocumentIngestionPipeline:
    """
    Professional document ingestion with hi-res extraction for all book sizes.
    Uses the Professional OCR Module (preferred) or batched Unstructured API
    calls to extract tables & images.
    """
    
    def __init__(
        self,
        config: Optional[RAGConfig] = None,
        store: Optional[GreenValueDocumentStore] = None
    ):
        self.config = config or RAGConfig()
        self.store = store
        self.chunker = TableAwareChunker(self.config)
        self._ocr_engine = None  # lazy-loaded OCR engine
        
        self.proptech_categories = {
            'valuation': ['ivs', 'appraisal', 'valuation', 'market'],
            'energy': ['energy', 'efficiency', 'thermal', 'insulation', 'u-value'],
            'finance': ['roi', 'cost', 'investment', 'budget', 'payback'],
            'retrofit': ['renovation', 'retrofit', 'upgrade', 'improvement'],
            'sustainability': ['green', 'sustainable', 'carbon', 'emission', 'eco'],
            'legal': ['regulation', 'compliance', 'standard', 'code', 'law']
        }
    
    def classify_document_category(self, text: str, filename: str) -> str:
        """Classify document into PropTech categories."""
        text_lower = text[:5000].lower()
        filename_lower = filename.lower()
        
        category_scores = {}
        for category, keywords in self.proptech_categories.items():
            score = sum(text_lower.count(kw) * 2 for kw in keywords)
            score += sum(filename_lower.count(kw) * 5 for kw in keywords)
            category_scores[category] = score
        
        best = max(category_scores, key=category_scores.get)
        return best if category_scores[best] > 0 else 'real_estate'
    
    def extract_financial_metadata(self, text: str) -> Dict:
        """Extract financial and energy efficiency metadata from sample text."""
        sample = text[:10000]
        metadata = {}
        
        currencies = ['€', '$', '£', 'USD', 'EUR', 'GBP']
        found = [c for c in currencies if c in sample]
        if found:
            metadata['currencies'] = found
        
        patterns = {
            'u_values': r'U-value[s]?\s*[:\-]?\s*([\d.,]+)',
            'r_values': r'R-value[s]?\s*[:\-]?\s*([\d.,]+)',
            'energy_consumption': r'([\d.,]+)\s*kWh',
            'co2_emissions': r'([\d.,]+)\s*(?:kg\s*)?CO2'
        }
        
        for key, pattern in patterns.items():
            matches = re.findall(pattern, sample, re.IGNORECASE)
            if matches:
                metadata[key] = matches[:5]
        
        roi_terms = ['payback period', 'return on investment', 'roi', 'npv', 'irr']
        found_roi = [t for t in roi_terms if t in sample.lower()]
        if found_roi:
            metadata['contains_roi_analysis'] = True
            metadata['roi_indicators'] = found_roi
        
        return metadata

    def process_pdf(self, file_path: str) -> Tuple[List[Document], List[Document]]:
        """
        Process any PDF with hi_res quality.
        
        Strategy (prioritized):
        1. Professional OCR Engine (hi_res/hybrid/tesseract/fast)
        2. Inline Unstructured API batched extraction (legacy fallback)
        3. PyPDF2 text-only extraction (final fallback)
        """
        filename = Path(file_path).name
        file_size = Path(file_path).stat().st_size
        file_size_mb = file_size / 1024 / 1024
        logger.info(f"📄 Processing: {filename} ({file_size_mb:.1f} MB)")
        
        try:
            extraction_strategy = "unknown"
            pages: List[Dict] = []

            # ── Strategy 1: Professional OCR Engine ──────────────
            ocr_engine = get_ocr_engine()
            if ocr_engine is not None:
                try:
                    from modules.ocr import OCRStrategy
                    strategy_name = getattr(self.config, "ocr_default_strategy", "hi_res")
                    strategy_map = {
                        "hi_res": OCRStrategy.HI_RES,
                        "tesseract": OCRStrategy.TESSERACT,
                        "hybrid": OCRStrategy.HYBRID,
                        "fast": OCRStrategy.FAST,
                    }
                    ocr_strategy = strategy_map.get(strategy_name, OCRStrategy.HI_RES)

                    logger.info(
                        f"  🔬 Using Professional OCR Engine "
                        f"(strategy={ocr_strategy.value})"
                    )

                    ocr_languages = getattr(self.config, "ocr_languages", None)
                    if isinstance(ocr_languages, str):
                        ocr_languages = [l.strip() for l in ocr_languages.split(",")]

                    ocr_result = ocr_engine.process(
                        file_path,
                        strategy=ocr_strategy,
                        languages=ocr_languages,
                    )

                    if ocr_result.success and ocr_result.pages:
                        pages = _ocr_result_to_pages(ocr_result)
                        extraction_strategy = f"ocr_{ocr_strategy.value}"
                        logger.info(
                            f"  ✅ OCR Engine: {len(pages)} pages, "
                            f"{ocr_result.total_tables} tables, "
                            f"{ocr_result.total_images} images "
                            f"({ocr_result.processing_time_ms:.0f}ms)"
                        )
                    else:
                        logger.warning(
                            f"  ⚠️ OCR Engine returned no content "
                            f"(error={ocr_result.error}), falling back..."
                        )
                except Exception as e:
                    logger.warning(f"  ⚠️ OCR Engine failed: {e}, falling back...")

            # ── Strategy 2: Inline Unstructured API (legacy) ─────
            if not pages:
                api_url = self.config.unstructured_url
                api_ok = _check_unstructured_api(api_url)
                if api_ok:
                    logger.info(f"  🔬 Using Unstructured API (hi_res) at {api_url}")
                    pages = _extract_hires_batched(file_path, api_url)
                    extraction_strategy = "hi_res_legacy"

            # ── Strategy 3: PyPDF2 fallback ──────────────────────
            if not pages:
                logger.warning("  ⚠️ Using PyPDF2 fallback (text only)")
                pages = _extract_text_pypdf2(file_path)
                extraction_strategy = "pypdf2"
            
            if not pages:
                logger.warning(f"  No content extracted from {filename}")
                return [], []
            
            total_pages = len(pages)
            total_chars = sum(len(p["text"]) for p in pages)
            total_tables = sum(len(p.get("tables", [])) for p in pages)
            total_images = sum(len(p.get("images", [])) for p in pages)
            
            logger.info(
                f"  → {total_pages} pages, {total_chars:,} chars, "
                f"{total_tables} tables, {total_images} images"
            )
            
            # Sample text for classification
            sample_text = "\n".join(p["text"] for p in (pages[:3] + pages[-2:]))
            
            # Build metadata
            parent_id = str(uuid.uuid4())
            category = self.classify_document_category(sample_text, filename)
            
            base_metadata = {
                'source_file': filename,
                'file_path': str(file_path),
                'category': category,
                'total_pages': total_pages,
                'file_size_mb': round(file_size_mb, 1),
                'extraction_strategy': extraction_strategy,
                'parent_id': parent_id,
                'has_tables': total_tables > 0,
                'table_count': total_tables,
                'image_count': total_images,
            }

            # ── Book-Aware Metadata (RAG Knowledge Library) ──
            try:
                from .router import identify_book_from_filename
                book_info = identify_book_from_filename(filename)
                if book_info:
                    base_metadata['book_id'] = book_info['book_id']
                    base_metadata['book_title'] = book_info['title']
                    base_metadata['book_authority'] = book_info['authority']
                    base_metadata['expertise_domain'] = book_info['expertise']
                    base_metadata['chain_role'] = book_info['chain_role']
                    base_metadata['book_domains'] = [
                        d.value for d in book_info['domains']
                    ]
                    logger.info(
                        f"  📚 Matched to book: {book_info['title']} "
                        f"(authority={book_info['authority']})"
                    )
            except Exception as e:
                logger.debug(f"Book identification skipped: {e}")

            financial_meta = self.extract_financial_metadata(sample_text)
            base_metadata.update(financial_meta)
            
            # Parent document (summary from first pages)
            parent_text = "\n\n".join(p["text"] for p in pages[:5])
            if len(parent_text) > self.config.parent_chunk_size * 3:
                parent_text = parent_text[:self.config.parent_chunk_size * 3]
            
            parent_doc = Document(
                page_content=parent_text,
                metadata={**base_metadata, 'doc_type': 'parent'}
            )
            
            # Child chunks — page by page
            all_child_chunks = []
            
            for page_info in pages:
                page_text = page_info["text"]
                page_num = page_info["page_number"]
                
                page_metadata = {
                    **base_metadata,
                    'doc_type': 'child',
                    'page_number': page_num,
                    'has_tables': page_info.get("has_tables", False),
                }
                
                # Add table-specific chunks (high priority)
                for tbl in page_info.get("tables", []):
                    tbl_meta = page_metadata.copy()
                    tbl_meta.update({
                        'chunk_type': 'table',
                        'contains_financial_data': True,
                        'priority': 'high',
                    })
                    all_child_chunks.append(Document(
                        page_content=tbl["text"],
                        metadata=tbl_meta,
                    ))
                
                # Add image description chunks
                for img in page_info.get("images", []):
                    if img.get("description", "").strip():
                        img_meta = page_metadata.copy()
                        img_meta.update({
                            'chunk_type': 'image_description',
                        })
                        all_child_chunks.append(Document(
                            page_content=img["description"],
                            metadata=img_meta,
                        ))
                
                # Chunk the main text
                page_chunks = self.chunker.chunk_with_table_preservation(
                    page_text, page_metadata
                )
                all_child_chunks.extend(page_chunks)
            
            logger.info(
                f"  ✅ {filename}: {len(all_child_chunks)} chunks "
                f"(category: {category})"
            )
            
            return [parent_doc], all_child_chunks
            
        except Exception as e:
            logger.error(f"PDF processing failed for {filename}: {e}", exc_info=True)
            return [], []
    
    # Backward compat alias
    def process_pdf_with_tables(self, file_path: str) -> Tuple[List[Document], List[Document]]:
        return self.process_pdf(file_path)
    
    def ingest_file(self, file_path: str) -> Dict:
        """Ingest a single file."""
        if not self.store:
            return {"success": False, "error": "Store not initialized"}
        
        try:
            parent_docs, child_docs = self.process_pdf(file_path)
            
            if not parent_docs or not child_docs:
                return {"success": False, "error": "No content extracted"}
            
            parent_count = self.store.add_documents(
                parent_docs, 
                collection=self.config.parent_collection
            )
            
            child_count = self.store.add_documents(
                child_docs,
                collection=self.config.child_collection
            )
            
            result = {
                "success": True,
                "file": Path(file_path).name,
                "parent_docs": parent_count,
                "child_docs": child_count,
                "tables_extracted": sum(
                    1 for d in child_docs if d.metadata.get('chunk_type') == 'table'
                ),
                "images_extracted": sum(
                    1 for d in child_docs if d.metadata.get('chunk_type') == 'image_description'
                ),
                "category": parent_docs[0].metadata.get('category'),
                "total_pages": parent_docs[0].metadata.get('total_pages', 0),
            }
            
            logger.info(f"✅ Ingested: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            return {"success": False, "error": str(e)}
    
    def ingest_directory(
        self,
        directory: str = None,
        force_recreate: bool = False
    ) -> Dict:
        """Ingest all PDFs in a directory."""
        if directory is None:
            directory = self.config.knowledge_base_path
            
        if not self.store:
            return {"success": False, "error": "Store not initialized"}
        
        if not self.store.setup_collections(force_recreate=force_recreate):
            return {"success": False, "error": "Failed to setup collections"}
        
        pdf_files = sorted(
            list(Path(directory).glob("*.pdf")) + list(Path(directory).glob("*.PDF")),
            key=lambda f: f.stat().st_size,  # smallest first
        )
        
        if not pdf_files:
            return {"success": False, "error": "No PDF files found"}
        
        total_size = sum(f.stat().st_size for f in pdf_files) / 1024 / 1024
        logger.info(f"🚀 Processing {len(pdf_files)} PDFs ({total_size:.1f} MB)")
        
        results = []
        total_tables = 0
        total_images = 0
        total_chunks = 0
        
        for i, pdf_file in enumerate(pdf_files, 1):
            size_mb = pdf_file.stat().st_size / 1024 / 1024
            logger.info(f"\n{'='*60}")
            logger.info(f"[{i}/{len(pdf_files)}] {pdf_file.name} ({size_mb:.1f} MB)")
            
            result = self.ingest_file(str(pdf_file))
            results.append(result)
            
            if result.get("success"):
                total_tables += result.get("tables_extracted", 0)
                total_images += result.get("images_extracted", 0)
                total_chunks += result.get("child_docs", 0)
        
        successful = [r for r in results if r.get("success")]
        
        summary = {
            "success": True,
            "total_files": len(pdf_files),
            "successful": len(successful),
            "failed": len(pdf_files) - len(successful),
            "total_chunks": total_chunks,
            "total_tables": total_tables,
            "total_images": total_images,
            "results": results,
        }
        
        logger.info(
            f"\n🎯 Done: {len(successful)}/{len(pdf_files)} files, "
            f"{total_chunks} chunks, {total_tables} tables, {total_images} images"
        )
        return summary
