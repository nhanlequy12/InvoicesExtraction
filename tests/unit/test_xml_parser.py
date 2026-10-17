from decimal import Decimal
from src.pipelines.xml.parser import XMLInvoiceParser


def test_xml_parser_metadata_and_parties(sample_xml_bytes):
    parser = XMLInvoiceParser()
    parsed = parser.parse(sample_xml_bytes)

    # Metadata
    assert parsed.metadata.form_number == "1"
    assert parsed.metadata.invoice_series == "1C24TKK"
    assert parsed.metadata.invoice_number == "00001234"
    assert parsed.metadata.issue_date == "2026-09-28"
    assert parsed.metadata.currency == "VND"

    # Seller
    assert parsed.seller.tax_id == "0100109106"
    assert "CONG NGHE ABC" in (parsed.seller.name or "")
    assert parsed.seller.bank_account == "19020000000001"

    # Buyer
    assert parsed.buyer.tax_id == "0312345678"
    assert "PHAN MEM KHOA HOC" in (parsed.buyer.name or "")


def test_xml_parser_line_items_and_totals(sample_xml_bytes):
    parser = XMLInvoiceParser()
    parsed = parser.parse(sample_xml_bytes)

    # Line items
    assert len(parsed.items) == 1
    item = parsed.items[0]
    assert item.line_number == 1
    assert "Dell Latitude" in item.description
    assert item.quantity == Decimal("2")
    assert item.unit_price == Decimal("25000000")
    assert item.amount_before_tax == Decimal("50000000")
    assert item.vat_rate == "10%"

    # Summary
    assert parsed.summary.subtotal == Decimal("50000000")
    assert parsed.summary.vat_amount == Decimal("5000000")
    assert parsed.summary.total_amount == Decimal("55000000")


def test_xml_signature_detection(sample_xml_bytes):
    parser = XMLInvoiceParser()
    parsed = parser.parse(sample_xml_bytes)

    assert parsed.signature.signature_present is True
