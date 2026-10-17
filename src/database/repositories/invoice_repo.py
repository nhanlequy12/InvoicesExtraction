import uuid
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session
from src.core.logging import logger
from src.database.models import (
    DocumentModel,
    InvoiceItemModel,
    InvoiceModel,
    InvoiceSignatureModel,
    ValidationResultModel,
)
from src.normalization.schemas import NormalizedInvoice
from src.validation.engine import ValidationReport


class InvoiceRepository:
    """
    Repository for persisting and retrieving invoices and audit trails.
    """

    def __init__(self, db: Session):
        self.db = db

    def save_invoice_transactional(
        self,
        invoice: NormalizedInvoice,
        validation_report: ValidationReport,
        routing_status: str
    ) -> InvoiceModel:
        # 1. Document record
        doc_record = self.db.query(DocumentModel).filter(DocumentModel.id == invoice.document.document_id).first()
        if not doc_record:
            doc_record = DocumentModel(
                id=invoice.document.document_id,
                source=invoice.document.source,
                file_name=invoice.document.file_name,
                file_type=invoice.document.format,
                storage_path=invoice.document.storage_path,
                file_hash=invoice.document.file_hash
            )
            self.db.add(doc_record)
            self.db.flush()

        # 2. Invoice record
        invoice_id = str(uuid.uuid4())
        inv_record = InvoiceModel(
            id=invoice_id,
            document_id=doc_record.id,
            form_number=invoice.metadata.form_number,
            invoice_series=invoice.metadata.invoice_series,
            invoice_number=invoice.metadata.invoice_number,
            issue_date=invoice.metadata.issue_date,
            tax_authority_code=invoice.metadata.tax_authority_code,
            seller_name=invoice.seller.name,
            seller_tax_id=invoice.seller.tax_id or "",
            seller_address=invoice.seller.address,
            buyer_name=invoice.buyer.name,
            buyer_tax_id=invoice.buyer.tax_id,
            buyer_address=invoice.buyer.address,
            currency=invoice.summary.currency,
            exchange_rate=invoice.summary.exchange_rate,
            subtotal=invoice.summary.subtotal,
            vat_amount=invoice.summary.vat_amount,
            total_amount=invoice.summary.total_amount,
            status=routing_status,
            confidence=invoice.confidence.composite_confidence
        )
        self.db.add(inv_record)

        # 3. Line Items
        for item in invoice.items:
            item_record = InvoiceItemModel(
                invoice_id=invoice_id,
                line_number=item.line_number,
                product_code=item.product_code,
                description=item.description,
                unit=item.unit,
                quantity=item.quantity,
                unit_price=item.unit_price,
                discount=item.discount or Decimal("0"),
                amount_before_tax=item.amount_before_tax,
                vat_rate=item.vat_rate,
                vat_amount=item.vat_amount or Decimal("0")
            )
            self.db.add(item_record)

        # 4. Signature
        sig_record = InvoiceSignatureModel(
            invoice_id=invoice_id,
            signature_present=invoice.signature.present,
            integrity_valid=invoice.signature.digest_valid,
            certificate_valid=invoice.signature.certificate_valid,
            certificate_subject=invoice.signature.subject_name,
            certificate_serial=invoice.signature.serial_number,
            status=invoice.signature.status
        )
        self.db.add(sig_record)

        # 5. Validation Results
        for issue in validation_report.issues:
            v_record = ValidationResultModel(
                invoice_id=invoice_id,
                rule_code=issue.rule_code,
                field=issue.field_name,
                severity=issue.severity.value,
                expected_value=issue.expected_value,
                actual_value=issue.actual_value,
                message=issue.message,
                passed=issue.passed
            )
            self.db.add(v_record)

        self.db.commit()
        self.db.refresh(inv_record)
        logger.info(f"Persisted invoice {invoice_id} to database with status {routing_status}")
        return inv_record

    def get_by_id(self, invoice_id: str) -> Optional[InvoiceModel]:
        return self.db.query(InvoiceModel).filter(InvoiceModel.id == invoice_id).first()

    def list_invoices(self, status: Optional[str] = None, limit: int = 50, offset: int = 0) -> List[InvoiceModel]:
        query = self.db.query(InvoiceModel)
        if status:
            query = query.filter(InvoiceModel.status == status)
        return query.order_by(InvoiceModel.created_at.desc()).offset(offset).limit(limit).all()
