# ============================================================
# GreenValue AI Engine - Analysis Pipeline Orchestrator
# Coordinates the full Scan-to-Value pipeline
# ============================================================

import time
import logging
import uuid
from io import BytesIO
from typing import Optional

from PIL import Image
import numpy as np

from modules.vision.inference import get_inference_engine
from modules.vision.heatmap import HeatmapGenerator
from modules.physics.u_value import PhysicsEngine
from modules.storage.minio_client import get_storage_service

logger = logging.getLogger(__name__)


class AnalysisPipeline:
    """
    Orchestrates the full image analysis pipeline:
    1. Download image from MinIO
    2. Run YOLO inference (detection + segmentation)
    3. Calculate U-Values (physics engine)
    4. Generate heatmap visualization
    5. Upload results to MinIO
    """

    def __init__(self):
        self.engine = get_inference_engine()
        self.physics = PhysicsEngine()
        self.heatmap_gen = HeatmapGenerator()
        self.storage = get_storage_service()

    async def run(
        self,
        job_id: str,
        file_key: str,
        property_id: str,
        model_size: Optional[str] = None,
    ) -> dict:
        """
        Execute the full analysis pipeline.

        Args:
            job_id: Unique job identifier
            file_key: MinIO object key for the source image
            property_id: Property UUID
            model_size: Optional YOLO model size override

        Returns:
            Complete analysis result dict
        """
        pipeline_start = time.perf_counter()
        logger.info(f"[{job_id}] Pipeline started for property {property_id}")

        # Step 1: Download image from MinIO
        logger.info(f"[{job_id}] Step 1/5: Downloading image...")
        image_bytes = self.storage.download_image(file_key)
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        image_np = np.array(image)

        # Step 2: YOLO inference
        logger.info(f"[{job_id}] Step 2/5: Running YOLO inference...")
        inference_result = self.engine.predict(image_np)
        detections = inference_result["detections"]
        logger.info(
            f"[{job_id}] Detected {len(detections)} components "
            f"in {inference_result['inference_time_ms']:.1f}ms"
        )

        # Step 3: Physics engine (U-Value calculations)
        logger.info(f"[{job_id}] Step 3/5: Calculating U-Values...")
        physics_result = self.physics.analyze_components(detections)

        # Step 4: Generate heatmap
        logger.info(f"[{job_id}] Step 4/5: Generating heatmap...")
        u_values = {
            i: comp["u_value"]
            for i, comp in enumerate(physics_result["components"])
        }
        heatmap_bytes = self.heatmap_gen.generate(image_np, detections, u_values)

        # Step 5: Upload heatmap to MinIO
        logger.info(f"[{job_id}] Step 5/5: Uploading results...")
        heatmap_key = f"{property_id}/{job_id}_heatmap.png"
        self.storage.upload_heatmap(heatmap_key, heatmap_bytes)

        pipeline_time = (time.perf_counter() - pipeline_start) * 1000

        # Assemble final result
        result = {
            "job_id": job_id,
            "property_id": property_id,
            "status": "completed",
            "inference": {
                "detections": detections,
                "inference_time_ms": inference_result["inference_time_ms"],
                "model_version": inference_result["model_version"],
                "device": inference_result["device"],
            },
            "physics": physics_result,
            "artifacts": {
                "heatmap_key": heatmap_key,
                "source_image_key": file_key,
            },
            "image_metadata": inference_result["image_metadata"],
            "pipeline_time_ms": round(pipeline_time, 2),
        }

        logger.info(
            f"[{job_id}] Pipeline completed in {pipeline_time:.0f}ms | "
            f"Label: {physics_result['energy_label']} | "
            f"U-Value: {physics_result['overall_u_value']}"
        )

        return result

    async def analyze_image_only(self, image_bytes: bytes) -> dict:
        """
        Quick analysis endpoint — runs detection without MinIO or job queue.
        Used for the REST API upload endpoint.
        """
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        image_np = np.array(image)

        # Inference
        inference_result = self.engine.predict(image_np)
        detections = inference_result["detections"]

        # Physics
        physics_result = self.physics.analyze_components(detections)

        return {
            "detections": detections,
            "inference_time_ms": inference_result["inference_time_ms"],
            "model_version": inference_result["model_version"],
            "physics": physics_result,
            "image_metadata": inference_result["image_metadata"],
        }
