from typing import Dict
from src.core.logging import logger
from src.normalization.schemas import NormalizedInvoice


class ConfidenceScorer:
    """
    Weighted Confidence Scorer.
    Computes weighted average based on field criticality:
    Seller Tax ID (20%), Total Amount (20%), Invoice Number (15%), Items (15%), etc.
    """

    DEFAULT_WEIGHTS = {
        "seller.tax_id": 0.20,
        "summary.total_amount": 0.20,
        "metadata.invoice_number": 0.15,
        "metadata.invoice_series": 0.10,
        "metadata.issue_date": 0.10,
        "summary.vat_amount": 0.10,
        "items": 0.15,
    }

    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or self.DEFAULT_WEIGHTS

    def calculate_score(self, invoice: NormalizedInvoice) -> tuple[float, float, Dict[str, float]]:
        field_confs = invoice.confidence.field_confidences.copy()

        # If XML, default confidence is 1.0
        if invoice.document.format == "xml":
            for k in self.weights.keys():
                field_confs.setdefault(k, 1.0)

        total_weight = 0.0
        weighted_sum = 0.0
        min_score = 1.0

        for field_name, weight in self.weights.items():
            conf = field_confs.get(field_name, 0.85)
            weighted_sum += conf * weight
            total_weight += weight
            if conf < min_score:
                min_score = conf

        composite_score = weighted_sum / total_weight if total_weight > 0 else 0.85
        return composite_score, min_score, field_confs
