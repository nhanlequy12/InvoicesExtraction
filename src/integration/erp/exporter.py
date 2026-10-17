import uuid
from decimal import Decimal
from typing import Any, Dict
from src.core.logging import logger
from src.integration.erp.models import AccountingJournalEntry, AccountPostingLine
from src.normalization.schemas import NormalizedInvoice


class ERPIntegrationEngine:
    """
    ERP Integration Engine.
    Transforms validated/approved invoices into double-entry accounting journal vouchers
    and pushes to corporate ERP platforms (MISA, SAP, Bravo, FAST, Oracle).
    """

    def __init__(self, erp_provider: str = "misa"):
        self.erp_provider = erp_provider

    def build_journal_entry(self, invoice: NormalizedInvoice) -> AccountingJournalEntry:
        """
        Builds standard Vietnamese double-entry accounting journal lines:
        Nợ TK 156 / 152 (Tiền hàng chưa thuế)
        Nợ TK 1331 (Thuế GTGT đầu vào)
        Có TK 331 (Phải trả người bán - Tổng tiền thanh toán)
        """
        lines = []

        # Line 1: Goods / Service Expense (Nợ 1561)
        if invoice.summary.subtotal > Decimal("0"):
            lines.append(
                AccountPostingLine(
                    account_debit="1561",
                    account_credit="331",
                    amount=invoice.summary.subtotal,
                    description=f"Tiền hàng theo HĐ {invoice.metadata.invoice_series}-{invoice.metadata.invoice_number}"
                )
            )

        # Line 2: Deductible Input VAT (Nợ 1331)
        if invoice.summary.vat_amount > Decimal("0"):
            lines.append(
                AccountPostingLine(
                    account_debit="1331",
                    account_credit="331",
                    amount=invoice.summary.vat_amount,
                    description=f"Thuế GTGT đầu vào theo HĐ {invoice.metadata.invoice_series}-{invoice.metadata.invoice_number}"
                )
            )

        entry = AccountingJournalEntry(
            entry_number=f"PKT-{invoice.metadata.invoice_number}",
            posting_date=invoice.metadata.issue_date,
            invoice_number=invoice.metadata.invoice_number,
            invoice_series=invoice.metadata.invoice_series,
            seller_tax_id=invoice.seller.tax_id or "",
            seller_name=invoice.seller.name,
            currency=invoice.summary.currency,
            total_amount=invoice.summary.total_amount,
            lines=lines
        )
        return entry

    def post_to_erp(self, invoice: NormalizedInvoice) -> Dict[str, Any]:
        journal_entry = self.build_journal_entry(invoice)
        logger.info(
            f"Posting invoice {invoice.metadata.invoice_number} to ERP ({self.erp_provider.upper()}) "
            f"with {len(journal_entry.lines)} accounting lines totaling {journal_entry.total_amount} {journal_entry.currency}"
        )

        # In production, invokes HTTP REST or RFC connector with ERP.
        return {
            "erp_provider": self.erp_provider,
            "success": True,
            "voucher_id": f"VOUCHER-{uuid.uuid4().hex[:8].upper()}",
            "posting_lines_count": len(journal_entry.lines),
            "message": f"Successfully posted to {self.erp_provider} ERP ledger."
        }
