import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional
from src.core.logging import logger
from src.pipelines.ai.layout.detector import LayoutRegion, LayoutRegionType
from src.pipelines.ai.ocr.engine import OCRResult
from src.pipelines.ai.table.extractor import ExtractedTableRow, TableExtractor


@dataclass
class ExtractedField:
    value: Any
    confidence: float
    bbox: Optional[List[int]] = None
    source: str = "ai_model"


@dataclass
class RawAIExtractionResult:
    fields: Dict[str, ExtractedField]
    line_items: List[ExtractedTableRow]
    composite_confidence: float


class AIFieldExtractor:
    """
    Field Extraction Module.
    Uses regex anchor matching on OCR full_text to populate standard invoice
    fields for both Vietnamese e-invoices and international formats (English,
    GSTIN, EUR/USD/GBP currency symbols, etc.).

    When a field cannot be extracted from the text, its value is set to None
    so the invoice is flagged for REVIEW instead of storing dummy data.
    """

    def __init__(self):
        self.table_extractor = TableExtractor()

    # ------------------------------------------------------------------ helpers

    def _search(self, text: str, pattern: str, flags: int = re.IGNORECASE) -> Optional[str]:
        """Return the first capture group of a regex match, stripped."""
        m = re.search(pattern, text, flags)
        return m.group(1).strip() if m else None

    def _search_all(self, text: str, pattern: str, flags: int = re.IGNORECASE) -> List[str]:
        return [m.strip() for m in re.findall(pattern, text, flags)]

    def _parse_decimal(self, raw: Optional[str]) -> Optional[Decimal]:
        """
        Parse a decimal string that may use European (1.234,56) or US/VN (1,234.56)
        thousand/decimal separators, and optional leading currency symbols.
        """
        if not raw:
            return None
        s = raw.strip().replace(" ", "")
        # Detect format when both separators present
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):
                # European: 1.234,56
                s = s.replace(".", "").replace(",", ".")
            else:
                # US: 1,234.56
                s = s.replace(",", "")
        elif "," in s:
            after_comma = s.split(",")[-1]
            if len(after_comma) == 3 and after_comma.isdigit():
                s = s.replace(",", "")   # thousands separator
            else:
                s = s.replace(",", ".")  # decimal comma
        elif "." in s:
            after_dot = s.split(".")[-1]
            if len(after_dot) == 3 and after_dot.isdigit():
                s = s.replace(".", "")   # VN-style thousands (e.g. 1.000.000)
        # Strip leading currency symbols / non-numeric characters
        s = re.sub(r"^[^\d\-]+", "", s)
        try:
            return Decimal(s)
        except InvalidOperation:
            return None

    # ------------------------------------------------------------------ field extractors

    def _extract_invoice_number(self, text: str) -> ExtractedField:
        patterns = [
            r"(?:S[oố]\s*(?:H[Đđ]|hóa\s*đơn)|Invoice\s*No\.?|INV\s*No\.?|Bill\s*No\.?)\s*[:\-]?\s*([A-Z0-9\-/]{3,20})",
            r"(?:PO\s*Number|PO\s*#)\s*[:\-]?\s*(\d+)",
            r"(?:Số|No\.?)\s*[:\-]?\s*(\d{5,})",
        ]
        for pat in patterns:
            val = self._search(text, pat)
            if val:
                return ExtractedField(value=val, confidence=0.88)
        return ExtractedField(value=None, confidence=0.40)

    def _extract_invoice_series(self, text: str) -> ExtractedField:
        patterns = [
            r"(?:Ký\s*hiệu|KHHDon|Series|Ký\s*hiệu\s*HĐ)\s*[:\-]?\s*([12][A-Z0-9]{4,9})",
        ]
        for pat in patterns:
            val = self._search(text, pat)
            if val:
                return ExtractedField(value=val, confidence=0.88)
        return ExtractedField(value=None, confidence=0.40)

    def _extract_form_number(self, text: str) -> ExtractedField:
        val = self._search(text, r"(?:Mẫu\s*số|KHMSHDon|Form\s*No\.?)\s*[:\-]?\s*([0-9]{1,2}[A-Z]?)")
        if val:
            return ExtractedField(value=val, confidence=0.82)
        return ExtractedField(value=None, confidence=0.40)

    def _extract_issue_date(self, text: str) -> ExtractedField:
        patterns = [
            # DD-Mon-YYYY  e.g. 20-Mar-2008
            r"(?:Date|Ngày\s*lập|Ngày)[:\s]*(\d{1,2}[-/\s][A-Za-z]{3}[-/\s]\d{4})",
            # DD/MM/YYYY or DD-MM-YYYY
            r"(?:Date|Ngày\s*lập|Ngày)[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
            # YYYY-MM-DD ISO
            r"(?:Date|Ngày\s*lập|Ngày)[:\s]*(\d{4}-\d{2}-\d{2})",
            # Bare date anywhere in text (last resort)
            r"\b(\d{1,2}[-/][A-Za-z]{3}[-/]\d{4})\b",
            r"\b(\d{1,2}[-/]\d{1,2}[-/]\d{4})\b",
        ]
        for pat in patterns:
            val = self._search(text, pat)
            if val:
                return ExtractedField(value=val, confidence=0.85)
        return ExtractedField(value=None, confidence=0.40)

    def _extract_tax_authority_code(self, text: str) -> ExtractedField:
        val = self._search(text, r"(?:MCCQT|Mã\s*CQT)\s*[:\-]?\s*([A-Z0-9\-]{5,20})")
        if val:
            return ExtractedField(value=val, confidence=0.90)
        return ExtractedField(value=None, confidence=0.30)

    def _extract_seller_name(self, text: str) -> ExtractedField:
        patterns = [
            # Vietnamese: "Tên người bán:" or "Đơn vị bán hàng:"
            r"(?:Tên\s*(?:người|đơn\s*vị)\s*bán|Đơn\s*vị\s*bán\s*hàng)\s*[:\-]?\s*(.+?)(?:\n|MST|Mã\s*số|\Z)",
            # www.CompanyName.org pattern
            r"www\.([A-Za-z]+(?:and[A-Za-z]+)?)\.(com|org|net|vn)",
            # "From:" seller block
            r"(?:From|Seller|Vendor|Supplier)\s*[:\-]?\s*\n?\s*(.+?)(?:\n|$)",
        ]
        for pat in patterns:
            val = self._search(text, pat)
            if val:
                # Convert CamelCase domain names to words (e.g. ThompsonandSons → Thompson and Sons)
                val = re.sub(r"([a-z])([A-Z])", r"\1 \2", val).strip()
                val = re.sub(r"(?i)\band\b", " and ", val)
                return ExtractedField(value=val.upper(), confidence=0.75)
        return ExtractedField(value=None, confidence=0.30)

    def _extract_seller_tax_id(self, text: str) -> ExtractedField:
        patterns = [
            # Vietnamese MST 10 or 13 digits
            r"(?:Mã\s*số\s*thuế|MST|Tax\s*[Cc]ode)\s*[:\-]?\s*([0-9]{10}(?:-[0-9]{3})?)",
            # GSTIN: first occurrence is usually the seller
            r"GSTIN\s*[:\-]?\s*([A-Z0-9@]{10,20})",
        ]
        for pat in patterns:
            val = self._search(text, pat)
            if val:
                return ExtractedField(value=val, confidence=0.88)
        return ExtractedField(value=None, confidence=0.40)

    def _extract_seller_address(self, text: str) -> ExtractedField:
        patterns = [
            r"(?:Địa\s*chỉ\s*(?:người|đơn\s*vị)\s*bán|Địa\s*chỉ)\s*[:\-]?\s*(.+?)(?:\n\n|\nMST|\nĐiện|\Z)",
            r"Address\s*[:\-]?\s*(.+?)(?:\n\n|Email|\Z)",
        ]
        for pat in patterns:
            val = self._search(text, pat, re.IGNORECASE | re.DOTALL)
            if val:
                return ExtractedField(value=" ".join(val.split()), confidence=0.70)
        return ExtractedField(value=None, confidence=0.30)

    def _extract_buyer_name(self, text: str) -> ExtractedField:
        patterns = [
            # Vietnamese
            r"(?:Tên\s*(?:người|đơn\s*vị)\s*mua|Khách\s*hàng)\s*[:\-]?\s*(.+?)(?:\n|MST|Mã\s*số|\Z)",
            # English "Bill to:" block — first name line
            r"(?:Bill\s*to|Billed\s*to|Customer|Client)\s*[:\-]?\s*\n?\s*(.+?)(?:\n|$)",
        ]
        for pat in patterns:
            val = self._search(text, pat)
            if val:
                return ExtractedField(value=val.strip().upper(), confidence=0.78)
        return ExtractedField(value=None, confidence=0.30)

    def _extract_buyer_tax_id(self, text: str) -> ExtractedField:
        val = self._search(
            text,
            r"(?:Mã\s*số\s*thuế\s*(?:người|đơn\s*vị)\s*mua)\s*[:\-]?\s*([0-9]{10}(?:-[0-9]{3})?)"
        )
        if val:
            return ExtractedField(value=val, confidence=0.82)

        # Find all GSTIN values — buyer is typically the second one
        all_gstins = self._search_all(text, r"GSTIN\s*[:\-]?\s*([A-Z0-9@]{10,20})")
        if len(all_gstins) >= 2:
            return ExtractedField(value=all_gstins[1], confidence=0.75)
        return ExtractedField(value=None, confidence=0.30)

    def _extract_buyer_address(self, text: str) -> ExtractedField:
        patterns = [
            r"(?:Địa\s*chỉ\s*(?:người|đơn\s*vị)\s*mua)\s*[:\-]?\s*(.+?)(?:\n\n|\nMST|\nĐiện|\Z)",
            r"(?:Bill\s*to|Billed\s*to)[^\n]*\n(.+?)(?:Tel|Email|Site|$)",
        ]
        for pat in patterns:
            val = self._search(text, pat, re.IGNORECASE | re.DOTALL)
            if val:
                return ExtractedField(value=" ".join(val.split()), confidence=0.68)
        return ExtractedField(value=None, confidence=0.30)

    def _extract_currency(self, text: str) -> ExtractedField:
        patterns = [
            r"(?:Đơn\s*vị\s*tiền\s*tệ|Currency|DVTTe)\s*[:\-]?\s*(VND|USD|EUR|GBP|JPY|CNY|SGD|AUD|CAD)",
            r"\b(EUR|USD|GBP|JPY|CNY|SGD|AUD|CAD|VND)\b",
        ]
        for pat in patterns:
            val = self._search(text, pat)
            if val:
                return ExtractedField(value=val.upper(), confidence=0.92)
        return ExtractedField(value=None, confidence=0.40)

    def _extract_subtotal(self, text: str) -> ExtractedField:
        val = self._search(
            text,
            r"(?:SUB[_\s]?TOTAL|Tổng\s*tiền\s*chưa\s*thuế|TgTCThue|Subtotal)\s*[:\-]?\s*([0-9.,\s]+)"
        )
        amount = self._parse_decimal(val)
        if amount is not None:
            return ExtractedField(value=amount, confidence=0.87)
        return ExtractedField(value=None, confidence=0.35)

    def _extract_vat_amount(self, text: str) -> ExtractedField:
        patterns = [
            r"(?:TAX\s*[:\-]?\s*VAT|VAT|Thuế\s*GTGT|TgTThue)\s*[^:\n]*[:\-]?\s*([0-9.,\s]+)",
            r"(?:TAX|VAT)\s*\([^)]*\)\s*[:\-]?\s*([0-9.,\s]+)",
        ]
        for pat in patterns:
            val = self._search(text, pat)
            amount = self._parse_decimal(val)
            if amount is not None:
                return ExtractedField(value=amount, confidence=0.85)
        return ExtractedField(value=None, confidence=0.35)

    def _extract_total_amount(self, text: str) -> ExtractedField:
        patterns = [
            r"(?:^|\b)TOTAL\s*[:\-]?\s*([0-9.,]+)",
            r"(?:Tổng\s*(?:cộng|tiền\s*thanh\s*toán)|TgTTTBSo|Total\s*Amount)\s*[:\-]?\s*([0-9.,\s]+)",
        ]
        for pat in patterns:
            matches = re.findall(pat, text, re.IGNORECASE | re.MULTILINE)
            if matches:
                # Use the last match to avoid capturing SUB_TOTAL
                amount = self._parse_decimal(matches[-1])
                if amount is not None:
                    return ExtractedField(value=amount, confidence=0.90)
        return ExtractedField(value=None, confidence=0.35)

    # ------------------------------------------------------------------ main entry

    def extract(self, ocr_result: OCRResult, regions: List[LayoutRegion]) -> RawAIExtractionResult:
        full_text = ocr_result.full_text
        fields: Dict[str, ExtractedField] = {}

        fields["invoice_number"]     = self._extract_invoice_number(full_text)
        fields["invoice_series"]     = self._extract_invoice_series(full_text)
        fields["form_number"]        = self._extract_form_number(full_text)
        fields["issue_date"]         = self._extract_issue_date(full_text)
        fields["tax_authority_code"] = self._extract_tax_authority_code(full_text)
        fields["seller_name"]        = self._extract_seller_name(full_text)
        fields["seller_tax_id"]      = self._extract_seller_tax_id(full_text)
        fields["seller_address"]     = self._extract_seller_address(full_text)
        fields["buyer_name"]         = self._extract_buyer_name(full_text)
        fields["buyer_tax_id"]       = self._extract_buyer_tax_id(full_text)
        fields["buyer_address"]      = self._extract_buyer_address(full_text)
        fields["currency"]           = self._extract_currency(full_text)
        fields["subtotal"]           = self._extract_subtotal(full_text)
        fields["vat_amount"]         = self._extract_vat_amount(full_text)
        fields["total_amount"]       = self._extract_total_amount(full_text)

        # Log fields that could not be extracted for traceability
        missing = [k for k, v in fields.items() if v.value is None]
        if missing:
            logger.warning(f"Could not extract fields (will require REVIEW): {missing}")

        # Extract table line items
        table_region = next((r for r in regions if r.region_type == LayoutRegionType.TABLE), None)
        line_items = self.table_extractor.extract_table(table_region)

        # Composite confidence — missing fields reduce the overall score
        total_conf = sum(f.confidence for f in fields.values()) + sum(i.confidence for i in line_items)
        count = len(fields) + len(line_items)
        composite_conf = total_conf / count if count > 0 else 0.50

        logger.info(
            f"AI Extraction: {len(fields)} fields extracted "
            f"(missing={len(missing)}), composite_confidence={composite_conf:.2f}"
        )

        return RawAIExtractionResult(
            fields=fields,
            line_items=line_items,
            composite_confidence=composite_conf,
        )
