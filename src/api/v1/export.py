from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session
from src.core.database import get_db
from src.database.models import InvoiceModel
from src.integration.export.file_exporter import InvoiceFileExporter
from src.normalization.schemas import (
    DocumentInfo,
    InvoiceMetadata,
    InvoiceParty,
    InvoiceSummary,
    InvoiceSignatureInfo,
    NormalizedInvoice,
)

router = APIRouter(prefix="/export", tags=["Export"])
exporter = InvoiceFileExporter()


def _convert_db_to_normalized(db_invoices: List[InvoiceModel]) -> List[NormalizedInvoice]:
    results = []
    for m in db_invoices:
        inv = NormalizedInvoice(
            document=DocumentInfo(
                document_id=m.document_id,
                source="database",
                file_name=f"inv_{m.invoice_number}.xml"
            ),
            metadata=InvoiceMetadata(
                form_number=m.form_number,
                invoice_series=m.invoice_series,
                invoice_number=m.invoice_number,
                issue_date=m.issue_date,
                tax_authority_code=m.tax_authority_code
            ),
            seller=InvoiceParty(
                name=m.seller_name or "",
                tax_id=m.seller_tax_id,
                address=m.seller_address
            ),
            buyer=InvoiceParty(
                name=m.buyer_name or "",
                tax_id=m.buyer_tax_id,
                address=m.buyer_address
            ),
            items=[],
            summary=InvoiceSummary(
                subtotal=m.subtotal,
                vat_amount=m.vat_amount,
                total_amount=m.total_amount,
                currency=m.currency
            ),
            signature=InvoiceSignatureInfo(
                present=True,
                status="VALID"
            )
        )
        results.append(inv)
    return results


@router.get("/excel", status_code=status.HTTP_200_OK)
def export_invoices_excel(
    status_filter: Optional[str] = Query("APPROVED"),
    db: Session = Depends(get_db)
):
    """Generates and downloads Excel (.xlsx) general purchase ledger."""
    query = db.query(InvoiceModel)
    if status_filter:
        query = query.filter(InvoiceModel.status == status_filter)
    invoices = query.all()

    norm_invoices = _convert_db_to_normalized(invoices)
    excel_bytes = exporter.export_to_excel(norm_invoices)

    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Bang_Ke_Hoa_Don.xlsx"}
    )


@router.get("/csv", status_code=status.HTTP_200_OK)
def export_invoices_csv(
    status_filter: Optional[str] = Query("APPROVED"),
    db: Session = Depends(get_db)
):
    """Generates and downloads CSV invoice export."""
    query = db.query(InvoiceModel)
    if status_filter:
        query = query.filter(InvoiceModel.status == status_filter)
    invoices = query.all()

    norm_invoices = _convert_db_to_normalized(invoices)
    csv_str = exporter.export_to_csv(norm_invoices)

    return Response(
        content=csv_str.encode("utf-8-sig"),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=Bang_Ke_Hoa_Don.csv"}
    )
