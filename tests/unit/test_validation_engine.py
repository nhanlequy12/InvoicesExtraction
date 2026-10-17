from decimal import Decimal
from src.normalization.normalizer import InvoiceNormalizer
from src.pipelines.xml.parser import XMLInvoiceParser
from src.validation.engine import ValidationEngine
from src.validation.rules.arithmetic_rule import ArithmeticValidationRule
from src.validation.rules.base import Severity


def test_validation_engine_on_valid_invoice(sample_xml_bytes):
    parser = XMLInvoiceParser()
    normalizer = InvoiceNormalizer()
    validator = ValidationEngine()

    raw_xml = parser.parse(sample_xml_bytes)
    normalized = normalizer.normalize_from_xml(
        raw_xml=raw_xml,
        document_id="doc-valid",
        file_name="valid.xml"
    )

    report = validator.validate(normalized)
    assert report.is_valid is True
    assert report.error_count == 0
    assert report.taxpayer_verification.exists is True
    assert report.duplicate_check.is_duplicate is False


def test_arithmetic_rule_detects_mismatch(sample_xml_bytes):
    parser = XMLInvoiceParser()
    normalizer = InvoiceNormalizer()
    rule = ArithmeticValidationRule(tolerance=Decimal("1.0"))

    raw_xml = parser.parse(sample_xml_bytes)
    normalized = normalizer.normalize_from_xml(
        raw_xml=raw_xml,
        document_id="doc-tampered",
        file_name="tampered.xml"
    )

    # Intentionally corrupt declared total amount (e.g., 99,000,000 instead of 55,000,000)
    normalized.summary.total_amount = Decimal("99000000")

    issues = rule.evaluate(normalized)
    math_errors = [i for i in issues if i.rule_code == "MATH_TOTAL_AMOUNT_MISMATCH"]
    assert len(math_errors) == 1
    assert math_errors[0].severity == Severity.ERROR
    assert math_errors[0].passed is False


def test_duplicate_detector_records_and_flags(sample_xml_bytes):
    parser = XMLInvoiceParser()
    normalizer = InvoiceNormalizer()
    validator = ValidationEngine()

    raw_xml = parser.parse(sample_xml_bytes)
    normalized = normalizer.normalize_from_xml(
        raw_xml=raw_xml,
        document_id="doc-first",
        file_name="first.xml"
    )

    # First time: passes
    report1 = validator.validate(normalized)
    assert report1.duplicate_check.is_duplicate is False

    # Mark as recorded
    validator.duplicate_detector.record_invoice(normalized)

    # Second time: should detect duplicate
    report2 = validator.validate(normalized)
    assert report2.duplicate_check.is_duplicate is True
    assert report2.error_count > 0
