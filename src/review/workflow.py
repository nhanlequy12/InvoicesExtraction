from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from src.core.logging import logger


class ReviewStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    UNDER_REVIEW = "UNDER_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


@dataclass
class ReviewAction:
    invoice_id: str
    reviewer_id: str
    action: ReviewStatus
    corrections: Dict[str, Any] # field_name -> new_value
    notes: Optional[str] = None
    timestamp: datetime = datetime.utcnow()


class ReviewWorkflowManager:
    """Manages Human-In-The-Loop review states and accountant approvals."""

    def __init__(self):
        self._reviews: Dict[str, ReviewStatus] = {}

    def assign_for_review(self, invoice_id: str) -> ReviewStatus:
        self._reviews[invoice_id] = ReviewStatus.PENDING_REVIEW
        logger.info(f"Invoice {invoice_id} queued for human review.")
        return ReviewStatus.PENDING_REVIEW

    def apply_decision(self, action: ReviewAction) -> ReviewStatus:
        self._reviews[action.invoice_id] = action.action
        logger.info(f"Reviewer {action.reviewer_id} set invoice {action.invoice_id} status to {action.action.value}")
        return action.action
