from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class IngestionSource(str, Enum):
    EMAIL = "email"
    API = "api"


@dataclass
class RawDocument:
    """Represents an ingested document bundle prior to classification."""
    document_id: str
    source: IngestionSource
    file_name: str
    file_bytes: bytes
    content_type: Optional[str] = None
    storage_path: Optional[str] = None
    file_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


class BaseIngestionService(ABC):
    """Abstract base class for all ingestion source adapters."""

    @abstractmethod
    def fetch_documents(self) -> List[RawDocument]:
        """Polls or pulls documents from the designated input channel."""
        pass
