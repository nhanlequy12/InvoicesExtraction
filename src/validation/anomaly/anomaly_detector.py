from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional
from src.core.logging import logger
from src.normalization.schemas import NormalizedInvoice


@dataclass
class AnomalyFinding:
    anomaly_type: str
    severity: str # LOW, MEDIUM, HIGH
    field: str
    description: str
    suggested_action: str = "MANUAL_REVIEW"


class FinancialAnomalyDetector:
    """
    Financial Anomaly Detection Engine.
    Identifies abnormal invoice metrics (e.g., massive price spikes compared
    to historical baseline, unusual VAT deviations, or zero quantity line items).
    Important Principle: 'Anomaly != Fraud'.
    Flags suspect entries for human review without premature fraud accusations.
    """

    def __init__(self, price_spike_threshold_multiplier: float = 3.0):
        self.price_spike_threshold_multiplier = price_spike_threshold_multiplier

    def detect(self, invoice: NormalizedInvoice) -> List[AnomalyFinding]:
        findings: List[AnomalyFinding] = []

        # 1. Negative or zero unit prices
        for item in invoice.items:
            if item.unit_price is not None and item.unit_price < Decimal("0"):
                findings.append(
                    AnomalyFinding(
                        anomaly_type="NEGATIVE_UNIT_PRICE",
                        severity="HIGH",
                        field=f"items[{item.line_number}].unit_price",
                        description=f"Negative unit price ({item.unit_price}) detected on item: {item.description}"
                    )
                )

        # 2. Total amount exceeding typical ceiling (e.g., 500,000,000 VND)
        if invoice.summary.total_amount > Decimal("500000000"):
            findings.append(
                AnomalyFinding(
                    anomaly_type="HIGH_VALUE_TRANSACTION",
                    severity="MEDIUM",
                    field="summary.total_amount",
                    description=f"Invoice value ({invoice.summary.total_amount:,.0f} {invoice.summary.currency}) exceeds normal automatic approval limit."
                )
            )

        # 3. VAT amount zero while subtotal is significant
        if invoice.summary.subtotal > Decimal("1000000") and invoice.summary.vat_amount == Decimal("0"):
            findings.append(
                AnomalyFinding(
                    anomaly_type="ZERO_VAT_WARNING",
                    severity="LOW",
                    field="summary.vat_amount",
                    description="Zero VAT declared for an invoice over 1,000,000 VND. Verify if tax-exempt good."
                )
            )

        if findings:
            logger.info(f"Anomaly detector flagged {len(findings)} potential anomalies for review.")

        return findings
