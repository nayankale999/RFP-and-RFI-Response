import io
import logging
from pathlib import Path

from minio import Minio
from minio.error import S3Error

from app.config import get_settings
from app.shared.exceptions import StorageError

logger = logging.getLogger(__name__)


class StorageClient:
    """MinIO S3-compatible storage client."""

    def __init__(self):
        settings = get_settings()
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self.bucket = settings.minio_bucket
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info(f"Created bucket: {self.bucket}")
        except S3Error as e:
            logger.error(f"Failed to ensure bucket: {e}")
            raise StorageError(f"Bucket initialization failed: {e}")

    def upload_file(self, object_name: str, file_data: bytes, content_type: str = "application/octet-stream") -> str:
        """Upload a file to MinIO. Returns the object path."""
        try:
            data = io.BytesIO(file_data)
            self.client.put_object(
                self.bucket,
                object_name,
                data,
                length=len(file_data),
                content_type=content_type,
            )
            logger.info(f"Uploaded: {object_name} ({len(file_data)} bytes)")
            return object_name
        except S3Error as e:
            logger.error(f"Upload failed: {e}")
            raise StorageError(f"File upload failed: {e}")

    def download_file(self, object_name: str) -> bytes:
        """Download a file from MinIO."""
        try:
            response = self.client.get_object(self.bucket, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            logger.error(f"Download failed: {e}")
            raise StorageError(f"File download failed: {e}")

    def delete_file(self, object_name: str):
        """Delete a file from MinIO."""
        try:
            self.client.remove_object(self.bucket, object_name)
            logger.info(f"Deleted: {object_name}")
        except S3Error as e:
            logger.error(f"Delete failed: {e}")
            raise StorageError(f"File deletion failed: {e}")

    def get_presigned_url(self, object_name: str, expires_hours: int = 1) -> str:
        """Generate a presigned URL for temporary access."""
        from datetime import timedelta

        try:
            url = self.client.presigned_get_object(
                self.bucket, object_name, expires=timedelta(hours=expires_hours)
            )
            return url
        except S3Error as e:
            logger.error(f"Presigned URL generation failed: {e}")
            raise StorageError(f"URL generation failed: {e}")

    def file_exists(self, object_name: str) -> bool:
        """Check if a file exists in storage."""
        try:
            self.client.stat_object(self.bucket, object_name)
            return True
        except S3Error:
            return False


_storage_client: StorageClient | None = None


def get_storage_client() -> StorageClient:
    global _storage_client
    if _storage_client is None:
        _storage_client = StorageClient()
    return _storage_client
