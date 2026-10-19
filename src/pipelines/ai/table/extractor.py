from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
import re
from typing import List, Optional
from src.core.logging import logger
from src.pipelines.ai.layout.detector import LayoutRegion, LayoutRegionType
from src.pipelines.ai.ocr.engine import OCRResult, OCRToken


@dataclass
class ExtractedTableCell:
    text: str
    row_idx: int
    col_idx: int
    box: List[int]
    confidence: float


@dataclass
class ExtractedTableRow:
    line_number: int
    product_code: Optional[str] = None
    description: str = ""
    unit: Optional[str] = None
    quantity: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    discount: Optional[Decimal] = None
    amount_before_tax: Decimal = Decimal("0")
    vat_rate: Optional[str] = None
    vat_amount: Optional[Decimal] = None
    confidence: float = 0.85


class TableExtractor:
    """
    Table Detection and Cell Alignment Engine.
    Uses spatial token clustering (Y-axis line clustering and X-axis column alignment)
    to parse rows and extract item descriptions, quantities, unit prices, and amounts.
    """

    def __init__(self):
        pass

    def extract_table(
        self,
        table_region: Optional[LayoutRegion],
        ocr_result: Optional[OCRResult] = None
    ) -> List[ExtractedTableRow]:
        tokens: List[OCRToken] = []
        if table_region and table_region.tokens:
            tokens = table_region.tokens
        elif ocr_result and ocr_result.tokens:
            # Fallback: scan tokens between header keywords and totals
            tokens = [t for t in ocr_result.tokens]

        if not tokens:
            return []

        # 1. Group tokens into horizontal lines based on Y-mid proximity
        lines = self._cluster_tokens_into_lines(tokens)
        if not lines:
            return []

        # 2. Check if the first line is the table header (e.g. ITEMS, QUANTITY, PRICE)
        header_keywords = [
            "items", "item", "description", "quantity", "qty", "price",
            "unit price", "amount", "stt", "thhdvu", "tên hàng hóa", "đơn giá",
            "thành tiền", "đơn vị tính"
        ]
        first_line_txt = " ".join(t.text.lower() for t in lines[0])
        is_header = any(k in first_line_txt for k in header_keywords)

        data_lines = lines[1:] if is_header and len(lines) > 1 else lines

        # 3. Parse each row line into an ExtractedTableRow
        rows: List[ExtractedTableRow] = []
        for idx, line in enumerate(data_lines, start=1):
            row = self._parse_row_line(line, idx)
            if row and row.description:
                rows.append(row)

        logger.info(f"Extracted {len(rows)} table row(s) from invoice table.")
        return rows

    def _cluster_tokens_into_lines(self, tokens: List[OCRToken]) -> List[List[OCRToken]]:
        """
        Clusters tokens into horizontal row lines based on vertical overlap.
        """
        sorted_tokens = sorted(
            tokens,
            key=lambda t: ((t.box[1] + t.box[3]) / 2.0, t.box[0])
        )
        lines: List[List[OCRToken]] = []

        for token in sorted_tokens:
            y_mid = (token.box[1] + token.box[3]) / 2.0
            height = max(10, token.box[3] - token.box[1])
            assigned = False

            for line in lines:
                line_y_mid = sum((t.box[1] + t.box[3]) / 2.0 for t in line) / len(line)
                if abs(y_mid - line_y_mid) <= max(14.0, height * 0.6):
                    line.append(token)
                    assigned = True
                    break

            if not assigned:
                lines.append([token])

        # Sort tokens within each line from left to right (X-axis)
        for line in lines:
            line.sort(key=lambda t: t.box[0])

        return lines

    def _clean_number(self, text: str) -> Optional[Decimal]:
        """Strips currency symbols, spaces, and commas to parse clean Decimal."""
        cleaned = re.sub(r"[^\d.,]", "", text)
        if not cleaned:
            return None
        # Handle format: 1,234.56 vs 1.234,56
        if "," in cleaned and "." in cleaned:
            if cleaned.rfind(",") > cleaned.rfind("."):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            # Check if comma is decimal (e.g. 12,50)
            parts = cleaned.split(",")
            if len(parts) == 2 and len(parts[1]) in (1, 2):
                cleaned = cleaned.replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None

    def _parse_row_line(self, line_tokens: List[OCRToken], line_idx: int) -> Optional[ExtractedTableRow]:
        """
        Extracts description, quantity, price, and amount from a single line of tokens.
        """
        if not line_tokens:
            return None

        # Identify numeric tokens vs text tokens
        num_tokens = []
        for i, t in enumerate(line_tokens):
            raw_txt = t.text.strip()
            # If token has digits and is not a purely alphanumeric word like 'iPhone14'
            if re.search(r"\d", raw_txt) and not re.search(r"[a-zA-Z]{4,}", raw_txt):
                val = self._clean_number(raw_txt)
                if val is not None:
                    num_tokens.append((i, val, t))

        desc = ""
        qty: Optional[Decimal] = None
        price: Optional[Decimal] = None
        amount: Decimal = Decimal("0")
        unit: Optional[str] = None
        known_units = ["cái", "cai", "bộ", "bo", "kg", "pcs", "set", "thùng", "thung", "hộp", "hop", "chiếc"]

        used_indices = set()

        if len(num_tokens) >= 3:
            # 3 numbers: e.g. Qty, Unit Price, Total Amount (or Line Number, Qty, Price)
            # Check if first number is a small integer (line number)
            first_idx, first_val, _ = num_tokens[0]
            if first_val == Decimal(line_idx) or (first_val.as_integer_ratio()[1] == 1 and first_val < 100 and first_idx == 0):
                used_indices.add(first_idx)
                # Next two numbers are qty and price
                qty_idx, qty, _ = num_tokens[1]
                price_idx, price, _ = num_tokens[2]
                used_indices.add(qty_idx)
                used_indices.add(price_idx)
                if len(num_tokens) >= 4:
                    amt_idx, amt_val, _ = num_tokens[3]
                    amount = amt_val
                    used_indices.add(amt_idx)
                else:
                    amount = qty * price
            else:
                # Qty, Unit Price, Total Amount
                qty_idx, qty, _ = num_tokens[-3]
                price_idx, price, _ = num_tokens[-2]
                amt_idx, amt_val, _ = num_tokens[-1]
                amount = amt_val
                used_indices.update([qty_idx, price_idx, amt_idx])

        elif len(num_tokens) == 2:
            # 2 numbers: typically Quantity and Price
            qty_idx, qty, _ = num_tokens[0]
            price_idx, price, _ = num_tokens[1]
            amount = qty * price
            used_indices.update([qty_idx, price_idx])

        elif len(num_tokens) == 1:
            # 1 number: Price / Amount
            price_idx, price, _ = num_tokens[0]
            qty = Decimal("1")
            amount = price
            used_indices.add(price_idx)

        # Remaining tokens form description and unit
        text_tokens = [t for i, t in enumerate(line_tokens) if i not in used_indices]
        for t in text_tokens:
            if t.text.lower().strip() in known_units and unit is None:
                unit = t.text.strip()
            else:
                desc += " " + t.text.strip()

        desc = desc.strip()
        # Remove any leading index if still present
        desc = re.sub(r"^\d+[\.\-]?\s*", "", desc)

        if not desc and price is not None:
            desc = f"Item {line_idx}"

        conf = sum(t.confidence for t in line_tokens) / len(line_tokens) if line_tokens else 0.85

        return ExtractedTableRow(
            line_number=line_idx,
            description=desc,
            unit=unit,
            quantity=qty,
            unit_price=price,
            amount_before_tax=amount,
            confidence=round(conf, 2)
        )
