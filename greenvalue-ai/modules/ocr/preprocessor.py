"""
Image Preprocessor for OCR
Author: GreenValue AI Team
Purpose: Deskew, denoise, and enhance document images before OCR.
"""

import logging
from typing import Optional

import numpy as np
from PIL import Image, ImageFilter, ImageEnhance, ImageOps

logger = logging.getLogger("greenvalue-ocr")


class ImagePreprocessor:
    """
    Preprocess document images for optimal OCR accuracy.

    Pipeline:
        1. Convert to RGB (handle RGBA, grayscale, palette)
        2. Auto-orient (EXIF rotation)
        3. Deskew (straighten rotated scans)
        4. Denoise (reduce scan artifacts)
        5. Binarize (adaptive thresholding)
        6. Enhance contrast and sharpness
    """

    def __init__(
        self,
        dpi: int = 300,
        enable_deskew: bool = True,
        enable_denoise: bool = True,
        target_size: Optional[int] = None,
    ):
        self.dpi = dpi
        self.enable_deskew = enable_deskew
        self.enable_denoise = enable_denoise
        self.target_size = target_size  # Max dimension, None = keep original

    def preprocess(self, image: Image.Image) -> Image.Image:
        """
        Full preprocessing pipeline for OCR.

        Args:
            image: Input PIL Image

        Returns:
            Preprocessed PIL Image optimized for OCR
        """
        try:
            # Step 1: Auto-orient based on EXIF
            image = ImageOps.exif_transpose(image)

            # Step 2: Convert to RGB
            if image.mode == "RGBA":
                # Composite on white background
                bg = Image.new("RGB", image.size, (255, 255, 255))
                bg.paste(image, mask=image.split()[3])
                image = bg
            elif image.mode != "RGB":
                image = image.convert("RGB")

            # Step 3: Resize if needed (preserve aspect ratio)
            if self.target_size and max(image.size) > self.target_size:
                image.thumbnail(
                    (self.target_size, self.target_size), Image.LANCZOS
                )

            # Step 4: Deskew
            if self.enable_deskew:
                image = self._deskew(image)

            # Step 5: Denoise
            if self.enable_denoise:
                image = self._denoise(image)

            # Step 6: Enhance for OCR
            image = self._enhance(image)

            return image

        except Exception as e:
            logger.warning(f"Preprocessing failed, returning original: {e}")
            if image.mode != "RGB":
                image = image.convert("RGB")
            return image

    def preprocess_for_table(self, image: Image.Image) -> Image.Image:
        """
        Specialized preprocessing for table detection.
        Enhances lines and grid structures.
        """
        try:
            image = ImageOps.exif_transpose(image)
            if image.mode != "RGB":
                image = image.convert("RGB")

            # Increase contrast more aggressively for grid lines
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)

            # Sharpen to make lines clearer
            image = image.filter(ImageFilter.SHARPEN)
            image = image.filter(ImageFilter.SHARPEN)

            return image

        except Exception as e:
            logger.warning(f"Table preprocessing failed: {e}")
            return image

    def _deskew(self, image: Image.Image) -> Image.Image:
        """
        Detect and correct document skew angle.
        Uses projection profile analysis for fast deskewing.
        """
        try:
            # Convert to grayscale for analysis
            gray = image.convert("L")
            gray_np = np.array(gray)

            # Binarize
            threshold = np.mean(gray_np)
            binary = (gray_np < threshold).astype(np.uint8)

            # Try small rotation angles and find the one with best horizontal projection
            best_angle = 0.0
            best_score = 0.0

            for angle_10x in range(-50, 51, 5):  # -5.0 to +5.0 degrees in 0.5 steps
                angle = angle_10x / 10.0
                rotated = image.rotate(angle, fillcolor=(255, 255, 255), expand=False)
                rot_gray = np.array(rotated.convert("L"))
                rot_binary = (rot_gray < threshold).astype(np.uint8)

                # Horizontal projection profile
                h_proj = np.sum(rot_binary, axis=1)

                # Score: variance of projection (high = well-aligned rows)
                score = np.var(h_proj)

                if score > best_score:
                    best_score = score
                    best_angle = angle

            if abs(best_angle) > 0.3:
                logger.debug(f"  Deskew: rotating {best_angle:.1f}°")
                image = image.rotate(
                    best_angle, fillcolor=(255, 255, 255), expand=False
                )

            return image

        except Exception as e:
            logger.debug(f"Deskew skipped: {e}")
            return image

    def _denoise(self, image: Image.Image) -> Image.Image:
        """Remove scan noise while preserving text edges."""
        try:
            # Median filter removes salt-and-pepper noise
            image = image.filter(ImageFilter.MedianFilter(size=3))
            return image
        except Exception:
            return image

    def _enhance(self, image: Image.Image) -> Image.Image:
        """Enhance contrast and sharpness for OCR."""
        try:
            # Boost contrast
            contrast = ImageEnhance.Contrast(image)
            image = contrast.enhance(1.5)

            # Sharpen slightly
            sharpness = ImageEnhance.Sharpness(image)
            image = sharpness.enhance(1.3)

            # Slight brightness adjustment (ensure text is dark on light)
            brightness = ImageEnhance.Brightness(image)
            image = brightness.enhance(1.1)

            return image

        except Exception:
            return image
