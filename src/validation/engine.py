from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional
from src.core.config import settings
from src.core.logging import logger
from src.normalization.schemas import NormalizedInvoice
from src.validation.anomaly.anomaly_detector import AnomalyFinding, FinancialAnomalyDetector
from src.validation.anomaly.duplicate_detector import DuplicateCheckResult, DuplicateInvoiceDetector
from src.validation.external.taxpayer_verifier import ExternalTaxpayerVerifier, TaxpayerVerificationResult
from src.validation.rules.arithmetic_rule import ArithmeticValidationRule
from src.validation.rules.base import Severity, ValidationIssue, ValidationRule
from src.validation.rules.cross_field_rule import CrossFieldValidationRule
from src.validation.rules.format_rule import FormatValidationRule
from src.validation.rules.schema_rule import SchemaCompletenessRule


@dataclass
class ValidationReport:
    is_valid: bool
    status: str # PASS, PASS_WITH_WARNINGS, FAILED
    error_count: int
    warning_count: int
    issues: List[ValidationIssue]
    taxpayer_verification: TaxpayerVerificationResult
    duplicate_check: DuplicateCheckResult
    anomalies: List[AnomalyFinding]


class ValidationEngine:
    """
    Validation Engine Orchestrator.
    Executes the 3 core validation pillars in parallel:
    1. Deterministic Business Rules (Schema, Format, Arithmetic, Cross-Field)
    2. External Tax Authority Verification (Seller Taxpayer status)
    3. Anomaly & Duplicate Detection (Hash, Business Key, Price Outliers)
    """

    def __init__(self, arithmetic_tolerance: float = settings.ARITHMETIC_TOLERANCE_VND):
        self.rules: List[ValidationRule] = [
            SchemaCompletenessRule(),
            FormatValidationRule(),
            ArithmeticValidationRule(tolerance=Decimal(str(arithmetic_tolerance))),
            CrossFieldValidationRule(),
        ]
        self.taxpayer_verifier = ExternalTaxpayerVerifier()
        self.duplicate_detector = DuplicateInvoiceDetector()
        self.anomaly_detector = FinancialAnomalyDetector()

    def validate(self, invoice: NormalizedInvoice) -> ValidationReport:
        logger.info(
            f"Starting validation engine for invoice {invoice.metadata.invoice_series}-{invoice.metadata.invoice_number}"
        )

        all_issues: List[ValidationIssue] = []

        # 1. Deterministic Rules Evaluation
        for rule in self.rules:
            issues = rule.evaluate(invoice)
            all_issues.extend(issues)

        # 2. External Taxpayer Verification
        taxpayer_res = self.taxpayer_verifier.verify(
            invoice.seller.tax_id,
            invoice.seller.name
        )
        if not taxpayer_res.exists:
            all_issues.append(
                ValidationIssue(
                    rule_code="EXT_SELLER_TAX_ID_NOT_FOUND",
                    field_name="seller.tax_id",
                    severity=Severity.ERROR,
                    message=f"Seller Tax ID '{invoice.seller.tax_id}' was not found in official tax registry",
                    passed=False
                )
            )

        # 3. Duplicate Detection
        dup_res = self.duplicate_detector.check_duplicate(invoice)
        if dup_res.is_duplicate:
            all_issues.append(
                ValidationIssue(
                    rule_code="DUP_DUPLICATE_INVOICE",
                    field_name="metadata.invoice_number",
                    severity=Severity.ERROR,
                    message=dup_res.message or "Invoice is a duplicate",
                    passed=False
                )
            )

        # 4. Anomaly Detection
        anomalies = self.anomaly_detector.detect(invoice)
        for anom in anomalies:
            if anom.severity == "HIGH":
                all_issues.append(
                    ValidationIssue(
                        rule_code=f"ANOM_{anom.anomaly_type}",
                        field_name=anom.field,
                        severity=Severity.WARNING,
                        message=anom.description,
                        passed=False
                    )
                )

        error_count = sum(1 for i in all_issues if i.severity == Severity.ERROR and not i.passed)
        warning_count = sum(1 for i in all_issues if i.severity == Severity.WARNING and not i.passed)

        if error_count > 0:
            status = "FAILED"
            is_valid = False
        elif warning_count > 0:
            status = "PASS_WITH_WARNINGS"
            is_valid = True
        else:
            status = "PASS"
            is_valid = True

        logger.info(
            f"Validation completed for {invoice.metadata.invoice_number}: "
            f"status={status}, errors={error_count}, warnings={warning_count}"
        )

        return ValidationReport(
            is_valid=is_valid,
            status=status,
            error_count=error_count,
            warning_count=warning_count,
            issues=all_issues,
            taxpayer_verification=taxpayer_res,
            duplicate_check=dup_res,
            anomalies=anomalies
        )
