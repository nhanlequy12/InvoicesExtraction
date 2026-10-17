from typing import Generator
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.orchestrator.pipeline_runner import InvoicePipelineOrchestrator
from src.storage.object_storage import StorageService, get_storage_service


def get_orchestrator() -> InvoicePipelineOrchestrator:
    return InvoicePipelineOrchestrator()


def get_storage() -> StorageService:
    return get_storage_service()
