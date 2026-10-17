from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.database.models import AuditLogModel, InvoiceModel, ReviewRecordModel

router = APIRouter(prefix="/reviews", tags=["Human Review"])


class ReviewSubmission(BaseModel):
    reviewer: str
    decision: str # APPROVED, REJECTED
    corrections: Dict[str, Any] = {} # e.g. {"summary.total_amount": 56000000}
    notes: Optional[str] = None


@router.get("/queue", status_code=status.HTTP_200_OK)
def get_review_queue(db: Session = Depends(get_db)):
    """Lists invoices currently awaiting manual human review."""
    pending = db.query(InvoiceModel).filter(InvoiceModel.status == "REVIEW").all()
    return {
        "count": len(pending),
        "invoices": [
            {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "invoice_series": inv.invoice_series,
                "seller_name": inv.seller_name,
                "total_amount": float(inv.total_amount),
                "confidence": inv.confidence,
                "created_at": inv.created_at.isoformat() if inv.created_at else None
            }
            for inv in pending
        ]
    }


@router.post("/{invoice_id}/decision", status_code=status.HTTP_200_OK)
def submit_review_decision(
    invoice_id: str,
    payload: ReviewSubmission,
    db: Session = Depends(get_db)
):
    """Submits manual accountant decision, records immutable audit trail, updates status."""
    inv = db.query(InvoiceModel).filter(InvoiceModel.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found.")

    # Apply any field corrections and log audit trail
    for field_name, new_val in payload.corrections.items():
        audit = AuditLogModel(
            invoice_id=inv.id,
            field=field_name,
            old_value=str(getattr(inv, field_name, "")),
            new_value=str(new_val),
            reviewer=payload.reviewer,
            reason=payload.notes or "Manual accountant correction in review queue"
        )
        db.add(audit)
        if hasattr(inv, field_name):
            setattr(inv, field_name, new_val)

    inv.status = payload.decision.upper()

    rev_record = ReviewRecordModel(
        invoice_id=inv.id,
        reviewer=payload.reviewer,
        status=payload.decision.upper(),
        notes=payload.notes
    )
    db.add(rev_record)
    db.commit()

    return {
        "status": "success",
        "invoice_id": inv.id,
        "new_status": inv.status,
        "message": f"Review completed by {payload.reviewer}."
    }
