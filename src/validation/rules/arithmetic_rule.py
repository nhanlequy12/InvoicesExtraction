from decimal import Decimal
from typing import List
from src.normalization.schemas import NormalizedInvoice
from src.validation.rules.base import Severity, ValidationIssue, ValidationRule


class ArithmeticValidationRule(ValidationRule):
    """
    Validates arithmetic and financial consistency.
    Enforces Decimal arithmetic to avoid floating-point inaccuracies,
    with configurable rounding tolerance (default: 1.0 VND).
    """

    def __init__(self, tolerance: Decimal = Decimal("1.0")):
        self.tolerance = tolerance

    def evaluate(self, invoice: NormalizedInvoice) -> List[ValidationIssue]:
        issues: List[ValidationIssue] = []

        calculated_subtotal = Decimal("0")
        calculated_vat_total = Decimal("0")

        # 1. Line item arithmetic
        for item in invoice.items:
            if item.quantity is not None and item.unit_price is not None:
                expected_line_amount = (item.quantity * item.unit_price) - (item.discount or Decimal("0"))
                diff = abs(expected_line_amount - item.amount_before_tax)
                if diff > self.tolerance:
                    issues.append(
                        ValidationIssue(
                            rule_code="MATH_LINE_ITEM_MISMATCH",
                            field_name=f"items[{item.line_number}].amount_before_tax",
                            severity=Severity.ERROR,
                            message=(
                                f"Line {item.line_number}: Quantity ({item.quantity}) * Unit Price ({item.unit_price}) - Discount ({item.discount}) = {expected_line_amount}, "
                                f"but declared amount is {item.amount_before_tax}"
                            ),
                            passed=False,
                            expected_value=str(expected_line_amount),
                            actual_value=str(item.amount_before_tax)
                        )
                    )

            calculated_subtotal += item.amount_before_tax
            calculated_vat_total += (item.vat_amount or Decimal("0"))

        # 2. Subtotal cross-check
        subtotal_diff = abs(calculated_subtotal - invoice.summary.subtotal)
        if subtotal_diff > self.tolerance:
            issues.append(
                ValidationIssue(
                    rule_code="MATH_SUBTOTAL_MISMATCH",
                    field_name="summary.subtotal",
                    severity=Severity.ERROR,
                    message=f"Sum of item subtotals ({calculated_subtotal}) does not equal invoice subtotal ({invoice.summary.subtotal})",
                    passed=False,
                    expected_value=str(calculated_subtotal),
                    actual_value=str(invoice.summary.subtotal)
                )
            )

        # 3. Total amount cross-check (Subtotal + VAT == Total)
        expected_total = invoice.summary.subtotal + invoice.summary.vat_amount
        total_diff = abs(expected_total - invoice.summary.total_amount)
        if total_diff > self.tolerance:
            issues.append(
                ValidationIssue(
                    rule_code="MATH_TOTAL_AMOUNT_MISMATCH",
                    field_name="summary.total_amount",
                    severity=Severity.ERROR,
                    message=f"Subtotal ({invoice.summary.subtotal}) + VAT ({invoice.summary.vat_amount}) = {expected_total}, but total is {invoice.summary.total_amount}",
                    passed=False,
                    expected_value=str(expected_total),
                    actual_value=str(invoice.summary.total_amount)
                )
            )

        return issues
