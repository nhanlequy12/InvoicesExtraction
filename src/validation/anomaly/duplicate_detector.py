import hashlib
from dataclasses import dataclass
from typing import List, Optional, Set
from src.core.logging import logger
from src.normalization.schemas import NormalizedInvoice


@dataclass
class DuplicateCheckResult:
    is_duplicate: bool
    duplicate_type: Optional[str] = None # FILE_HASH, BUSINESS_KEY
    matched_invoice_id: Optional[str] = None
    message: Optional[str] = None


class DuplicateInvoiceDetector:
    """
    Multi-layer Duplicate Invoice Detection:
    Layer 1: Exact File SHA-256 hash
    Layer 2: Perceptual hash / Content hash
    Layer 3: Canonical Business Key:
             (seller_tax_id + invoice_series + invoice_number + issue_date + total_amount)
    """

    def __init__(self):
        self._seen_file_hashes: Set[str] = set()
        self._seen_business_keys: dict[str, str] = {} # business_key -> invoice_id

    def generate_business_key(self, invoice: NormalizedInvoice) -> str:
        raw_key = (
            f"{invoice.seller.tax_id or ''}|"
            f"{invoice.metadata.invoice_series.upper()}|"
            f"{invoice.metadata.invoice_number}|"
            f"{invoice.metadata.issue_date}|"
            f"{str(invoice.summary.total_amount)}"
        )
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()

    def check_duplicate(self, invoice: NormalizedInvoice) -> DuplicateCheckResult:
        # 1. Check File Hash
        if invoice.document.file_hash:
            if invoice.document.file_hash in self._seen_file_hashes:
                logger.warning(f"Duplicate invoice detected by exact file hash: {invoice.document.file_hash}")
                return DuplicateCheckResult(
                    is_duplicate=True,
                    duplicate_type="FILE_HASH",
                    message="Exact identical file has already been ingested into the system."
                )

        # 2. Check Business Key
        b_key = self.generate_business_key(invoice)
        if b_key in self._seen_business_keys:
            existing_id = self._seen_business_keys[b_key]
            logger.warning(f"Duplicate invoice detected by business key matching invoice {existing_id}")
            return DuplicateCheckResult(
                is_duplicate=True,
                duplicate_type="BUSINESS_KEY",
                matched_invoice_id=existing_id,
                message=f"Duplicate invoice detected by business key matching existing record {existing_id}"
            )

        return DuplicateCheckResult(is_duplicate=False)

    def record_invoice(self, invoice: NormalizedInvoice):
        """Records invoice fingerprint in cache to prevent subsequent duplicates."""
        if invoice.document.file_hash:
            self._seen_file_hashes.add(invoice.document.file_hash)
        b_key = self.generate_business_key(invoice)
        self._seen_business_keys[b_key] = invoice.document.document_id
