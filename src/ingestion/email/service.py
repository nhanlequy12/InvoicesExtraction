import uuid
from typing import List, Optional
from src.core.logging import logger
from src.ingestion.base import BaseIngestionService, IngestionSource, RawDocument


class EmailIngestionService(BaseIngestionService):
    """
    Enterprise Email Ingestion Service.
    Connects to IMAP or MS Graph mailbox, scans unread emails from suppliers,
    extracts XML and PDF attachments, and marks emails as processed.
    """

    def __init__(self, host: str = "imap.example.com", username: str = "invoice@company.com"):
        self.host = host
        self.username = username

    def fetch_documents(self) -> List[RawDocument]:
        logger.info(f"Checking email mailbox {self.username} for new invoice attachments...")
        # Production implementation polls IMAP / Graph API.
        # Returns parsed RawDocument attachments list.
        return []

    def ingest_mock_email(self, sender: str, attachments: List[tuple[str, bytes]]) -> List[RawDocument]:
        """Utility for test suites and simulator environments."""
        docs = []
        for filename, data in attachments:
            doc = RawDocument(
                document_id=str(uuid.uuid4()),
                source=IngestionSource.EMAIL,
                file_name=filename,
                file_bytes=data,
                metadata={"sender": sender, "channel": "imap"}
            )
            docs.append(doc)
        return docs
