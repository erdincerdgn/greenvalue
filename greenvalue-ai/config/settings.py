# ============================================================
# GreenValue AI Engine - Application Settings
# Pydantic-based configuration from environment variables
# ============================================================

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Central configuration loaded from environment variables / .env file."""

    # --- Application ---
    app_name: str = "GreenValue AI Engine"
    app_env: str = Field(default="development", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    debug: bool = Field(default=False)

    # --- FastAPI Server ---
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    workers: int = Field(default=1)

    # --- gRPC Server ---
    grpc_port: int = Field(default=50051, alias="GRPC_PORT")

    # --- YOLO Model ---
    yolo_model_size: str = Field(default="m", alias="YOLO_MODEL_SIZE")
    yolo_confidence_threshold: float = Field(default=0.25, alias="YOLO_CONFIDENCE")
    yolo_iou_threshold: float = Field(default=0.45, alias="YOLO_IOU")
    yolo_weights_dir: str = Field(default="/app/data/yolo_weights", alias="YOLO_WEIGHTS_DIR")

    # --- GPU / CUDA ---
    device: str = Field(default="auto", alias="DEVICE")  # auto, cuda, cpu

    # --- Redis (BullMQ Queue) ---
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")

    # --- MinIO (S3 Object Storage) ---
    minio_endpoint: str = Field(default="localhost:9000", alias="MINIO_ENDPOINT")
    minio_access_key: str = Field(default="greenvalue", alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="greenvalue_secret", alias="MINIO_SECRET_KEY")
    minio_secure: bool = Field(default=False, alias="MINIO_SECURE")
    minio_bucket_uploads: str = Field(default="raw-uploads", alias="MINIO_BUCKET_UPLOADS")
    minio_bucket_reports: str = Field(default="pdf-reports", alias="MINIO_BUCKET_REPORTS")
    minio_bucket_heatmaps: str = Field(default="ai-heatmaps", alias="MINIO_BUCKET_HEATMAPS")

    # --- PostgreSQL + PostGIS ---
    database_url: str = Field(
        default="postgresql://greenvalue:greenvalue_secret@localhost:5432/greenvalue",
        alias="DATABASE_URL",
    )

    # --- Qdrant (Vector DB) ---
    qdrant_url: str = Field(default="http://localhost:6333", alias="QDRANT_URL")
    qdrant_collection: str = Field(default="property_embeddings", alias="QDRANT_COLLECTION")

    # --- MLflow ---
    mlflow_tracking_uri: str = Field(default="http://localhost:5000", alias="MLFLOW_TRACKING_URI")

    # --- Prometheus Metrics ---
    metrics_port: int = Field(default=9090, alias="METRICS_PORT")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
        "populate_by_name": True,
    }

    @property
    def yolo_model_name(self) -> str:
        """Returns the full YOLO model name based on size."""
        return f"yolo11{self.yolo_model_size}-seg"

    @property
    def yolo_model_path(self) -> str:
        """Returns the expected path to the YOLO weights file."""
        return f"{self.yolo_weights_dir}/{self.yolo_model_name}.pt"

    @property
    def resolved_device(self) -> str:
        """Resolve device: auto-detect GPU availability."""
        if self.device != "auto":
            return self.device
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"


@lru_cache()
def get_settings() -> Settings:
    """Singleton settings instance (cached)."""
    return Settings()
