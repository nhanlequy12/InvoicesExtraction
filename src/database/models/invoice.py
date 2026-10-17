import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from src.core.database import Base


class InvoiceModel(Base):
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False, index=True)

    form_number = Column(String(20), nullable=True)
    invoice_series = Column(String(50), nullable=False, index=True)
    invoice_number = Column(String(50), nullable=False, index=True)
    issue_date = Column(String(20), nullable=False, index=True)
    tax_authority_code = Column(String(100), nullable=True)

    seller_name = Column(String(255), nullable=True)
    seller_tax_id = Column(String(50), nullable=False, index=True)
    seller_address = Column(Text, nullable=True)

    buyer_name = Column(String(255), nullable=True)
    buyer_tax_id = Column(String(50), nullable=True, index=True)
    buyer_address = Column(Text, nullable=True)

    currency = Column(String(10), default="VND")
    exchange_rate = Column(Numeric(18, 4), nullable=True)
    subtotal = Column(Numeric(18, 2), nullable=False)
    vat_amount = Column(Numeric(18, 2), nullable=False)
    total_amount = Column(Numeric(18, 2), nullable=False)

    status = Column(String(50), default="PENDING", index=True) # APPROVED, REVIEW, REJECTED
    confidence = Column(Float, default=1.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    items = relationship("InvoiceItemModel", back_populates="invoice", cascade="all, delete-orphan")
    signatures = relationship("InvoiceSignatureModel", back_populates="invoice", cascade="all, delete-orphan")
    validations = relationship("ValidationResultModel", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceItemModel(Base):
    __tablename__ = "invoice_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_id = Column(String(36), ForeignKey("invoices.id"), nullable=False, index=True)
    line_number = Column(Integer, nullable=False)
    product_code = Column(String(100), nullable=True)
    description = Column(Text, nullable=False)
    unit = Column(String(50), nullable=True)
    quantity = Column(Numeric(18, 4), nullable=True)
    unit_price = Column(Numeric(18, 4), nullable=True)
    discount = Column(Numeric(18, 2), default=0)
    amount_before_tax = Column(Numeric(18, 2), nullable=False)
    vat_rate = Column(String(20), nullable=True)
    vat_amount = Column(Numeric(18, 2), default=0)

    invoice = relationship("InvoiceModel", back_populates="items")


class InvoiceSignatureModel(Base):
    __tablename__ = "invoice_signatures"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    invoice_id = Column(String(36), ForeignKey("invoices.id"), nullable=False, index=True)
    signature_present = Column(Boolean, default=False)
    integrity_valid = Column(Boolean, default=False)
    certificate_valid = Column(Boolean, default=False)
    certificate_subject = Column(Text, nullable=True)
    certificate_serial = Column(String(100), nullable=True)
    valid_from = Column(DateTime, nullable=True)
    valid_to = Column(DateTime, nullable=True)
    status = Column(String(50), default="MISSING")

    invoice = relationship("InvoiceModel", back_populates="signatures")
