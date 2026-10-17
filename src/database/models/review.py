import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from src.core.database import Base


class ReviewRecordModel(Base):
    __tablename__ = "reviews"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_id = Column(String(36), ForeignKey("invoices.id"), nullable=False, index=True)
    reviewer = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False) # APPROVED, REJECTED
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_id = Column(String(36), ForeignKey("invoices.id"), nullable=False, index=True)
    field = Column(String(100), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    reviewer = Column(String(100), nullable=False)
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
