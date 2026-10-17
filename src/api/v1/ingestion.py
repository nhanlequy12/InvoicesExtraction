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

    return {
        "status": "success",
        "document_id": result.document_id,
        "file_name": result.file_name,
        "pipeline_used": result.pipeline_type,
        "routing_decision": result.routing_decision.value,
        "confidence_score": result.confidence_evaluation.composite_score,
        "validation_status": result.validation_report.status,
        "invoice": result.normalized_invoice.model_dump(mode="json"),
        "erp_result": result.erp_post_result
    }

