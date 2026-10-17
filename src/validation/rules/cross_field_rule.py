from datetime import datetime
from typing import List
from src.normalization.schemas import NormalizedInvoice
from src.validation.rules.base import Severity, ValidationIssue, ValidationRule


class CrossFieldValidationRule(ValidationRule):
    """
    Validates logical inter-dependencies between distinct fields.
    """

    def evaluate(self, invoice: NormalizedInvoice) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        # 1. Issue date cannot be far in the future
        try:
            issue_date = datetime.strptime(invoice.metadata.issue_date, "%Y-%m-%d").date()
            today = datetime.utcnow().date()
            if issue_date > today:
                issues.append(
                    ValidationIssue(
                        rule_code="XFIELD_FUTURE_ISSUE_DATE",
                        field_name="metadata.issue_date",
                        severity=Severity.ERROR,
                        message=f"Invoice issue date ({invoice.metadata.issue_date}) is in the future",
                        passed=False,
                        expected_value=f"<= {today}",
                        actual_value=invoice.metadata.issue_date
                    )
                )
        except Exception:
            pass

        # 2. Seller Tax ID must not match Buyer Tax ID
        if invoice.seller.tax_id and invoice.buyer.tax_id:
            if invoice.seller.tax_id.strip() == invoice.buyer.tax_id.strip():
                issues.append(
                    ValidationIssue(
                        rule_code="XFIELD_SELLER_BUYER_TAX_ID_IDENTICAL",
                        field_name="seller.tax_id",
                        severity=Severity.WARNING,
                        message="Seller Tax ID and Buyer Tax ID are identical (Self-billing or test invoice)",
                        passed=False,
                        expected_value="Distinct tax IDs",
                        actual_value=invoice.seller.tax_id
                    )
                )

        return issues
