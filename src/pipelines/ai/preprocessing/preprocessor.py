import asyncio
from dataclasses import dataclass, field
import io
from pathlib import Path
from typing import List, Optional, Tuple
import numpy as np
from PIL import Image, ImageEnhance, ImageOps, UnidentifiedImageError

from src.core.logging import logger


class PreprocessingError(Exception):
    """Base exception for all document preprocessing errors."""
    pass


class UnsupportedFileFormatError(PreprocessingError):
    """Raised when the document format is not supported."""
    pass


class CorruptDocumentError(PreprocessingError):
    """Raised when the document file is damaged, empty, or unreadable."""
    pass


class EncryptedDocumentError(PreprocessingError):
    """Raised when a PDF is password-protected or encrypted."""
    pass


class DocumentLimitExceededError(PreprocessingError):
    """Raised when a document exceeds size or page count limits."""
    pass


@dataclass
class PreprocessedPage:
    """
    Standardized container representing a single preprocessed invoice page.
    Compatible with downstream OCR engines and pipeline orchestration.
    """
    page_number: int
    image_bytes: bytes
    width: int
    height: int
    skew_angle: float = 0.0
    quality_score: float = 1.0
    mime_type: str = "image/png"
    dpi: int = 300
    transforms_applied: List[str] = field(default_factory=list)
    quality_warnings: List[str] = field(default_factory=list)


