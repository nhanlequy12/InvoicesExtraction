from decimal import Decimal
import pytest
from src.pipelines.ai.layout.detector import LayoutDetector, LayoutRegionType
from src.pipelines.ai.ocr.engine import OCRResult, OCRToken
from src.pipelines.ai.table.extractor import TableExtractor
from src.pipelines.ai.extraction.field_extractor import AIFieldExtractor


@pytest.fixture
def sample_invoice_ocr_result() -> OCRResult:
    tokens = [
        OCRToken(text="TAX INVOICE", box=[550, 20, 750, 45], confidence=0.98, page_number=1),
        OCRToken(text="Date: 20-Mar-2008", box=[550, 60, 720, 80], confidence=0.97, page_number=1),
        OCRToken(text="Due Date : 16-Oct-2016", box=[550, 85, 760, 105], confidence=0.96, page_number=1),
        OCRToken(text="PO Number :35", box=[550, 110, 680, 130], confidence=0.99, page_number=1),
        OCRToken(text="Address:16424 Timothy Mission", box=[50, 170, 350, 190], confidence=0.95, page_number=1),
        OCRToken(text="Markville, AK 58294 US", box=[50, 195, 270, 215], confidence=0.95, page_number=1),
        OCRToken(text="Email:melvin40@example.net", box=[50, 230, 320, 250], confidence=0.95, page_number=1),
        OCRToken(text="www.ThompsonandSons.org", box=[50, 255, 300, 275], confidence=0.95, page_number=1),
        OCRToken(text="(GSTIN: 12345670 00070007", box=[50, 280, 310, 300], confidence=0.95, page_number=1),
        OCRToken(text="Bill to:Denise Perez", box=[550, 170, 730, 190], confidence=0.97, page_number=1),
        OCRToken(text="16424 Timothy Mission", box=[550, 195, 760, 215], confidence=0.96, page_number=1),
        OCRToken(text="Markville, AK 58294 US", box=[550, 220, 770, 240], confidence=0.96, page_number=1),
        OCRToken(text="Tel:+ (352)259-8443", box=[550, 245, 740, 265], confidence=0.95, page_number=1),
        OCRToken(text="Email:melvin40@example.net", box=[550, 270, 820, 290], confidence=0.95, page_number=1),
        OCRToken(text="Site:http://smith.org/", box=[550, 295, 740, 315], confidence=0.95, page_number=1),
        OCRToken(text="GSTIN: OG@AAMFCO376K124", box=[350, 340, 650, 360], confidence=0.95, page_number=1),
        # Table Header
        OCRToken(text="ITEMS", box=[50, 610, 150, 630], confidence=0.99, page_number=1),
        OCRToken(text="QUANTITY", box=[400, 610, 520, 630], confidence=0.99, page_number=1),
        OCRToken(text="PRICE", box=[700, 610, 780, 630], confidence=0.99, page_number=1),
        # Table Rows
        OCRToken(text="Data score fire.", box=[50, 635, 200, 655], confidence=0.95, page_number=1),
        OCRToken(text="6.00", box=[440, 635, 480, 655], confidence=0.99, page_number=1),
        OCRToken(text="$57.80", box=[720, 635, 780, 655], confidence=0.98, page_number=1),
        OCRToken(text="Determine half.", box=[50, 660, 200, 680], confidence=0.95, page_number=1),
        OCRToken(text="2.00", box=[440, 660, 480, 680], confidence=0.99, page_number=1),
        OCRToken(text="$24.70", box=[720, 660, 780, 680], confidence=0.98, page_number=1),
        OCRToken(text="Model read.", box=[50, 685, 180, 705], confidence=0.95, page_number=1),
        OCRToken(text="1.00", box=[440, 685, 480, 705], confidence=0.99, page_number=1),
        OCRToken(text="$86.14", box=[720, 685, 780, 705], confidence=0.98, page_number=1),
        OCRToken(text="Mother consider.", box=[50, 710, 210, 730], confidence=0.95, page_number=1),
        OCRToken(text="1.00", box=[440, 710, 480, 730], confidence=0.99, page_number=1),
        OCRToken(text="$81.84", box=[720, 710, 780, 730], confidence=0.98, page_number=1),
        OCRToken(text="Tv focus.", box=[50, 735, 150, 755], confidence=0.95, page_number=1),
        OCRToken(text="4.00", box=[440, 735, 480, 755], confidence=0.99, page_number=1),
        OCRToken(text="$40.28", box=[720, 735, 780, 755], confidence=0.98, page_number=1),
        # Payment info
        OCRToken(text="Total in words: seven hundred and thirty-four point three three", box=[50, 780, 450, 800], confidence=0.95, page_number=1),
        OCRToken(text="Bank Name State Bank of California", box=[50, 810, 380, 830], confidence=0.96, page_number=1),
        OCRToken(text="Branch Name Raf CAMP", box=[50, 835, 250, 855], confidence=0.95, page_number=1),
        OCRToken(text="Bank Account Number 11695435", box=[50, 860, 300, 880], confidence=0.97, page_number=1),
        OCRToken(text="Bank Swift Code SBININBB250", box=[50, 885, 280, 905], confidence=0.97, page_number=1),
        # Totals
        OCRToken(text="SUB_TOTAL : 725.30 EUR", box=[600, 780, 850, 800], confidence=0.98, page_number=1),
        OCRToken(text="DISCOUNT(1.85%): (-) 13.42", box=[600, 805, 830, 825], confidence=0.95, page_number=1),
        OCRToken(text="TAX:VAT (3.88%): 28.18 EUR", box=[600, 830, 860, 850], confidence=0.97, page_number=1),
        OCRToken(text="TOTAL : 734.33 EUR", box=[600, 870, 820, 890], confidence=0.99, page_number=1),
        # Footer
        OCRToken(text="Note: This order is shipped through blue dart courier", box=[50, 930, 450, 950], confidence=0.95, page_number=1),
    ]
    full_text = "\n".join(t.text for t in tokens)
    return OCRResult(full_text=full_text, tokens=tokens, page_number=1, mean_confidence=0.97)


