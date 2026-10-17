import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from src.core.database import Base


class ValidationResultModel(Base):
    __tablename__ = "validation_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_id = Column(String(36), ForeignKey("invoices.id"), nullable=False, index=True)
    rule_code = Column(String(100), nullable=False)
    field = Column(String(100), nullable=True)
    severity = Column(String(20), nullable=False) # ERROR, WARNING, INFO
    expected_value = Column(Text, nullable=True)
    actual_value = Column(Text, nullable=True)
    message = Column(Text, nullable=False)
    passed = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    invoice = relationship("InvoiceModel", back_populates="validations")


class AnomalyRecordModel(Base):
    __tablename__ = "anomalies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_id = Column(String(36), ForeignKey("invoices.id"), nullable=False, index=True)
    anomaly_type = Column(String(100), nullable=False)
    severity = Column(String(20), nullable=False)
    field = Column(String(100), nullable=True)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
