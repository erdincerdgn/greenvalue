# ============================================================
# GreenValue AI Engine - YOLO Inference Module
# Vision/Segmentation with YOLOv11
# ============================================================

import time
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import torch
from ultralytics import YOLO
from PIL import Image

from config.settings import get_settings

logger = logging.getLogger(__name__)


# Building component classes that YOLO will be trained to detect
COMPONENT_CLASSES = {
    0: "window",
    1: "door",
    2: "facade",
    3: "roof",
    4: "balcony",
    5: "insulation",
    6: "solar_panel",
}


class YOLOInferenceEngine:
    """YOLO11 Instance Segmentation engine for building component detection."""

    def __init__(self):
        self.settings = get_settings()
        self.model: Optional[YOLO] = None
        self.device: str = self.settings.resolved_device
        self._model_info: dict = {}

    @property
    def model_version(self) -> Optional[str]:
        return self._model_info.get("model_version", self.settings.yolo_model_name)

    @property
    def gpu_info(self) -> Optional[dict]:
        if self._model_info.get("gpu_available"):
            return {
                "name": self._model_info.get("gpu_name"),
                "memory_mb": self._model_info.get("gpu_memory_mb"),
            }
        return None

    def load_model(self) -> None:
        """Load the YOLO model based on configuration."""
        model_name = self.settings.yolo_model_name
        weights_path = Path(self.settings.yolo_model_path)

        logger.info(f"Loading YOLO model: {model_name} on device: {self.device}")

        if weights_path.exists():
            # Load from local weights (custom trained)
            logger.info(f"Loading custom weights from: {weights_path}")
            self.model = YOLO(str(weights_path))
        else:
            # Download pretrained model (first run)
            logger.info(f"Downloading pretrained model: {model_name}.pt")
            self.model = YOLO(f"{model_name}.pt")
            # Save to weights directory for persistence
            weights_path.parent.mkdir(parents=True, exist_ok=True)

        # Move model to device
        if self.device == "cuda" and torch.cuda.is_available():
            self.model.to("cuda")
            gpu_name = torch.cuda.get_device_name(0)
            gpu_memory = torch.cuda.get_device_properties(0).total_memory // (1024 * 1024)
            logger.info(f"GPU loaded: {gpu_name} ({gpu_memory} MB VRAM)")
            self._model_info = {
                "gpu_available": True,
                "gpu_name": gpu_name,
                "gpu_memory_mb": gpu_memory,
            }
        else:
            logger.warning("Running on CPU - inference will be slower")
            self._model_info = {"gpu_available": False, "gpu_name": "N/A", "gpu_memory_mb": 0}

        self._model_info["model_loaded"] = model_name
        logger.info(f"YOLO model loaded successfully: {model_name}")

    def predict(
        self,
        image: np.ndarray | Image.Image,
        confidence: Optional[float] = None,
        iou: Optional[float] = None,
    ) -> dict:
        """
        Run YOLO instance segmentation on an image.

        Args:
            image: Input image (numpy array or PIL Image)
            confidence: Confidence threshold override
            iou: IoU threshold override

        Returns:
            Dict with detections, metadata, and timing info
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        conf = confidence or self.settings.yolo_confidence_threshold
        iou_thresh = iou or self.settings.yolo_iou_threshold

        start_time = time.perf_counter()

        # Run inference
        results = self.model.predict(
            source=image,
            conf=conf,
            iou=iou_thresh,
            device=self.device,
            verbose=False,
            retina_masks=True,
        )

        inference_time = (time.perf_counter() - start_time) * 1000  # ms

        # Parse results
        detections = self._parse_results(results[0])

        # Get image metadata
        if isinstance(image, np.ndarray):
            h, w = image.shape[:2]
        else:
            w, h = image.size

        return {
            "detections": detections,
            "inference_time_ms": round(inference_time, 2),
            "model_version": self.settings.yolo_model_name,
            "image_metadata": {
                "width": w,
                "height": h,
                "format": "rgb",
            },
            "device": self.device,
        }

    def _parse_results(self, result) -> list[dict]:
        """Parse YOLO result into structured detection list."""
        detections = []

        if result.boxes is None:
            return detections

        boxes = result.boxes
        masks = result.masks

        for i in range(len(boxes)):
            box = boxes[i]
            cls_id = int(box.cls[0].item())
            confidence = float(box.conf[0].item())

            # Bounding box coordinates
            x1, y1, x2, y2 = box.xyxy[0].tolist()

            detection = {
                "class_id": cls_id,
                "class_name": COMPONENT_CLASSES.get(cls_id, f"class_{cls_id}"),
                "confidence": round(confidence, 4),
                "bbox": {
                    "x_min": round(x1, 2),
                    "y_min": round(y1, 2),
                    "x_max": round(x2, 2),
                    "y_max": round(y2, 2),
                },
                "area_pixels": round((x2 - x1) * (y2 - y1), 2),
            }

            # Add segmentation mask polygon if available
            if masks is not None and i < len(masks):
                mask_xy = masks[i].xy
                if len(mask_xy) > 0:
                    polygon = mask_xy[0].flatten().tolist()
                    detection["mask_polygon"] = [round(p, 2) for p in polygon]

            detections.append(detection)

        # Sort by confidence descending
        detections.sort(key=lambda d: d["confidence"], reverse=True)
        return detections

    @property
    def model_info(self) -> dict:
        """Return model and GPU information."""
        return self._model_info

    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded."""
        return self.model is not None


# Singleton instance
_engine: Optional[YOLOInferenceEngine] = None


def get_inference_engine() -> YOLOInferenceEngine:
    """Get or create the singleton inference engine."""
    global _engine
    if _engine is None:
        _engine = YOLOInferenceEngine()
    return _engine
