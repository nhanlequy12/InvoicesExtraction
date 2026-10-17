from decimal import Decimal
from src.confidence.engine import ConfidenceEngine
from src.confidence.schemas import RoutingDecision
from src.normalization.normalizer import InvoiceNormalizer
from src.pipelines.xml.parser import XMLInvoiceParser
from src.validation.engine import ValidationEngine


def test_confidence_engine_routes_valid_invoice(sample_xml_bytes):
    parser = XMLInvoiceParser()
    normalizer = InvoiceNormalizer()
    validator = ValidationEngine()
    confidence_engine = ConfidenceEngine(approval_threshold=0.90)

    raw_xml = parser.parse(sample_xml_bytes)
    # Ensure signature is considered valid for test
    raw_xml.signature.status = "VALID"
    raw_xml.signature.signature_present = True

    normalized = normalizer.normalize_from_xml(
        raw_xml=raw_xml,
        document_id="doc-approvable",
        file_name="approvable.xml"
    )

    val_report = validator.validate(normalized)
    decision = confidence_engine.evaluate(normalized, val_report)

    assert decision.decision == RoutingDecision.APPROVED
    assert decision.is_auto_approvable is True
    assert decision.composite_score >= 0.90


def test_confidence_engine_routes_errored_invoice_to_review(sample_xml_bytes):
    parser = XMLInvoiceParser()
    normalizer = InvoiceNormalizer()
    validator = ValidationEngine()
    confidence_engine = ConfidenceEngine()

    raw_xml = parser.parse(sample_xml_bytes)
    normalized = normalizer.normalize_from_xml(
        raw_xml=raw_xml,
        document_id="doc-faulty",
        file_name="faulty.xml"
    )

    # Invalidate arithmetic
    normalized.summary.total_amount = Decimal("123456789")

    val_report = validator.validate(normalized)
    decision = confidence_engine.evaluate(normalized, val_report)

    assert decision.decision == RoutingDecision.REVIEW
    assert decision.is_auto_approvable is False
