import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, String, Text
from src.core.database import Base


class DocumentModel(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source = Column(String(50), nullable=False) # email, portal, erp, api
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False) # xml, pdf, image
    storage_path = Column(Text, nullable=True)
    file_hash = Column(String(64), nullable=True, index=True) # SHA-256
    created_at = Column(DateTime, default=datetime.utcnow)
