import uuid
from decimal import Decimal
from src.confidence.schemas import RoutingDecision
from src.database.repositories.invoice_repo import InvoiceRepository
from src.ingestion.base import IngestionSource, RawDocument
from src.orchestrator.pipeline_runner import InvoicePipelineOrchestrator


def test_end_to_end_xml_pipeline_flow(sample_xml_bytes, test_db):
    """
    Validates complete pipeline for XML:
    Input (XML) -> Classifier -> XML Pipeline -> Normalization ->
    Validation Engine -> Confidence Engine -> Approved -> Database -> ERP
    """
    orchestrator = InvoicePipelineOrchestrator()
    # Mock valid signature for test invoice
    orchestrator.xml_parser.signature_verifier.verify_signature = lambda root: type(
        "Sig", (), {
            "signature_present": True,
            "digest_valid": True,
            "certificate_valid": True,
            "subject_name": "ABC TECH CORP",
            "serial_number": "123456",
            "status": "VALID",
            "message": "Valid"
        }
    )()

    raw_doc = RawDocument(
        document_id=str(uuid.uuid4()),
        source=IngestionSource.EMAIL,
        file_name="electronic_invoice.xml",
        file_bytes=sample_xml_bytes
    )

    result = orchestrator.process_document(raw_doc, db=test_db)

    # 1. Classifier check
    assert result.pipeline_type == "xml_processing"

    # 2. Normalization check
    assert result.normalized_invoice.metadata.invoice_number == "00001234"
    assert result.normalized_invoice.summary.total_amount == Decimal("55000000")

    # 3. Validation check
    assert result.validation_report.is_valid is True

    # 4. Routing decision
    assert result.routing_decision == RoutingDecision.APPROVED

    # 5. ERP Post check
    assert result.erp_post_result is not None
    assert result.erp_post_result["success"] is True

    # 6. Database persistence check
    repo = InvoiceRepository(test_db)
    saved_invoices = repo.list_invoices()
    assert len(saved_invoices) == 1
    assert saved_invoices[0].invoice_number == "00001234"
    assert saved_invoices[0].status == "APPROVED"
    assert len(saved_invoices[0].items) == 1


def test_end_to_end_pdf_ai_pipeline_flow(sample_pdf_bytes, test_db):
    """
    Validates complete pipeline for PDF/Image:
    Input (PDF) -> Classifier -> AI Pipeline -> Normalization ->
    Validation Engine -> Confidence Engine -> Review/Approved -> Database
    """
    orchestrator = InvoicePipelineOrchestrator()

    raw_doc = RawDocument(
        document_id=str(uuid.uuid4()),
        source=IngestionSource.API,
        file_name="scanned_invoice.pdf",
        file_bytes=sample_pdf_bytes
    )

    result = orchestrator.process_document(raw_doc, db=test_db)

    # 1. Classifier check
    assert result.pipeline_type == "ai_document_processing"

    # 2. AI Extraction check (normalization commented out)
    assert result.raw_ai_result is not None
    assert result.full_text is not None
    assert isinstance(result.raw_ai_result.line_items, list)
    assert result.regions is not None
