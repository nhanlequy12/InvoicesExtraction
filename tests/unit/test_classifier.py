import uuid
from src.classifier.detector import FormatDetector
from src.classifier.router import InputClassifier
from src.classifier.schemas import DocumentFormat, ProcessingPipelineType
from src.ingestion.base import IngestionSource, RawDocument


def test_format_detector_xml(sample_xml_bytes):
    detector = FormatDetector()
    fmt, mime = detector.detect_format("invoice.xml", sample_xml_bytes)
    assert fmt == DocumentFormat.XML
    assert "xml" in mime


def test_format_detector_pdf(sample_pdf_bytes):
    detector = FormatDetector()
    fmt, mime = detector.detect_format("invoice.pdf", sample_pdf_bytes)
    assert fmt == DocumentFormat.PDF
    assert "pdf" in mime


def test_format_detector_image(sample_image_bytes):
    detector = FormatDetector()
    fmt, mime = detector.detect_format("scan.png", sample_image_bytes)
    assert fmt == DocumentFormat.IMAGE
    assert "png" in mime


def test_input_classifier_routing_xml(sample_xml_bytes):
    classifier = InputClassifier()
    doc = RawDocument(
        document_id=str(uuid.uuid4()),
        source=IngestionSource.EMAIL,
        file_name="invoice_electronic.xml",
        file_bytes=sample_xml_bytes
    )
    result = classifier.classify_single(doc)
    assert result.target_pipeline == ProcessingPipelineType.XML_PIPELINE
    assert result.detected_format == DocumentFormat.XML


def test_input_classifier_routing_pdf(sample_pdf_bytes):
    classifier = InputClassifier()
    doc = RawDocument(
        document_id=str(uuid.uuid4()),
        source=IngestionSource.API,
        file_name="invoice_paper_scan.pdf",
        file_bytes=sample_pdf_bytes
    )
    result = classifier.classify_single(doc)
    assert result.target_pipeline == ProcessingPipelineType.AI_DOCUMENT_PIPELINE
    assert result.detected_format == DocumentFormat.PDF


def test_classifier_bundle_pairing(sample_xml_bytes, sample_pdf_bytes):
    classifier = InputClassifier()
    docs = [
        RawDocument(str(uuid.uuid4()), IngestionSource.EMAIL, "invoice.xml", sample_xml_bytes),
        RawDocument(str(uuid.uuid4()), IngestionSource.EMAIL, "invoice.pdf", sample_pdf_bytes),
    ]
    bundle_results = classifier.classify_bundle(docs)
    assert len(bundle_results) == 2

    xml_res = next(r for r in bundle_results if r.detected_format == DocumentFormat.XML)
    assert xml_res.target_pipeline == ProcessingPipelineType.XML_PIPELINE
    assert xml_res.has_paired_visual_file is True
    assert xml_res.paired_file_name == "invoice.pdf"
