# ============================================================
# GreenValue AI Engine - MinIO Storage Service
# S3-compatible object storage for images, heatmaps, and PDFs
# ============================================================

import io
import logging
from typing import Optional
from datetime import timedelta

from minio import Minio
from minio.error import S3Error

from config.settings import get_settings

logger = logging.getLogger(__name__)


class StorageService:
    """MinIO S3-compatible storage client for GreenValue AI."""

    def __init__(self):
        self.settings = get_settings()
        self.client: Optional[Minio] = None

    def connect(self) -> None:
        """Initialize MinIO client connection."""
        self.client = Minio(
            endpoint=self.settings.minio_endpoint,
            access_key=self.settings.minio_access_key,
            secret_key=self.settings.minio_secret_key,
            secure=self.settings.minio_secure,
        )
        logger.info(f"MinIO connected: {self.settings.minio_endpoint}")
        self._ensure_buckets()

    def _ensure_buckets(self) -> None:
        """Create required buckets if they don't exist."""
        buckets = [
            self.settings.minio_bucket_uploads,
            self.settings.minio_bucket_reports,
            self.settings.minio_bucket_heatmaps,
        ]
        for bucket in buckets:
            try:
                if not self.client.bucket_exists(bucket):
                    self.client.make_bucket(bucket)
                    logger.info(f"Created bucket: {bucket}")
            except S3Error as e:
                logger.warning(f"Bucket check failed for {bucket}: {e}")

    def download_image(self, file_key: str, bucket: Optional[str] = None) -> bytes:
        """
        Download an image from MinIO.

        Args:
            file_key: Object key in the bucket
            bucket: Bucket name (defaults to raw-uploads)

        Returns:
            Image file bytes
        """
        bucket = bucket or self.settings.minio_bucket_uploads
        try:
            response = self.client.get_object(bucket, file_key)
            data = response.read()
            response.close()
            response.release_conn()
            logger.info(f"Downloaded: {bucket}/{file_key} ({len(data)} bytes)")
            return data
        except S3Error as e:
            logger.error(f"Failed to download {bucket}/{file_key}: {e}")
            raise

    def upload_heatmap(self, file_key: str, data: bytes) -> str:
        """
        Upload a generated heatmap image to MinIO.

        Returns:
            The object key of the uploaded file
        """
        bucket = self.settings.minio_bucket_heatmaps
        return self._upload(bucket, file_key, data, "image/png")

    def upload_report(self, file_key: str, data: bytes) -> str:
        """
        Upload a generated PDF report to MinIO.

        Returns:
            The object key of the uploaded file
        """
        bucket = self.settings.minio_bucket_reports
        return self._upload(bucket, file_key, data, "application/pdf")

    def _upload(self, bucket: str, file_key: str, data: bytes, content_type: str) -> str:
        """Generic upload method."""
        try:
            self.client.put_object(
                bucket_name=bucket,
                object_name=file_key,
                data=io.BytesIO(data),
                length=len(data),
                content_type=content_type,
            )
            logger.info(f"Uploaded: {bucket}/{file_key} ({len(data)} bytes)")
            return file_key
        except S3Error as e:
            logger.error(f"Failed to upload {bucket}/{file_key}: {e}")
            raise

    def get_presigned_url(
        self,
        file_key: str,
        bucket: Optional[str] = None,
        expires: int = 3600,
    ) -> str:
        """
        Generate a pre-signed download URL.

        Args:
            file_key: Object key
            bucket: Bucket name
            expires: URL expiration in seconds (default: 1 hour)

        Returns:
            Pre-signed URL string
        """
        bucket = bucket or self.settings.minio_bucket_uploads
        try:
            url = self.client.presigned_get_object(
                bucket, file_key, expires=timedelta(seconds=expires)
            )
            return url
        except S3Error as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise

    @property
    def is_connected(self) -> bool:
        """Check if MinIO client is initialized."""
        return self.client is not None


# Singleton
_storage: Optional[StorageService] = None


def get_storage_service() -> StorageService:
    """Get or create singleton storage service."""
    global _storage
    if _storage is None:
        _storage = StorageService()
    return _storage
