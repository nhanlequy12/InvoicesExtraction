from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class RoutingDecision(str, Enum):
    APPROVED = "APPROVED"
    REVIEW = "REVIEW"


class ConfidenceEvaluationResult(BaseModel):
    decision: RoutingDecision
    composite_score: float
    min_field_score: float
    field_scores: Dict[str, float]
    reasons: List[str]
    is_auto_approvable: bool
