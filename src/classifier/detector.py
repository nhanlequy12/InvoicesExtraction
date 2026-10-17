from pathlib import Path
from typing import Tuple
from src.classifier.schemas import DocumentFormat


class FormatDetector:
    """Detects document format from magic bytes and filename extension."""

    @staticmethod
    def detect_format(file_name: str, file_bytes: bytes) -> Tuple[DocumentFormat, str]:
        ext = Path(file_name).suffix.lower()

        # Check magic bytes first
        if file_bytes.startswith(b"<?xml") or file_bytes.startswith(b"<HDon") or file_bytes.startswith(b"\xef\xbb\xbf<?xml"):
            return DocumentFormat.XML, "application/xml"
        if file_bytes.startswith(b"%PDF"):
            return DocumentFormat.PDF, "application/pdf"
        if file_bytes.startswith(b"\xff\xd8\xff"):
            return DocumentFormat.IMAGE, "image/jpeg"
        if file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return DocumentFormat.IMAGE, "image/png"
        if file_bytes.startswith(b"II*\x00") or file_bytes.startswith(b"MM\x00*"):
            return DocumentFormat.IMAGE, "image/tiff"

        # Fallback to extension
        if ext == ".xml":
            return DocumentFormat.XML, "application/xml"
        elif ext == ".pdf":
            return DocumentFormat.PDF, "application/pdf"
        elif ext in [".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"]:
            return DocumentFormat.IMAGE, f"image/{ext.replace('.', '')}"

        return DocumentFormat.UNKNOWN, "application/octet-stream"
