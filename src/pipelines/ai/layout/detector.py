from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
from src.core.logging import logger
from src.pipelines.ai.ocr.engine import OCRResult, OCRToken


class LayoutRegionType(str, Enum):
    HEADER = "header"
    SELLER = "seller"
    BUYER = "buyer"
    TABLE = "table"
    TOTALS = "totals"
    PAYMENT_INFO = "payment_info"
    FOOTER = "footer"
    SIGNATURE = "signature"
    OTHER = "other"


@dataclass
class LayoutRegion:
    region_type: LayoutRegionType
    box: List[int]  # [x1, y1, x2, y2]
    confidence: float
    tokens: List[OCRToken]


class LayoutDetector:
    """
    Layout Analysis Engine.
    Employs spatial positioning and semantic heuristics to segment document
    structural zones (Header, Seller, Buyer, Item Table, Totals, Payment Info, Footer).
    Specifically tailored to both Vietnamese e-invoices and standard international tax invoices.
    """

    def __init__(self, confidence_threshold: float = 0.80):
        self.confidence_threshold = confidence_threshold

    def detect_regions(self, ocr_result: OCRResult) -> List[LayoutRegion]:
        tokens = ocr_result.tokens
        if not tokens:
            return []

        page_w = max((t.box[2] for t in tokens), default=1000)
        page_h = max((t.box[3] for t in tokens), default=1000)

        # 1. Identify table header Y-coordinate
        table_header_keywords = [
            "items", "item", "description", "quantity", "qty", "price",
            "unit price", "amount", "stt", "thhdvu", "tên hàng hóa",
            "đơn vị tính", "số lượng", "đơn giá", "thành tiền"
        ]
        tbl_hdr_tokens = [
            t for t in tokens
            if any(k in t.text.lower() for k in table_header_keywords)
        ]
        if tbl_hdr_tokens:
            tbl_top_y = min(t.box[1] for t in tbl_hdr_tokens)
        else:
            tbl_top_y = 0.40 * page_h

        # 2. Identify totals / bottom section Y-coordinate
        totals_keywords = [
            "sub_total", "subtotal", "sub total", "total in words", "bank name",
            "branch name", "total :", "total:", "tổng cộng", "tiền thanh toán",
            "cộng tiền hàng", "tiền thuế"
        ]
        totals_tokens_found = [
            t for t in tokens
            if any(k in t.text.lower() for k in totals_keywords)
        ]
        if totals_tokens_found:
            totals_top_y = min(t.box[1] for t in totals_tokens_found)
        else:
            totals_top_y = 0.72 * page_h

        # Categorize tokens into semantic regions
        header_tokens: List[OCRToken] = []
        seller_tokens: List[OCRToken] = []
        buyer_tokens: List[OCRToken] = []
        table_tokens: List[OCRToken] = []
        payment_tokens: List[OCRToken] = []
        totals_tokens: List[OCRToken] = []
        footer_tokens: List[OCRToken] = []

        header_keywords = [
            "tax invoice", "invoice", "date:", "due date", "po number",
            "hóa đơn", "mẫu số", "ký hiệu", "số:", "số hóa đơn"
        ]
        buyer_keywords = [
            "bill to", "buyer", "customer", "khách hàng", "người mua",
            "tel:", "site:", "ship to"
        ]
        payment_keywords = [
            "total in words", "bank name", "branch name", "account number",
            "bank account", "swift code", "swift", "ngân hàng", "stk", "tài khoản"
        ]
        footer_keywords = [
            "note:", "note :", "shipped through", "ghi chú", "lưu ý"
        ]

        for token in tokens:
            y_mid = (token.box[1] + token.box[3]) / 2.0
            x_mid = (token.box[0] + token.box[2]) / 2.0
            lower = token.text.lower().strip()

            # Footer: very bottom or explicit note
            if any(k in lower for k in footer_keywords) or (y_mid > 0.90 * page_h and not any(k in lower for k in ["total", "bank"])):
                footer_tokens.append(token)
            # Above table: Header, Seller (left), Buyer (right)
            elif y_mid < tbl_top_y - 10:
                if any(k in lower for k in header_keywords) or (y_mid < 0.14 * page_h and x_mid >= 0.40 * page_w):
                    header_tokens.append(token)
                elif any(k in lower for k in buyer_keywords) or x_mid >= 0.48 * page_w:
                    buyer_tokens.append(token)
                else:
                    seller_tokens.append(token)
            # Within table: between table header and totals
            elif y_mid < totals_top_y - 10:
                table_tokens.append(token)
            # Below table: Payment info (left) vs Totals (right)
            else:
                if any(k in lower for k in payment_keywords) or x_mid < 0.48 * page_w:
                    payment_tokens.append(token)
                else:
                    totals_tokens.append(token)

        regions: List[LayoutRegion] = []

        def _make_region(rtype: LayoutRegionType, group_tokens: List[OCRToken], default_conf: float = 0.90):
            if not group_tokens:
                return
            x1 = int(min(t.box[0] for t in group_tokens))
            y1 = int(min(t.box[1] for t in group_tokens))
            x2 = int(max(t.box[2] for t in group_tokens))
            y2 = int(max(t.box[3] for t in group_tokens))

            # Table grid spans across the invoice content width
            if rtype == LayoutRegionType.TABLE and tokens:
                min_page_x = int(min(t.box[0] for t in tokens))
                max_page_x = int(max(t.box[2] for t in tokens))
                x1 = min(x1, min_page_x)
                x2 = max(x2, max_page_x)

            conf = sum(t.confidence for t in group_tokens) / len(group_tokens) if group_tokens else default_conf
            regions.append(LayoutRegion(
                region_type=rtype,
                box=[x1, y1, x2, y2],
                confidence=round(conf, 2),
                tokens=group_tokens
            ))

        _make_region(LayoutRegionType.HEADER, header_tokens, 0.92)
        _make_region(LayoutRegionType.SELLER, seller_tokens, 0.88)
        _make_region(LayoutRegionType.BUYER, buyer_tokens, 0.88)
        _make_region(LayoutRegionType.TABLE, table_tokens, 0.85)
        _make_region(LayoutRegionType.PAYMENT_INFO, payment_tokens, 0.88)
        _make_region(LayoutRegionType.TOTALS, totals_tokens, 0.92)
        _make_region(LayoutRegionType.FOOTER, footer_tokens, 0.85)

        logger.info(
            f"Detected {len(regions)} layout region(s) on page {ocr_result.page_number}: "
            f"{[r.region_type.value for r in regions]}"
        )
        return regions
