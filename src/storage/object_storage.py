import hashlib
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Tuple
from src.core.config import settings
from src.core.logging import logger


class StorageService(ABC):
    """Abstract interface for storing raw invoice files."""

    @abstractmethod
    def save(self, file_bytes: bytes, filename: str, subfolder: str = "raw") -> Tuple[str, str]:
        """
        Saves file bytes and returns (storage_path, sha256_hash).
        """
        pass

    @abstractmethod
    def read(self, storage_path: str) -> bytes:
        """Reads file bytes from storage."""
        pass


class LocalStorageService(StorageService):
    """Local disk storage implementation (ideal for development and air-gapped deployments)."""

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or settings.LOCAL_STORAGE_PATH
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save(self, file_bytes: bytes, filename: str, subfolder: str = "raw") -> Tuple[str, str]:
        sha256 = hashlib.sha256(file_bytes).hexdigest()
        ext = Path(filename).suffix.lower()
        unique_name = f"{sha256}{ext}"

        dest_dir = self.base_path / subfolder
        dest_dir.mkdir(parents=True, exist_ok=True)

        full_path = dest_dir / unique_name
        with open(full_path, "wb") as f:
            f.write(file_bytes)

        rel_path = str(full_path.as_posix())
        logger.info(f"Saved file {filename} to {rel_path} with hash {sha256}")
        return rel_path, sha256

    def read(self, storage_path: str) -> bytes:
        with open(storage_path, "rb") as f:
            return f.read()


class MinioStorageService(StorageService):
    """MinIO / S3 object storage implementation for production scale."""

    def __init__(self):
        try:
            from minio import Minio
            self.client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE
            )
            self.bucket = settings.MINIO_BUCKET_NAME
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except Exception as e:
            logger.warning(f"Failed to initialize MinIO client ({e}), falling back to local storage.")
            self.fallback = LocalStorageService()
        else:
            self.fallback = None

    def save(self, file_bytes: bytes, filename: str, subfolder: str = "raw") -> Tuple[str, str]:
        if self.fallback:
            return self.fallback.save(file_bytes, filename, subfolder)

        import io
        sha256 = hashlib.sha256(file_bytes).hexdigest()
        ext = Path(filename).suffix.lower()
        object_name = f"{subfolder}/{sha256}{ext}"

        stream = io.BytesIO(file_bytes)
        self.client.put_object(
            self.bucket,
            object_name,
            stream,
            length=len(file_bytes)
        )
        storage_path = f"s3://{self.bucket}/{object_name}"
        logger.info(f"Saved file {filename} to MinIO {storage_path}")
        return storage_path, sha256

    def read(self, storage_path: str) -> bytes:
        if self.fallback:
            return self.fallback.read(storage_path)

        prefix = f"s3://{self.bucket}/"
        object_name = storage_path.replace(prefix, "")
        response = self.client.get_object(self.bucket, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()


def get_storage_service() -> StorageService:
    if settings.STORAGE_TYPE.lower() == "minio":
        return MinioStorageService()
    return LocalStorageService()
