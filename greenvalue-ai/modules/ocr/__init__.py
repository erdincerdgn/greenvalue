"""
GreenValue AI — Professional OCR Module
Enterprise-grade document processing with hi_res strategy for major publications.
Supports PDF, images (JPEG/PNG/TIFF/HEIF), and scanned documents.
"""

from .engine import OCREngine, OCRResult, OCRStrategy
from .preprocessor import ImagePreprocessor
from .table_extractor import TableExtractor
from .layout_analyzer import LayoutAnalyzer
from .post_processor import OCRPostProcessor

__all__ = [
    "OCREngine",
    "OCRResult",
    "OCRStrategy",
    "ImagePreprocessor",
    "TableExtractor",
    "LayoutAnalyzer",
    "OCRPostProcessor",
]
