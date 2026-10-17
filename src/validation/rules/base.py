from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Optional
from src.normalization.schemas import NormalizedInvoice


class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class ValidationIssue:
    rule_code: str
    field_name: str
    severity: Severity
    message: str
    passed: bool
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None


class ValidationRule(ABC):
    """Abstract interface for deterministic validation rules."""

    @abstractmethod
    def evaluate(self, invoice: NormalizedInvoice) -> List[ValidationIssue]:
        pass
