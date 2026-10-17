from typing import List, Optional
from src.classifier.detector import FormatDetector
from src.classifier.schemas import ClassificationResult, DocumentFormat, ProcessingPipelineType
from src.core.logging import logger
from src.ingestion.base import RawDocument


class InputClassifier:
    """
    Input Classifier Engine.
    Implements Core Rule: 'Structured First, AI Second'.
    When XML is available, route to XML Processing pipeline.
    When PDF/Image is available, route to AI Document Processing pipeline.
    When a bundle contains both XML and PDF, XML is extracted as authoritative,
    and PDF is linked for visual verification.
    """

    def __init__(self):
        self.detector = FormatDetector()

    def classify_single(self, document: RawDocument) -> ClassificationResult:
        doc_format, mime_type = self.detector.detect_format(
            document.file_name,
            document.file_bytes
        )

        if doc_format == DocumentFormat.XML:
            pipeline = ProcessingPipelineType.XML_PIPELINE
            reason = "Structured XML e-invoice detected: routing to XML Processing (Parser + Signature Verification)."
        elif doc_format in (DocumentFormat.PDF, DocumentFormat.IMAGE):
            pipeline = ProcessingPipelineType.AI_DOCUMENT_PIPELINE
            reason = f"Unstructured {doc_format.value.upper()} detected: routing to AI Document Processing (OCR + Layout + Table + Extraction)."
        else:
            pipeline = ProcessingPipelineType.AI_DOCUMENT_PIPELINE
            reason = "Unknown format fallback: attempt AI Document Processing pipeline."

        logger.info(f"Classified {document.file_name} -> {pipeline.value} ({reason})")

        return ClassificationResult(
            document_id=document.document_id,
            file_name=document.file_name,
            detected_format=doc_format,
            mime_type=mime_type,
            target_pipeline=pipeline,
            reason=reason
        )

    def classify_bundle(self, documents: List[RawDocument]) -> List[ClassificationResult]:
        """
        Detects if XML and PDF belong to the same invoice (e.g. email with both).
        Pairs them up so XML takes precedence, while PDF is flagged as companion.
        """
        results = [self.classify_single(doc) for doc in documents]

        xml_docs = [r for r in results if r.detected_format == DocumentFormat.XML]
        pdf_docs = [r for r in results if r.detected_format == DocumentFormat.PDF]

        if xml_docs and pdf_docs:
            for xml_r in xml_docs:
                xml_r.has_paired_visual_file = True
                xml_r.paired_file_name = pdf_docs[0].file_name
                xml_r.reason += f" Paired with visual file '{pdf_docs[0].file_name}'."

        return results
