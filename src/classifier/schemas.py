from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class DocumentFormat(str, Enum):
    XML = "xml"
    PDF = "pdf"
    IMAGE = "image"
    UNKNOWN = "unknown"


class ProcessingPipelineType(str, Enum):
    XML_PIPELINE = "xml_processing"
    AI_DOCUMENT_PIPELINE = "ai_document_processing"
    HYBRID_VERIFICATION = "hybrid_verification"


class ClassificationResult(BaseModel):
    document_id: str
    file_name: str
    detected_format: DocumentFormat
    mime_type: str
    target_pipeline: ProcessingPipelineType
    has_paired_visual_file: bool = False
    paired_file_name: Optional[str] = None
    reason: str
