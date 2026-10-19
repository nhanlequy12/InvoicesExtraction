import uuid
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from src.api.dependencies import get_orchestrator
from src.core.database import get_db
from src.ingestion.base import IngestionSource, RawDocument
from src.orchestrator.pipeline_runner import InvoicePipelineOrchestrator

router = APIRouter(prefix="/ingest", tags=["Ingestion"])


@router.post("/upload", status_code=status.HTTP_200_OK)
async def upload_invoice_file(
    file: UploadFile = File(...),
    orchestrator: InvoicePipelineOrchestrator = Depends(get_orchestrator),
    db: Session = Depends(get_db)
):
    """
    Direct File Ingestion endpoint (XML, PDF, PNG, JPG).
    Routes file into Input Classifier -> Processing Pipeline -> Validation -> Database.
    """
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    raw_doc = RawDocument(
        document_id=str(uuid.uuid4()),
        source=IngestionSource.API,
        file_name=file.filename or "uploaded_invoice",
        file_bytes=content,
        content_type=file.content_type
    )

    result = orchestrator.process_document(raw_doc, db=db)

    response = {
        "status": "success",
        "document_id": result.document_id,
        "file_name": result.file_name,
        "pipeline_used": result.pipeline_type,
    }

    if result.full_text is not None:
        response["full_text"] = result.full_text

    if result.raw_ai_result is not None:
        response["extracted_fields"] = {
            k: v.value for k, v in result.raw_ai_result.fields.items() if v.value is not None
        }
        response["table_items"] = [
            {
                "line_number": item.line_number,
                "description": item.description,
                "unit": item.unit,
                "quantity": float(item.quantity) if item.quantity is not None else None,
                "unit_price": float(item.unit_price) if item.unit_price is not None else None,
                "amount": float(item.amount_before_tax) if item.amount_before_tax is not None else None,
            }
            for item in result.raw_ai_result.line_items
        ]
        if hasattr(result.raw_ai_result, "warnings") and result.raw_ai_result.warnings:
            response["warnings"] = result.raw_ai_result.warnings
        if hasattr(result.raw_ai_result, "tax_ids_found") and result.raw_ai_result.tax_ids_found:
            response["tax_ids_found"] = result.raw_ai_result.tax_ids_found
        if result.regions:
            response["regions"] = [
                {
                    "type": r.region_type.value if hasattr(r.region_type, "value") else str(r.region_type),
                    "box": r.box,
                    "confidence": r.confidence,
                    "token_count": len(r.tokens)
                }
                for r in result.regions
            ]

    if result.routing_decision is not None:
        response["routing_decision"] = result.routing_decision.value
    if result.confidence_evaluation is not None:
        response["confidence_score"] = result.confidence_evaluation.composite_score
    if result.validation_report is not None:
        response["validation_status"] = result.validation_report.status
    if result.normalized_invoice is not None:
        response["invoice"] = result.normalized_invoice.model_dump(mode="json")
    if result.erp_post_result is not None:
        response["erp_result"] = result.erp_post_result

    return response

