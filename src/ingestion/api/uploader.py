import uuid
from typing import Optional
from src.core.logging import logger
from src.ingestion.base import IngestionSource, RawDocument


class APIUploaderService:
    """Handles direct REST API multipart file uploads."""

    @staticmethod
    def process_uploaded_file(
        filename: str,
        content: bytes,
        content_type: Optional[str] = None
    ) -> RawDocument:
        logger.info(f"API received uploaded file: {filename} ({len(content)} bytes)")
        return RawDocument(
            document_id=str(uuid.uuid4()),
            source=IngestionSource.API,
            file_name=filename,
            file_bytes=content,
            content_type=content_type,
            metadata={"upload_channel": "rest_api_v1"}
        )
