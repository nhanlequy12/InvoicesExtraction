from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.database.repositories.invoice_repo import InvoiceRepository

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.get("", status_code=status.HTTP_200_OK)
def list_invoices(
    status: Optional[str] = Query(None, description="Filter by status: APPROVED, REVIEW, etc."),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Lists processed invoices from database with optional status filter."""
    repo = InvoiceRepository(db)
    items = repo.list_invoices(status=status, limit=limit, offset=offset)
    return {
        "total": len(items),
        "items": [
            {
                "id": inv.id,
                "document_id": inv.document_id,
                "invoice_series": inv.invoice_series,
                "invoice_number": inv.invoice_number,
                "issue_date": inv.issue_date,
                "seller_name": inv.seller_name,
                "seller_tax_id": inv.seller_tax_id,
                "total_amount": float(inv.total_amount),
                "currency": inv.currency,
                "status": inv.status,
                "confidence": inv.confidence,
                "created_at": inv.created_at.isoformat() if inv.created_at else None
            }
            for inv in items
        ]
    }


@router.get("/{invoice_id}", status_code=status.HTTP_200_OK)
def get_invoice_detail(invoice_id: str, db: Session = Depends(get_db)):
    """Fetches comprehensive details of an invoice including items and validations."""
    repo = InvoiceRepository(db)
    inv = repo.get_by_id(invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found.")

    return {
        "id": inv.id,
        "metadata": {
            "form_number": inv.form_number,
            "invoice_series": inv.invoice_series,
            "invoice_number": inv.invoice_number,
            "issue_date": inv.issue_date,
            "tax_authority_code": inv.tax_authority_code
        },
        "seller": {
            "name": inv.seller_name,
            "tax_id": inv.seller_tax_id,
            "address": inv.seller_address
        },
        "buyer": {
            "name": inv.buyer_name,
            "tax_id": inv.buyer_tax_id,
            "address": inv.buyer_address
        },
        "summary": {
            "subtotal": float(inv.subtotal),
            "vat_amount": float(inv.vat_amount),
            "total_amount": float(inv.total_amount),
            "currency": inv.currency
        },
        "status": inv.status,
        "confidence": inv.confidence,
        "items": [
            {
                "line_number": it.line_number,
                "description": it.description,
                "unit": it.unit,
                "quantity": float(it.quantity) if it.quantity else None,
                "unit_price": float(it.unit_price) if it.unit_price else None,
                "amount_before_tax": float(it.amount_before_tax),
                "vat_rate": it.vat_rate,
                "vat_amount": float(it.vat_amount) if it.vat_amount else None
            }
            for it in inv.items
        ],
        "validations": [
            {
                "rule_code": v.rule_code,
                "field": v.field,
                "severity": v.severity,
                "message": v.message,
                "passed": v.passed
            }
            for v in inv.validations
        ]
    }
