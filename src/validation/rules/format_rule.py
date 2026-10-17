import re
from typing import List
from src.normalization.schemas import NormalizedInvoice
from src.validation.rules.base import Severity, ValidationIssue, ValidationRule


class FormatValidationRule(ValidationRule):
    """
    Validates field formatting against Vietnamese tax standards and regulations.
    """

    def evaluate(self, invoice: NormalizedInvoice) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        # 1. Seller Tax ID pattern (10 digits or 13 digits with hyphen)
        tax_id_pattern = r"^[0-9]{10}(-[0-9]{3})?$"
        if invoice.seller.tax_id:
            if not re.match(tax_id_pattern, invoice.seller.tax_id):
                issues.append(
                    ValidationIssue(
                        rule_code="FMT_INVALID_SELLER_TAX_ID",
                        field_name="seller.tax_id",
                        severity=Severity.ERROR,
                        message=f"Seller Tax ID '{invoice.seller.tax_id}' does not match standard 10 or 13-digit pattern",
                        passed=False,
                        expected_value="XXXXXXXXXX or XXXXXXXXXX-XXX",
                        actual_value=invoice.seller.tax_id
                    )
                )

        # 2. Buyer Tax ID pattern (if present)
        if invoice.buyer.tax_id and invoice.buyer.tax_id.strip() != "":
            if not re.match(tax_id_pattern, invoice.buyer.tax_id):
                issues.append(
                    ValidationIssue(
                        rule_code="FMT_INVALID_BUYER_TAX_ID",
                        field_name="buyer.tax_id",
                        severity=Severity.WARNING,
                        message=f"Buyer Tax ID '{invoice.buyer.tax_id}' format warning",
                        passed=False,
                        expected_value="XXXXXXXXXX or XXXXXXXXXX-XXX",
                        actual_value=invoice.buyer.tax_id
                    )
                )

        # 3. Invoice Number pattern (up to 8 digits)
        inv_no = invoice.metadata.invoice_number
        if inv_no:
            if not re.match(r"^[0-9]{1,8}$", inv_no):
                issues.append(
                    ValidationIssue(
                        rule_code="FMT_INVALID_INVOICE_NUMBER",
                        field_name="metadata.invoice_number",
                        severity=Severity.ERROR,
                        message=f"Invoice number '{inv_no}' must be 1 to 8 digits",
                        passed=False,
                        expected_value="Digits only (<= 8 chars)",
                        actual_value=inv_no
                    )
                )

        # 4. Invoice Series pattern (Circular 78 format: 1C24TKK)
        series = invoice.metadata.invoice_series
        if series:
            if not re.match(r"^[12C][0-9]{2}[A-Z]{2,4}$", series):
                issues.append(
                    ValidationIssue(
                        rule_code="FMT_SERIES_NON_STANDARD",
                        field_name="metadata.invoice_series",
                        severity=Severity.WARNING,
                        message=f"Invoice series '{series}' may not conform to standard TT78 pattern",
                        passed=False,
                        expected_value="Pattern like 1C24TKK",
                        actual_value=series
                    )
                )

        return issues
