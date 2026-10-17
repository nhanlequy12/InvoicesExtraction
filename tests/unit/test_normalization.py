from decimal import Decimal
from src.normalization.normalizer import InvoiceNormalizer
from src.pipelines.xml.parser import XMLInvoiceParser


def test_normalization_from_xml(sample_xml_bytes):
    parser = XMLInvoiceParser()
    normalizer = InvoiceNormalizer()

    raw_xml = parser.parse(sample_xml_bytes)
    normalized = normalizer.normalize_from_xml(
        raw_xml=raw_xml,
        document_id="doc-test-123",
        file_name="invoice.xml",
        source="email",
        file_hash="test-sha256-hash",
        storage_path="/storage/raw/test.xml"
    )

    assert normalized.document.document_id == "doc-test-123"
    assert normalized.document.source == "email"
    assert normalized.metadata.invoice_number == "00001234"
    assert normalized.metadata.invoice_series == "1C24TKK"
    assert normalized.metadata.issue_date == "2026-09-28"
    assert normalized.seller.tax_id == "0100109106"
    assert normalized.buyer.tax_id == "0312345678"

    # Strict Decimal checks
    assert isinstance(normalized.summary.total_amount, Decimal)
    assert normalized.summary.total_amount == Decimal("55000000")
    assert normalized.summary.subtotal == Decimal("50000000")
    assert normalized.summary.vat_amount == Decimal("5000000")

    assert len(normalized.items) == 1
    assert normalized.items[0].description == "May tinh xach tay Dell Latitude"
