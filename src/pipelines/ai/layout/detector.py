from dataclasses import dataclass
from enum import Enum
from typing import List
from src.core.logging import logger
from src.pipelines.ai.ocr.engine import OCRResult, OCRToken


class LayoutRegionType(str, Enum):
    HEADER = "header"
    SELLER = "seller"
    BUYER = "buyer"
    TABLE = "table"
    TOTALS = "totals"
    SIGNATURE = "signature"
    OTHER = "other"


@dataclass
class LayoutRegion:
    region_type: LayoutRegionType
    box: List[int] # [x1, y1, x2, y2]
    confidence: float
    tokens: List[OCRToken]


class LayoutDetector:
    """
    Layout Analysis Engine.
    Employs LayoutLMv3 / YOLO / DETR or spatial heuristics to detect
    document structural zones (Header, Seller, Buyer, Item Table, Totals, Signature).
    """

    def __init__(self, confidence_threshold: float = 0.80):
        self.confidence_threshold = confidence_threshold

    def detect_regions(self, ocr_result: OCRResult) -> List[LayoutRegion]:
        regions: List[LayoutRegion] = []
        # In production, invokes deep learning model (e.g., LayoutLMv3 or YOLOv8-DocLayNet)
        # Groups tokens spatially into semantic zones:
        tokens = ocr_result.tokens

        seller_tokens = []
        buyer_tokens = []
        table_tokens = []
        totals_tokens = []
        header_tokens = []

        for token in tokens:
            lower = token.text.lower()
            if any(k in lower for k in ["hóa đơn", "invoice", "mẫu số", "ký hiệu", "số:"]):
                header_tokens.append(token)
            elif any(k in lower for k in ["đơn vị bán", "người bán", "seller", "mst:"]):
                seller_tokens.append(token)
            elif any(k in lower for k in ["người mua", "buyer", "khách hàng"]):
                buyer_tokens.append(token)
            elif any(k in lower for k in ["tổng cộng", "cộng tiền", "tiền thuế", "thanh toán", "total"]):
                totals_tokens.append(token)
            else:
                table_tokens.append(token)

        if header_tokens:
            regions.append(LayoutRegion(LayoutRegionType.HEADER, [0, 0, 1000, 300], 0.90, header_tokens))
        if seller_tokens:
            regions.append(LayoutRegion(LayoutRegionType.SELLER, [0, 300, 1000, 600], 0.88, seller_tokens))
        if buyer_tokens:
            regions.append(LayoutRegion(LayoutRegionType.BUYER, [0, 600, 1000, 900], 0.88, buyer_tokens))
        if table_tokens:
            regions.append(LayoutRegion(LayoutRegionType.TABLE, [0, 900, 1000, 2000], 0.85, table_tokens))
        if totals_tokens:
            regions.append(LayoutRegion(LayoutRegionType.TOTALS, [0, 2000, 1000, 2500], 0.92, totals_tokens))

        logger.info(f"Detected {len(regions)} layout region(s) on page {ocr_result.page_number}")
        return regions