class DocumentPreprocessor:
    """
    Production-grade Document Preprocessor for Invoices.
    Handles:
      1. Format validation (magic bytes & structure, rejecting invalid/corrupt inputs).
      2. Secure, leak-free PDF rendering to standardized 300 DPI raster images.
      3. Real dimension detection & resolution standardization.
      4. Auto EXIF orientation correction and conditional deskewing (projection profile).
      5. Non-destructive conditional image enhancement (retaining small font & decimal marks).
      6. Objective image quality scoring (sharpness, brightness, contrast, resolution).
    """

    SUPPORTED_IMAGE_FORMATS = {"png", "jpeg", "jpg", "tiff", "tif", "bmp", "webp"}
    SUPPORTED_FORMATS = SUPPORTED_IMAGE_FORMATS | {"pdf"}

    def __init__(
        self,
        target_dpi: int = 300,
        auto_deskew: bool = True,
        max_file_size_mb: int = 25,
        max_pages: int = 30,
        max_dimension: int = 4000,
        min_deskew_angle: float = 0.5,
        max_deskew_angle: float = 45.0,
    ):
        self.target_dpi = target_dpi
        self.auto_deskew = auto_deskew
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.max_pages = max_pages
        self.max_dimension = max_dimension
        self.min_deskew_angle = min_deskew_angle
        self.max_deskew_angle = max_deskew_angle

    def process(self, file_bytes: bytes, file_name: str) -> List[PreprocessedPage]:
        """
        Synchronously preprocess a raw document file into a list of normalized PreprocessedPage objects.
        Raises PreprocessingError subclasses on validation or parsing failure.
        """
        detected_ext = self._validate_and_detect_format(file_bytes, file_name)

        if detected_ext == "pdf":
            pages = self._process_pdf(file_bytes, file_name)
        else:
            pages = [self._process_single_image(file_bytes, file_name, page_number=1)]

        logger.info(
            f"Preprocessed {len(pages)} page(s) for '{file_name}' "
            f"(format: {detected_ext.upper()}, mean quality: "
            f"{round(sum(p.quality_score for p in pages) / len(pages), 2)})"
        )
        return pages

    async def process_async(self, file_bytes: bytes, file_name: str) -> List[PreprocessedPage]:
        """
        Asynchronous wrapper to offload CPU-intensive preprocessing tasks
        to a worker thread pool, preventing blocking of the FastAPI event loop.
        """
        return await asyncio.to_thread(self.process, file_bytes, file_name)

    def _validate_and_detect_format(self, file_bytes: bytes, file_name: str) -> str:
        """
        Validates document size, non-emptiness, and verifies file type via magic bytes.
        """
        if not file_bytes or len(file_bytes) == 0:
            raise CorruptDocumentError(f"Document '{file_name}' is empty (0 bytes).")

        if len(file_bytes) > self.max_file_size_bytes:
            raise DocumentLimitExceededError(
                f"Document '{file_name}' size ({len(file_bytes)} bytes) exceeds "
                f"allowed limit of {self.max_file_size_bytes} bytes."
            )

        # Magic bytes detection
        if file_bytes.startswith(b"%PDF"):
            return "pdf"
        elif file_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return "png"
        elif file_bytes.startswith(b"\xff\xd8\xff"):
            return "jpeg"
        elif file_bytes.startswith(b"II*\x00") or file_bytes.startswith(b"MM\x00*"):
            return "tiff"
        elif file_bytes.startswith(b"BM"):
            return "bmp"
        elif file_bytes.startswith(b"RIFF") and len(file_bytes) >= 12 and file_bytes[8:12] == b"WEBP":
            return "webp"

        # Fallback to extension check with PIL verification
        ext = Path(file_name).suffix.lower().lstrip(".")
        if ext in self.SUPPORTED_FORMATS:
            if ext == "pdf":
                # Header did not match %PDF
                raise CorruptDocumentError(f"File '{file_name}' has .pdf extension but lacks valid PDF signature.")
            try:
                with Image.open(io.BytesIO(file_bytes)) as probe_img:
                    probe_img.verify()
                return ext
            except Exception as e:
                raise CorruptDocumentError(f"Image '{file_name}' is corrupt or unreadable: {e}") from e

        raise UnsupportedFileFormatError(
            f"File format for '{file_name}' is not supported. "
            f"Supported formats: {sorted(list(self.SUPPORTED_FORMATS))}"
        )

    def _process_pdf(self, pdf_bytes: bytes, file_name: str) -> List[PreprocessedPage]:
        """
        Renders PDF pages into images using PyMuPDF.
        Guarantees proper resource cleanup and rejects encrypted/empty files.
        Never falls back to passing raw PDF bytes into downstream image OCR.
        """
        try:
            try:
                import pymupdf as fitz
            except ImportError:
                import fitz  # Fallback to legacy import
        except ImportError as err:
            raise PreprocessingError(
                "PyMuPDF library is required to render PDF invoices to images. "
                "Please ensure 'pymupdf' is installed."
            ) from err

        doc = None
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")

            if doc.is_encrypted:
                raise EncryptedDocumentError(f"PDF document '{file_name}' is encrypted or password-protected.")

            page_count = doc.page_count
            if page_count == 0:
                raise CorruptDocumentError(f"PDF document '{file_name}' contains no readable pages.")

            if page_count > self.max_pages:
                raise DocumentLimitExceededError(
                    f"PDF document '{file_name}' has {page_count} pages, "
                    f"exceeding the maximum allowed limit of {self.max_pages} pages."
                )

            preprocessed_pages = []
            for i in range(page_count):
                page = doc.load_page(i)
                # Calculate zoom matrix for target DPI (PDF default is 72 DPI)
                zoom = self.target_dpi / 72.0
                matrix = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=matrix, alpha=False)

                # Convert to PIL Image for standardized processing
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

                page_obj = self._process_image_object(
                    img=img,
                    page_number=i + 1,
                    source_format="pdf"
                )
                preprocessed_pages.append(page_obj)

            return preprocessed_pages

        except (EncryptedDocumentError, DocumentLimitExceededError, CorruptDocumentError):
            raise
        except Exception as e:
            # Map unreadable/damaged stream errors to CorruptDocumentError
            err_msg = str(e)
            if "FileDataError" in type(e).__name__ or "open stream" in err_msg.lower() or "cannot open" in err_msg.lower():
                raise CorruptDocumentError(f"PDF document '{file_name}' is corrupt or unreadable: {err_msg}") from e
            raise PreprocessingError(f"Failed to render PDF document '{file_name}': {err_msg}") from e
        finally:
            if doc is not None:
                doc.close()

    def _process_single_image(self, img_bytes: bytes, file_name: str, page_number: int = 1) -> PreprocessedPage:
        """
        Decodes a single raw image byte payload, inspects orientation, and runs image normalization.
        """
        try:
            img = Image.open(io.BytesIO(img_bytes))
            # Auto-correct camera orientation based on EXIF metadata
            img = ImageOps.exif_transpose(img)
        except UnidentifiedImageError as e:
            raise CorruptDocumentError(f"Image '{file_name}' could not be decoded: {e}") from e
        except Exception as e:
            raise CorruptDocumentError(f"Failed to open image '{file_name}': {e}") from e

        # Ensure uniform RGB format
        if img.mode != "RGB":
            img = img.convert("RGB")

        return self._process_image_object(img, page_number=page_number, source_format="image")

    def _process_image_object(self, img: Image.Image, page_number: int, source_format: str) -> PreprocessedPage:
        """
        Standardizes an active PIL Image:
          - Enforces memory/dimension constraints (scaling down if excessively large).
          - Conditional deskewing (only if auto_deskew=True and skew is significant).
          - Non-destructive conditional contrast/brightness tuning.
          - Calculates factual quality score (sharpness, brightness, contrast, resolution).
          - Encodes to PNG byte payload.
        """
        transforms_applied: List[str] = []

        # 1. Enforce dimension limits to protect RAM
        orig_width, orig_height = img.size
        max_edge = max(orig_width, orig_height)
        if max_edge > self.max_dimension:
            scale = self.max_dimension / float(max_edge)
            new_w = max(1, int(orig_width * scale))
            new_h = max(1, int(orig_height * scale))
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            transforms_applied.append(f"resize_max_dim({self.max_dimension})")

        # 2. Conditional Deskewing
        skew_angle = 0.0
        if self.auto_deskew:
            detected_angle = self._detect_skew_angle(img)
            if self.min_deskew_angle <= abs(detected_angle) <= self.max_deskew_angle:
                # Counter-rotate to deskew; fill borders with clean white (typical for invoice paper)
                img = img.rotate(
                    angle=float(detected_angle),
                    resample=Image.Resampling.BICUBIC,
                    expand=True,
                    fillcolor=(255, 255, 255)
                )
                skew_angle = round(float(detected_angle), 2)
                transforms_applied.append(f"deskew({skew_angle}deg)")

        # 3. Conditional Image Enhancement (Only apply if genuinely poor, avoid over-processing)
        gray = ImageOps.grayscale(img)
        arr = np.array(gray, dtype=np.float32)
        mean_lum = float(np.mean(arr))
        std_lum = float(np.std(arr))

        # Underexposed / dark photo -> mild brightness boost
        if mean_lum < 90.0:
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(1.2)
            transforms_applied.append("enhance_brightness")

        # Faded / low contrast -> mild contrast boost
        if std_lum < 35.0:
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(1.25)
            transforms_applied.append("enhance_contrast")

        # 4. Objective Quality Assessment
        quality_score, quality_warnings = self._evaluate_quality(img, skew_angle)

        # 5. Export to PNG bytes
        buffer = io.BytesIO()
        img.save(buffer, format="PNG", optimize=True)
        final_bytes = buffer.getvalue()
        final_width, final_height = img.size

        return PreprocessedPage(
            page_number=page_number,
            image_bytes=final_bytes,
            width=final_width,
            height=final_height,
            skew_angle=skew_angle,
            quality_score=quality_score,
            mime_type="image/png",
            dpi=self.target_dpi,
            transforms_applied=transforms_applied,
            quality_warnings=quality_warnings
        )

    def _detect_skew_angle(self, img: Image.Image) -> float:
        """
        Estimates skew angle between -15° and +15° via projection profile variance.
        Operates on a downscaled thumbnail for near-instant execution (<25ms).
        Returns the angle that maximizes horizontal text line alignment.
        """
        try:
            # Downscale thumbnail for fast projection analysis
            thumb = img.resize((300, 400), Image.Resampling.BILINEAR)
            thumb_gray = ImageOps.grayscale(thumb)

            # Invert so black text on white paper becomes high intensity
            arr = 255.0 - np.array(thumb_gray, dtype=np.float32)

            best_angle = 0.0
            max_variance = 0.0
            test_angles = np.arange(-15.0, 15.5, 0.5)

            for angle in test_angles:
                rot_thumb = thumb_gray.rotate(float(angle), expand=False, fillcolor=255)
                rot_arr = 255.0 - np.array(rot_thumb, dtype=np.float32)
                row_sums = np.sum(rot_arr, axis=1)
                variance = float(np.var(row_sums))

                if variance > max_variance:
                    max_variance = variance
                    best_angle = float(angle)

            return best_angle
        except Exception as e:
            logger.warning(f"Skew detection encountered error, falling back to 0.0: {e}")
            return 0.0

    def _evaluate_quality(self, img: Image.Image, skew_angle: float) -> Tuple[float, List[str]]:
        """
        Computes composite image quality score (0.0 to 1.0) and warning flags based on:
          - Sharpness (Laplacian filter variance for blur detection).
          - Contrast (Standard deviation of pixel luminance).
          - Exposure / Brightness (Mean luminance).
          - Resolution (Adequacy of dimensions for OCR legibility).
        """
        warnings: List[str] = []
        gray = ImageOps.grayscale(img)
        arr = np.array(gray, dtype=np.float32)
        w, h = img.size

        # A. Sharpness / Blur estimation via 2D Laplacian kernel
        if arr.shape[0] > 4 and arr.shape[1] > 4:
            lap = (
                arr[1:-1, 2:] + arr[1:-1, :-2] + arr[2:, 1:-1] + arr[:-2, 1:-1]
                - 4.0 * arr[1:-1, 1:-1]
            )
            lap_variance = float(np.var(lap))
        else:
            lap_variance = 100.0

        if lap_variance < 60.0:
            warnings.append("BLURRY_IMAGE")
        sharpness_score = min(1.0, max(0.0, lap_variance / 350.0))

        # B. Contrast estimation
        std_lum = float(np.std(arr))
        if std_lum < 30.0:
            warnings.append("LOW_CONTRAST")
        contrast_score = min(1.0, max(0.0, std_lum / 60.0))

        # C. Exposure / Brightness estimation
        mean_lum = float(np.mean(arr))
        if mean_lum < 80.0:
            warnings.append("UNDEREXPOSED")
        elif mean_lum > 248.0:
            warnings.append("OVEREXPOSED")
        brightness_score = 1.0 - (abs(mean_lum - 200.0) / 200.0)
        brightness_score = min(1.0, max(0.0, brightness_score))

        # D. Resolution adequacy
        min_dim = min(w, h)
        if min_dim < 600:
            warnings.append("LOW_RESOLUTION")
        resolution_score = min(1.0, max(0.0, min_dim / 1200.0))

        # E. Severe skew warning
        if abs(skew_angle) > 10.0:
            warnings.append("SIGNIFICANT_SKEW")

        # Composite weighted score
        composite = (
            0.35 * sharpness_score
            + 0.30 * contrast_score
            + 0.20 * brightness_score
            + 0.15 * resolution_score
        )
        final_score = round(min(1.0, max(0.1, composite)), 2)

        return final_score, warnings