def test_layout_detector_sample_invoice_regions(sample_invoice_ocr_result):
    detector = LayoutDetector()
    regions = detector.detect_regions(sample_invoice_ocr_result)
    region_types = {r.region_type for r in regions}

    assert LayoutRegionType.HEADER in region_types
    assert LayoutRegionType.SELLER in region_types
    assert LayoutRegionType.BUYER in region_types
    assert LayoutRegionType.TABLE in region_types
    assert LayoutRegionType.PAYMENT_INFO in region_types
    assert LayoutRegionType.TOTALS in region_types
    assert LayoutRegionType.FOOTER in region_types


def test_table_extractor_sample_invoice_rows(sample_invoice_ocr_result):
    detector = LayoutDetector()
    regions = detector.detect_regions(sample_invoice_ocr_result)
    table_region = next(r for r in regions if r.region_type == LayoutRegionType.TABLE)

    extractor = TableExtractor()
    rows = extractor.extract_table(table_region, sample_invoice_ocr_result)

    assert len(rows) == 5
    assert rows[0].description == "Data score fire."
    assert rows[0].quantity == Decimal("6.00")
    assert rows[0].unit_price == Decimal("57.80")

    assert rows[1].description == "Determine half."
    assert rows[1].quantity == Decimal("2.00")
    assert rows[1].unit_price == Decimal("24.70")

    assert rows[4].description == "Tv focus."
    assert rows[4].quantity == Decimal("4.00")
    assert rows[4].unit_price == Decimal("40.28")


def test_field_extractor_returns_full_text_and_table(sample_invoice_ocr_result):
    detector = LayoutDetector()
    regions = detector.detect_regions(sample_invoice_ocr_result)

    extractor = AIFieldExtractor()
    result = extractor.extract(sample_invoice_ocr_result, regions)

    assert result.full_text == sample_invoice_ocr_result.full_text
    assert len(result.line_items) == 5

    # 1. Invoice Number vs PO Number (P0 Review correction: PO Number 35 is NOT Invoice Number)
    assert result.fields["invoice_number"].value is None
    assert result.fields["po_number"].value == "35"

    # 2. Dates
    assert result.fields["issue_date"].value == "20-Mar-2008"
    assert result.fields["due_date"].value == "16-Oct-2016"

    # 3. Clean separated addresses
    assert "Denise Perez" not in (result.fields["seller_address"].value or "")
    assert "16424 Timothy Mission" in result.fields["seller_address"].value
    assert "16424 Timothy Mission" in result.fields["buyer_address"].value

    # 4. Buyer & Seller extra contact fields
    assert "Denise Perez" in result.fields["buyer_name"].value
    assert result.fields["seller_website"].value == "www.ThompsonandSons.org"
    assert result.fields["seller_email"].value == "melvin40@example.net"
    assert "352" in result.fields["buyer_phone"].value
    assert result.fields["buyer_website"].value == "http://smith.org/"

    # 5. Financials
    assert result.fields["subtotal"].value == Decimal("725.30")
    assert result.fields["discount"].value == Decimal("13.42")
    assert result.fields["discount_rate"].value == "1.85%"
    assert result.fields["vat_amount"].value == Decimal("28.18")
    assert result.fields["vat_rate"].value == "3.88%"
    assert result.fields["total_amount"].value == Decimal("734.33")
    assert result.fields["currency"].value == "EUR"
    assert result.fields["total_in_words"].value == "seven hundred and thirty-four point three three"

    # 6. Payment info
    assert result.fields["bank_name"].value == "State Bank of California"
    assert result.fields["bank_branch"].value == "Raf CAMP"
    assert result.fields["bank_account"].value == "11695435"
    assert result.fields["bank_swift"].value == "SBININBB250"
    assert "blue dart courier" in result.fields["notes"].value

    # 7. Multiple Tax IDs / GSTIN tracking
    assert len(result.tax_ids_found) >= 2
    assert any("12345670 00070007" in rec["tax_id"] for rec in result.tax_ids_found)
    assert any("OG@AAMFCO376K124" in rec["tax_id"] for rec in result.tax_ids_found)

    # 8. Tier 3 Anomaly Warnings
    assert any("TOTAL_CALCULATION_MISMATCH" in w for w in result.warnings)
    assert any("CURRENCY_INCONSISTENCY" in w for w in result.warnings)
    assert any("TABLE_INTERPRETATION" in w for w in result.warnings)
