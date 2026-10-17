from typing import List
from src.normalization.schemas import NormalizedInvoice
from src.validation.rules.base import Severity, ValidationIssue, ValidationRule


class SchemaCompletenessRule(ValidationRule):
    """
    Validates presence of mandatory business fields defined by Decree 123.
    """

    def evaluate(self, invoice: NormalizedInvoice) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        # 1. Invoice Number
        if not invoice.metadata.invoice_number or invoice.metadata.invoice_number.strip() == "":
            issues.append(
                ValidationIssue(
                    rule_code="SCHEMA_MISSING_INVOICE_NUMBER",
                    field_name="metadata.invoice_number",
                    severity=Severity.ERROR,
                    message="Invoice number (Số hóa đơn) is missing",
                    passed=False,
                    expected_value="Non-empty string",
                    actual_value=None
                )
            )

        # 2. Invoice Series
        if not invoice.metadata.invoice_series or invoice.metadata.invoice_series.strip() == "":
            issues.append(
                ValidationIssue(
                    rule_code="SCHEMA_MISSING_SERIES",
                    field_name="metadata.invoice_series",
                    severity=Severity.ERROR,
                    message="Invoice series (Ký hiệu hóa đơn) is missing",
                    passed=False,
                    expected_value="Non-empty string",
                    actual_value=None
                )
            )

        # 3. Seller Tax ID
        if not invoice.seller.tax_id or invoice.seller.tax_id.strip() == "":
            issues.append(
                ValidationIssue(
                    rule_code="SCHEMA_MISSING_SELLER_TAX_ID",
                    field_name="seller.tax_id",
                    severity=Severity.ERROR,
                    message="Seller Tax ID (Mã số thuế người bán) is missing",
                    passed=False,
                    expected_value="10 or 13 digit tax code",
                    actual_value=None
                )
            )

        # 4. Seller Name
        if not invoice.seller.name or invoice.seller.name.strip() == "":
            issues.append(
                ValidationIssue(
                    rule_code="SCHEMA_MISSING_SELLER_NAME",
                    field_name="seller.name",
                    severity=Severity.ERROR,
                    message="Seller Name (Tên người bán) is missing",
                    passed=False,
                    expected_value="Seller Name",
                    actual_value=None
                )
            )

        # 5. Items presence
        if not invoice.items or len(invoice.items) == 0:
            issues.append(
                ValidationIssue(
                    rule_code="SCHEMA_EMPTY_LINE_ITEMS",
                    field_name="items",
                    severity=Severity.ERROR,
                    message="Invoice must contain at least one line item",
                    passed=False,
                    expected_value=">= 1 item",
                    actual_value="0 items"
                )
            )

        return issues
