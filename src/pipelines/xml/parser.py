from decimal import Decimal
from typing import List, Optional
from lxml import etree
from src.core.logging import logger
from src.pipelines.xml.models import (
    ParsedXMLMetadata,
    ParsedXMLParty,
    ParsedXMLLineItem,
    ParsedXMLSummary,
    RawParsedXMLResult,
)
from src.pipelines.xml.schema_validator import XMLSchemaValidator
from src.pipelines.xml.signature_verifier import XMLSignatureVerifier


class XMLInvoiceParser:
    """
    Production XML Parser for Vietnamese Electronic Invoices (TT78/ND123).
    Extracts invoice metadata, seller, buyer, line items, totals, and signatures
    using robust XPath and XML namespace agnostic queries.
    """

    def __init__(self):
        self.schema_validator = XMLSchemaValidator()
        self.signature_verifier = XMLSignatureVerifier()

    def _get_text(self, element: Optional[etree._Element], xpath: str) -> Optional[str]:
        if element is None:
            return None
        nodes = element.xpath(xpath)
        if nodes and len(nodes) > 0:
            if isinstance(nodes[0], etree._Element) and nodes[0].text:
                return nodes[0].text.strip()
            elif isinstance(nodes[0], str):
                return nodes[0].strip()
        return None

    def _get_decimal(self, element: Optional[etree._Element], xpath: str, default: str = "0") -> Decimal:
        val = self._get_text(element, xpath)
        if val is None or val == "":
            return Decimal(default)
        # Clean currency characters and spaces
        cleaned = val.replace(",", "").replace(" ", "").strip()
        try:
            return Decimal(cleaned)
        except Exception:
            return Decimal(default)

    def parse(self, xml_bytes: bytes) -> RawParsedXMLResult:
        schema_valid, schema_errors = self.schema_validator.validate(xml_bytes)
        root = etree.fromstring(xml_bytes)

        # 1. Invoice Metadata (TTChung / THDon)
        tt_chung = root.find(".//TTChung")
        if tt_chung is None:
            tt_chung = root.find(".//THDon")

        metadata = ParsedXMLMetadata(
            form_number=self._get_text(tt_chung, ".//KHMSHDon | .//MauSo"),
            invoice_series=self._get_text(tt_chung, ".//KHHDon | .//KyHieu"),
            invoice_number=self._get_text(tt_chung, ".//SHDon | .//SoHDon"),
            issue_date=self._get_text(tt_chung, ".//NLap | .//NgayLap"),
            tax_authority_code=self._get_text(tt_chung, ".//MCCQT | .//MaCuaCQT"),
            currency=self._get_text(tt_chung, ".//DVTTe | .//LoaiTien") or "VND",
            exchange_rate=self._get_decimal(tt_chung, ".//TGia | .//TyGia", "1")
            if self._get_text(tt_chung, ".//TGia | .//TyGia") else None,
            payment_method=self._get_text(tt_chung, ".//HTTToan | .//HinhThucTT"),
        )

        # 2. Seller Information (NBan)
        n_ban = root.find(".//NBan")
        if n_ban is None:
            n_ban = root.find(".//Seller")

        seller = ParsedXMLParty(
            name=self._get_text(n_ban, ".//Ten | .//TenNBan"),
            tax_id=self._get_text(n_ban, ".//MST | .//MSTNBan"),
            address=self._get_text(n_ban, ".//DChi | .//DChiNBan"),
            phone=self._get_text(n_ban, ".//SDThoai | .//DienThoai"),
            bank_account=self._get_text(n_ban, ".//STKNHang | .//SoTK"),
            bank_name=self._get_text(n_ban, ".//TNHang | .//NganHang"),
        )

        # 3. Buyer Information (NMua)
        n_mua = root.find(".//NMua")
        if n_mua is None:
            n_mua = root.find(".//Buyer")

        buyer = ParsedXMLParty(
            name=self._get_text(n_mua, ".//Ten | .//TenNMua"),
            tax_id=self._get_text(n_mua, ".//MST | .//MSTNMua"),
            address=self._get_text(n_mua, ".//DChi | .//DChiNMua"),
            phone=self._get_text(n_mua, ".//SDThoai"),
            bank_account=self._get_text(n_mua, ".//STKNHang"),
            bank_name=self._get_text(n_mua, ".//TNHang"),
        )

        # 4. Line Items (DSHHDVu / HHDVu)
        item_nodes = root.xpath(".//DSHHDVu/HHDVu | .//ChiTietHHDVu | .//Item")
        items: List[ParsedXMLLineItem] = []
        for idx, item_elem in enumerate(item_nodes, start=1):
            stt_str = self._get_text(item_elem, ".//STT")
            line_no = int(stt_str) if stt_str and stt_str.isdigit() else idx
            desc = self._get_text(item_elem, ".//THHDVu | .//TenHHDVu | .//Name") or ""
            unit = self._get_text(item_elem, ".//DVTinh | .//DonViTinh")
            qty = self._get_decimal(item_elem, ".//SLuong | .//SoLuong", "0")
            price = self._get_decimal(item_elem, ".//DGia | .//DonGia", "0")
            discount = self._get_decimal(item_elem, ".//STCKhau | .//ChietKhau", "0")
            amount = self._get_decimal(item_elem, ".//ThTien | .//ThanhTien", "0")
            vat_rate = self._get_text(item_elem, ".//TSuat | .//ThueSuat")

            items.append(
                ParsedXMLLineItem(
                    line_number=line_no,
                    product_code=self._get_text(item_elem, ".//MHHDVu | .//MaHHDVu"),
                    description=desc,
                    unit=unit,
                    quantity=qty,
                    unit_price=price,
                    discount_amount=discount,
                    amount_before_tax=amount,
                    vat_rate=vat_rate,
                )
            )

        # 5. Totals & Payment (TToan)
        t_toan = root.find(".//TToan")
        if t_toan is None:
            t_toan = root.find(".//TongTien")
        subtotal = self._get_decimal(t_toan, ".//TgTCThue | .//TongTienChuaThue", "0")
        vat_amount = self._get_decimal(t_toan, ".//TgTThue | .//TongTienThue", "0")
        total_amount = self._get_decimal(t_toan, ".//TgTTTBSo | .//TongTienThanhToan", "0")
        amount_words = self._get_text(t_toan, ".//TgTTTBChu | .//SoTienBangChu")

        summary = ParsedXMLSummary(
            subtotal=subtotal,
            vat_amount=vat_amount,
            total_amount=total_amount,
            amount_in_words=amount_words,
        )

        # 6. Digital Signature
        signature = self.signature_verifier.verify_signature(root)

        logger.info(
            f"Successfully parsed XML invoice: series={metadata.invoice_series}, "
            f"no={metadata.invoice_number}, total={summary.total_amount}"
        )

        return RawParsedXMLResult(
            metadata=metadata,
            seller=seller,
            buyer=buyer,
            items=items,
            summary=summary,
            signature=signature,
            schema_valid=schema_valid,
            schema_errors=schema_errors,
        )
