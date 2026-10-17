from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, List, Optional
from src.core.logging import logger


@dataclass
class AuditRecord:
    invoice_id: str
    field_name: str
    old_value: Any
    new_value: Any
    reviewer: str
    reason: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


class AuditTrailService:
    """
    Immutable Financial Audit Trail Service.
    Records every manual field override by human reviewers.
    Essential for compliance, tax audits, and accountability.
    """

    def __init__(self):
        self._audit_log: List[AuditRecord] = []

    def record_change(
        self,
        invoice_id: str,
        field_name: str,
        old_value: Any,
        new_value: Any,
        reviewer: str,
        reason: str
    ) -> AuditRecord:
        record = AuditRecord(
            invoice_id=invoice_id,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            reviewer=reviewer,
            reason=reason
        )
        self._audit_log.append(record)
        logger.info(
            f"AUDIT LOG: [Invoice {invoice_id}] Field '{field_name}' changed from '{old_value}' "
            f"to '{new_value}' by {reviewer}. Reason: {reason}"
        )
        return record

    def get_audit_trail(self, invoice_id: str) -> List[AuditRecord]:
        return [r for r in self._audit_log if r.invoice_id == invoice_id]
