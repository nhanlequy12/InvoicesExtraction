from typing import List
from src.confidence.schemas import ConfidenceEvaluationResult, RoutingDecision
from src.confidence.scorer import ConfidenceScorer
from src.core.config import settings
from src.core.logging import logger
from src.normalization.schemas import NormalizedInvoice
from src.validation.engine import ValidationReport


class ConfidenceEngine:
    """
    Confidence Engine & Routing Decision Maker.
    Decides whether an invoice can be directly APPROVED or must be routed to REVIEW.
    Criteria for auto-approval:
    - Composite confidence >= threshold (default 0.92)
    - Minimum key field confidence >= 0.85
    - 0 Validation Errors
    - In XML invoices: digital signature present and valid
    """

    def __init__(
        self,
        approval_threshold: float = settings.CONFIDENCE_THRESHOLD_AUTO_APPROVE,
        review_threshold: float = settings.CONFIDENCE_THRESHOLD_MANUAL_REVIEW
    ):
        self.approval_threshold = approval_threshold
        self.review_threshold = review_threshold
        self.scorer = ConfidenceScorer()

    def evaluate(self, invoice: NormalizedInvoice, validation_report: ValidationReport) -> ConfidenceEvaluationResult:
        composite_score, min_score, field_scores = self.scorer.calculate_score(invoice)
        reasons: List[str] = []

        is_approvable = True

        # Check 1: Validation errors block auto-approval
        if validation_report.error_count > 0:
            is_approvable = False
            reasons.append(f"Validation reported {validation_report.error_count} blocking error(s).")

        # Check 2: Composite score threshold
        if composite_score < self.approval_threshold:
            is_approvable = False
            reasons.append(f"Composite confidence {composite_score:.2f} is below auto-approval threshold ({self.approval_threshold}).")

        # Check 3: Digital signature for XML invoices
        if invoice.document.format == "xml":
            if not invoice.signature.present or invoice.signature.status != "VALID":
                is_approvable = False
                reasons.append("XML e-invoice signature is missing or untrusted.")

        # Check 4: Taxpayer status
        if not validation_report.taxpayer_verification.exists or validation_report.taxpayer_verification.status != "ACTIVE":
            is_approvable = False
            reasons.append("Seller tax status is not confirmed ACTIVE in tax authority registry.")

        if is_approvable:
            decision = RoutingDecision.APPROVED
            reasons.append("All deterministic validation rules passed with high field confidence.")
        else:
            decision = RoutingDecision.REVIEW

        logger.info(
            f"Routing decision for invoice {invoice.metadata.invoice_number}: "
            f"{decision.value} (score={composite_score:.2f})"
        )

        return ConfidenceEvaluationResult(
            decision=decision,
            composite_score=composite_score,
            min_field_score=min_score,
            field_scores=field_scores,
            reasons=reasons,
            is_auto_approvable=is_approvable
        )
