from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from src.classifier.router import InputClassifier
from src.classifier.schemas import DocumentFormat, ProcessingPipelineType
from src.confidence.engine import ConfidenceEngine
from src.confidence.schemas import ConfidenceEvaluationResult, RoutingDecision
from src.core.logging import logger
from src.database.repositories.invoice_repo import InvoiceRepository
from src.ingestion.base import RawDocument
from src.integration.erp.exporter import ERPIntegrationEngine
from src.normalization.normalizer import InvoiceNormalizer
from src.normalization.schemas import NormalizedInvoice
from src.pipelines.ai.extraction.field_extractor import AIFieldExtractor
from src.pipelines.ai.layout.detector import LayoutDetector
from src.pipelines.ai.ocr.engine import OCREngine
from src.pipelines.ai.preprocessing.preprocessor import DocumentPreprocessor
from src.pipelines.xml.parser import XMLInvoiceParser
from src.review.workflow import ReviewWorkflowManager
from src.storage.object_storage import StorageService, get_storage_service
from src.validation.engine import ValidationEngine, ValidationReport


@dataclass
class ProcessingPipelineResult:
    document_id: str
    file_name: str
    pipeline_type: str
    normalized_invoice: NormalizedInvoice
    validation_report: ValidationReport
    confidence_evaluation: ConfidenceEvaluationResult
    routing_decision: RoutingDecision
    erp_post_result: Optional[Dict[str, Any]] = None


class InvoicePipelineOrchestrator:
    """
    End-to-End Invoice Processing Orchestrator.
    Directly reflects the enterprise architecture pipeline:
    Input -> Classifier -> XML / AI Pipeline -> Normalization ->
    Validation Engine -> Confidence Engine -> Approved / Review ->
    Invoice Database -> ERP / Export.
    """

    def __init__(self, storage: Optional[StorageService] = None):
        self.storage = storage or get_storage_service()
        self.classifier = InputClassifier()

        # XML Branch
        self.xml_parser = XMLInvoiceParser()

        # AI Branch
        self.preprocessor = DocumentPreprocessor()
        self.ocr_engine = OCREngine()
        self.layout_detector = LayoutDetector()
        self.field_extractor = AIFieldExtractor()

        # Normalization
        self.normalizer = InvoiceNormalizer()

        # Validation Engine
        self.validation_engine = ValidationEngine()

        # Confidence Engine
        self.confidence_engine = ConfidenceEngine()

        # Review & ERP
        self.review_manager = ReviewWorkflowManager()
        self.erp_engine = ERPIntegrationEngine()

    def process_document(self, raw_doc: RawDocument, db: Optional[Session] = None) -> ProcessingPipelineResult:
        logger.info(f"=== Starting pipeline for document: {raw_doc.file_name} (ID: {raw_doc.document_id}) ===")

        # Step 1: Save raw document to object storage
        storage_path, file_hash = self.storage.save(raw_doc.file_bytes, raw_doc.file_name)
        raw_doc.storage_path = storage_path
        raw_doc.file_hash = file_hash

        # Step 2: Input Classifier
        classification = self.classifier.classify_single(raw_doc)

        # Step 3: Branch Execution (XML vs AI Document Processing)
        if classification.target_pipeline == ProcessingPipelineType.XML_PIPELINE:
            logger.info("Executing Branch: XML Processing")
            raw_xml_result = self.xml_parser.parse(raw_doc.file_bytes)
            normalized_invoice = self.normalizer.normalize_from_xml(
                raw_xml=raw_xml_result,
                document_id=raw_doc.document_id,
                file_name=raw_doc.file_name,
                source=raw_doc.source.value,
                file_hash=file_hash,
                storage_path=storage_path
            )
        else:
            logger.info("Executing Branch: AI Document Processing")
            # AI Sub-pipeline: Preprocessing -> OCR -> Layout -> Table & Extraction
            pages = self.preprocessor.process(raw_doc.file_bytes, raw_doc.file_name)
            first_page = pages[0] if pages else None
            ocr_res = self.ocr_engine.extract(first_page)
            regions = self.layout_detector.detect_regions(ocr_res)
            raw_ai_result = self.field_extractor.extract(ocr_res, regions)

            normalized_invoice = self.normalizer.normalize_from_ai(
                raw_ai=raw_ai_result,
                document_id=raw_doc.document_id,
                file_name=raw_doc.file_name,
                source=raw_doc.source.value,
                doc_format=classification.detected_format.value,
                file_hash=file_hash,
                storage_path=storage_path
            )

        # Step 4: Validation Engine (Rules + External Verify + Anomaly Detection)
        validation_report = self.validation_engine.validate(normalized_invoice)

        # Step 5: Confidence Engine (Evaluates composite score & validation -> Approved vs Review)
        confidence_eval = self.confidence_engine.evaluate(normalized_invoice, validation_report)

        # Step 6: Route handling & Database Persistence
        erp_result = None
        if confidence_eval.decision == RoutingDecision.APPROVED:
            logger.info(f"Invoice {normalized_invoice.metadata.invoice_number} APPROVED. Forwarding to ERP.")
            erp_result = self.erp_engine.post_to_erp(normalized_invoice)
        else:
            logger.info(f"Invoice {normalized_invoice.metadata.invoice_number} routed to REVIEW queue.")
            self.review_manager.assign_for_review(raw_doc.document_id)

        # Step 7: Transactional Database Persistence
        if db:
            repo = InvoiceRepository(db)
            repo.save_invoice_transactional(
                invoice=normalized_invoice,
                validation_report=validation_report,
                routing_status=confidence_eval.decision.value
            )

        logger.info(f"=== Completed processing for {raw_doc.file_name}: Result={confidence_eval.decision.value} ===")

        return ProcessingPipelineResult(
            document_id=raw_doc.document_id,
            file_name=raw_doc.file_name,
            pipeline_type=classification.target_pipeline.value,
            normalized_invoice=normalized_invoice,
            validation_report=validation_report,
            confidence_evaluation=confidence_eval,
            routing_decision=confidence_eval.decision,
            erp_post_result=erp_result
        )
