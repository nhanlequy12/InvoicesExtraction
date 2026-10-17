import re
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from src.core.logging import logger
from src.normalization.schemas import (
    DocumentInfo,
    InvoiceConfidenceInfo,
    InvoiceLineItem,
    InvoiceMetadata,
    InvoiceParty,
    InvoiceSignatureInfo,
    InvoiceSummary,
    NormalizedInvoice,
)
from src.pipelines.ai.extraction.field_extractor import RawAIExtractionResult
from src.pipelines.xml.models import RawParsedXMLResult


class InvoiceNormalizer:
    """
    Invoice Normalization Engine.
    Converts raw heterogeneous extraction results (XML or AI Pipeline) into
    the standardized Canonical Normalized Invoice representation.
    Normalizes dates, formats Tax IDs, and ensures strict Decimal numeric casting.
    """

    def _normalize_date(self, raw_date: Optional[str]) -> str:
        if not raw_date:
            return datetime.utcnow().strftime("%Y-%m-%d")

        cleaned = raw_date.strip()
        # Common Vietnamese formats: DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD
        patterns = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d"]
        for p in patterns:
            try:
                dt = datetime.strptime(cleaned, p)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                pass

        # If it's already an ISO timestamp:
        try:
            return cleaned.split("T")[0]
        except Exception:
            return cleaned

    def _normalize_tax_id(self, tax_id: Optional[str]) -> Optional[str]:
        if not tax_id:
            return None
        # Remove whitespace and invalid characters
        cleaned = re.sub(r"[^\d\-]", "", tax_id.strip())
        return cleaned

    def normalize_from_xml(
        self,
        raw_xml: RawParsedXMLResult,
        document_id: str,
        file_name: str,
        source: str = "email",
        file_hash: Optional[str] = None,
        storage_path: Optional[str] = None
    ) -> NormalizedInvoice:
        """Transforms parsed XML result into NormalizedInvoice."""
        doc_info = DocumentInfo(
            document_id=document_id,
            source=source,
            format="xml",
            document_type="vietnamese_einvoice",
            file_name=file_name,
            file_hash=file_hash,
            storage_path=storage_path
        )

        meta = InvoiceMetadata(
            form_number=raw_xml.metadata.form_number,
            invoice_series=raw_xml.metadata.invoice_series or "",
            invoice_number=raw_xml.metadata.invoice_number or "",
            issue_date=self._normalize_date(raw_xml.metadata.issue_date),
            tax_authority_code=raw_xml.metadata.tax_authority_code
        )

        seller = InvoiceParty(
            name=raw_xml.seller.name or "UNKNOWN SELLER",
            tax_id=self._normalize_tax_id(raw_xml.seller.tax_id),
            address=raw_xml.seller.address,
            phone=raw_xml.seller.phone,
            bank_account=raw_xml.seller.bank_account,
            bank_name=raw_xml.seller.bank_name
        )

        buyer = InvoiceParty(
            name=raw_xml.buyer.name or "UNKNOWN BUYER",
            tax_id=self._normalize_tax_id(raw_xml.buyer.tax_id),
            address=raw_xml.buyer.address,
            phone=raw_xml.buyer.phone,
            bank_account=raw_xml.buyer.bank_account,
            bank_name=raw_xml.buyer.bank_name
        )

        items = []
        for it in raw_xml.items:
            items.append(
                InvoiceLineItem(
                    line_number=it.line_number,
                    product_code=it.product_code,
                    description=it.description,
                    unit=it.unit,
                    quantity=it.quantity,
                    unit_price=it.unit_price,
                    discount=it.discount_amount or Decimal("0"),
                    amount_before_tax=it.amount_before_tax,
                    vat_rate=it.vat_rate,
                    vat_amount=it.vat_amount or Decimal("0")
                )
            )

        summary = InvoiceSummary(
            subtotal=raw_xml.summary.subtotal,
            vat_amount=raw_xml.summary.vat_amount,
            total_amount=raw_xml.summary.total_amount,
            currency=raw_xml.metadata.currency or "VND",
            exchange_rate=raw_xml.metadata.exchange_rate,
            amount_in_words=raw_xml.summary.amount_in_words
        )

        signature = InvoiceSignatureInfo(
            present=raw_xml.signature.signature_present,
            digest_valid=raw_xml.signature.digest_valid,
            certificate_valid=raw_xml.signature.certificate_valid,
            status=raw_xml.signature.status,
            subject_name=raw_xml.signature.subject_name,
            serial_number=raw_xml.signature.serial_number,
            message=raw_xml.signature.message
        )

        confidence = InvoiceConfidenceInfo(
            composite_confidence=1.0 if raw_xml.schema_valid else 0.95,
            field_confidences={
                "metadata.invoice_number": 1.0,
                "metadata.invoice_series": 1.0,
                "seller.tax_id": 1.0,
                "summary.total_amount": 1.0,
                "items": 1.0
            }
        )

        logger.info(f"Normalized XML invoice: {meta.invoice_series}-{meta.invoice_number}")
        return NormalizedInvoice(
            document=doc_info,
            metadata=meta,
            seller=seller,
            buyer=buyer,
            items=items,
            summary=summary,
            signature=signature,
            confidence=confidence
        )

    def normalize_from_ai(
        self,
        raw_ai: RawAIExtractionResult,
        document_id: str,
        file_name: str,
        source: str = "api",
        doc_format: str = "pdf",
        file_hash: Optional[str] = None,
        storage_path: Optional[str] = None
    ) -> NormalizedInvoice:
        """Transforms AI extraction result into NormalizedInvoice."""
        fields = raw_ai.fields

        doc_info = DocumentInfo(
            document_id=document_id,
            source=source,
            format=doc_format,
            document_type="vietnamese_einvoice",
            file_name=file_name,
            file_hash=file_hash,
            storage_path=storage_path
        )

        def _str_or_none(key: str) -> Optional[str]:
            """Safely convert a field value to str, returning None if missing or None."""
            f = fields.get(key)
            if f is None or f.value is None:
                return None
            return str(f.value)

        meta = InvoiceMetadata(
            form_number=_str_or_none("form_number"),
            invoice_series=_str_or_none("invoice_series") or "",
            invoice_number=_str_or_none("invoice_number") or "",
            issue_date=self._normalize_date(_str_or_none("issue_date") or ""),
            tax_authority_code=_str_or_none("tax_authority_code")
        )

        seller = InvoiceParty(
            name=_str_or_none("seller_name") or "UNKNOWN SELLER",
            tax_id=self._normalize_tax_id(_str_or_none("seller_tax_id")),
            address=_str_or_none("seller_address"),
            phone=_str_or_none("seller_phone")
        )

        buyer = InvoiceParty(
            name=_str_or_none("buyer_name") or "UNKNOWN BUYER",
            tax_id=self._normalize_tax_id(_str_or_none("buyer_tax_id")),
            address=_str_or_none("buyer_address")
        )

        items = []
        for it in raw_ai.line_items:
            items.append(
                InvoiceLineItem(
                    line_number=it.line_number,
                    product_code=it.product_code,
                    description=it.description,
                    unit=it.unit,
                    quantity=it.quantity,
                    unit_price=it.unit_price,
                    discount=it.discount or Decimal("0"),
                    amount_before_tax=it.amount_before_tax,
                    vat_rate=it.vat_rate,
                    vat_amount=it.vat_amount or Decimal("0")
                )
            )

        summary = InvoiceSummary(
            subtotal=fields["subtotal"].value if fields.get("subtotal") and fields["subtotal"].value is not None else Decimal("0"),
            vat_amount=fields["vat_amount"].value if fields.get("vat_amount") and fields["vat_amount"].value is not None else Decimal("0"),
            total_amount=fields["total_amount"].value if fields.get("total_amount") and fields["total_amount"].value is not None else Decimal("0"),
            currency=_str_or_none("currency") or "VND"
        )

        signature = InvoiceSignatureInfo(
            present=False,
            status="MISSING",
            message="No cryptographic signature in raw image/PDF document"
        )

        field_confidences = {k: v.confidence for k, v in fields.items()}
        confidence = InvoiceConfidenceInfo(
            composite_confidence=raw_ai.composite_confidence,
            field_confidences=field_confidences
        )

        logger.info(f"Normalized AI invoice: {meta.invoice_series}-{meta.invoice_number}")
        return NormalizedInvoice(
            document=doc_info,
            metadata=meta,
            seller=seller,
            buyer=buyer,
            items=items,
            summary=summary,
            signature=signature,
            confidence=confidence
        )
